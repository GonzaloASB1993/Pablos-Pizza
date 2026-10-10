"""Characterization tests for /api/event-supplies and /api/event-consumption (main.py).

They pin the behavior before the logic moves to services/event_inventory_service.py.
Deliberate changes made by the extraction are marked CHANGED.
"""
import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402


@pytest.fixture
def db(monkeypatch):
    fake = FakeFirestore()
    monkeypatch.setattr(main, 'get_db', lambda: fake)
    return fake


@pytest.fixture
def client(db):
    main.limiter.enabled = False
    main.app.config['TESTING'] = True
    return main.app.test_client()


def _booking(db, booking_id='b1', status='confirmed', **extra):
    db.store.setdefault('bookings', {})[booking_id] = {
        'id': booking_id, 'client_name': 'Martina', 'status': status, 'event_date': '2026-10-20', **extra}
    return booking_id


def _item(db, item_id, name, stock, cost=1000, unit='kg', **extra):
    db.store.setdefault('inventory', {})[item_id] = {
        'id': item_id, 'name': name, 'unit': unit, 'current_stock': stock, 'min_stock': 2, 'cost_per_unit': cost,
        'needs_restock': stock <= 2, **extra}
    return item_id


@pytest.fixture
def world(db):
    _booking(db)
    _item(db, 'flour', 'Harina', 50, cost=1000)                      # legacy item: only cost_per_unit
    _item(db, 'cheese', 'Queso', 20, cost=6000, weighted_avg_cost=5000)  # weighted average wins
    return db


def _supplies(client, items, booking_id='b1', **extra):
    return client.post('/api/event-supplies/', json={'booking_id': booking_id, 'items': items, **extra})


def _consume(client, items, booking_id='b1', other=0, **extra):
    return client.post('/api/event-consumption/', json={
        'booking_id': booking_id, 'items_consumed': items, 'total_other_expenses': other, **extra})


# ================= supplies: create =================

def test_supplies_require_booking_id_and_items(client):
    res = client.post('/api/event-supplies/', json={'items': []})
    assert res.status_code == 400 and res.get_json() == {'error': 'booking_id and items are required'}
    assert client.post('/api/event-supplies/', json={'booking_id': 'b1'}).status_code == 400


def test_supplies_booking_must_exist_and_be_confirmed(client, db):
    assert _supplies(client, [{'item_id': 'x', 'estimated_quantity': 1}], booking_id='nope').status_code == 404
    _booking(db, 'pend', status='pending')
    res = _supplies(client, [{'item_id': 'x', 'estimated_quantity': 1}], booking_id='pend')
    assert res.status_code == 400 and res.get_json() == {'error': 'Booking must be confirmed to add supplies'}


def test_supplies_item_validations(client, world):
    res = _supplies(client, [{'item_id': 'flour'}])
    assert res.status_code == 400 and res.get_json() == {'error': 'Each item must have item_id and estimated_quantity'}
    res = _supplies(client, [{'item_id': 'ghost', 'estimated_quantity': 1}])
    assert res.status_code == 404 and res.get_json() == {'error': 'Inventory item ghost not found'}
    res = _supplies(client, [{'item_id': 'flour', 'estimated_quantity': 999}])
    assert res.status_code == 400
    assert res.get_json()['error'] == 'Insufficient stock for Harina. Available: 50, Required: 999'


def test_supplies_are_costed_without_touching_stock_and_sync_the_booking(client, world):
    res = _supplies(client, [{'item_id': 'flour', 'estimated_quantity': 10, 'notes': 'masa'},
                             {'item_id': 'cheese', 'estimated_quantity': 4}], notes='Fiesta')
    body = res.get_json()
    assert res.status_code == 201 and body['supplies']['estimated_total_cost'] == 10 * 1000 + 4 * 5000
    flour, cheese = body['supplies']['items']
    assert flour['cost_per_unit'] == 1000 and flour['item_name'] == 'Harina' and flour['unit'] == 'kg' and flour['notes'] == 'masa'
    assert cheese['cost_per_unit'] == 5000 and cheese['estimated_total_cost'] == 20000
    assert world.store['event_supplies'][body['supplies_id']]['booking_id'] == 'b1'
    assert world.store['inventory']['flour']['current_stock'] == 50  # estimate only: stock untouched
    assert world.store['bookings']['b1']['financials']['estimated_supply_cost'] == 30000.0


def test_posting_supplies_twice_creates_two_documents(client, world):
    # Pinned quirk: nothing prevents a second estimate for the same booking
    _supplies(client, [{'item_id': 'flour', 'estimated_quantity': 1}])
    _supplies(client, [{'item_id': 'flour', 'estimated_quantity': 2}])
    assert len(world.store['event_supplies']) == 2


# ================= supplies: read / update =================

def test_get_supplies_by_booking(client, world):
    assert client.get('/api/event-supplies/booking/b1').status_code == 404
    created = _supplies(client, [{'item_id': 'flour', 'estimated_quantity': 3}]).get_json()
    res = client.get('/api/event-supplies/booking/b1')
    assert res.status_code == 200 and res.get_json()['id'] == created['supplies_id']
    assert isinstance(res.get_json()['created_at'], str)


def test_update_supplies_replaces_items_and_resyncs_the_booking(client, world):
    sid = _supplies(client, [{'item_id': 'flour', 'estimated_quantity': 10}]).get_json()['supplies_id']
    res = client.put(f'/api/event-supplies/{sid}', json={'items': [{'item_id': 'cheese', 'estimated_quantity': 2}], 'notes': 'v2'})
    body = res.get_json()['supplies']
    assert res.status_code == 200 and body['estimated_total_cost'] == 10000 and body['notes'] == 'v2'
    assert [i['item_id'] for i in body['items']] == ['cheese']
    assert world.store['bookings']['b1']['financials']['estimated_supply_cost'] == 10000.0


def test_update_supplies_notes_only_keeps_items(client, world):
    sid = _supplies(client, [{'item_id': 'flour', 'estimated_quantity': 10}]).get_json()['supplies_id']
    body = client.put(f'/api/event-supplies/{sid}', json={'notes': 'solo notas'}).get_json()['supplies']
    assert body['notes'] == 'solo notas' and body['estimated_total_cost'] == 10000 and len(body['items']) == 1


def test_update_supplies_errors(client, world):
    assert client.put('/api/event-supplies/nope', json={'notes': 'x'}).status_code == 404
    sid = _supplies(client, [{'item_id': 'flour', 'estimated_quantity': 1}]).get_json()['supplies_id']
    res = client.put(f'/api/event-supplies/{sid}', json={'items': [{'item_id': 'flour', 'estimated_quantity': 999}]})
    assert res.status_code == 400 and res.get_json() == {'error': 'Insufficient stock for Harina'}
    res = client.put(f'/api/event-supplies/{sid}', json={'items': [{'item_id': 'ghost', 'estimated_quantity': 1}]})
    assert res.status_code == 404


# ================= consumption: create =================

def test_consumption_required_fields_and_booking(client, world):
    res = client.post('/api/event-consumption/', json={'booking_id': 'b1'})
    assert res.status_code == 400
    assert res.get_json() == {'error': 'Required fields: booking_id, items_consumed, total_other_expenses'}
    assert _consume(client, [], booking_id='nope').status_code == 404


def test_consumption_actual_quantity_deducts_stock_and_records_a_sale_movement(client, world):
    res = _consume(client, [{'item_id': 'flour', 'actual_quantity_consumed': 8}, {'item_id': 'cheese', 'actual_quantity_consumed': 3}],
                   other=7000, notes='Fiesta')
    body = res.get_json()
    assert res.status_code == 201
    consumption = body['consumption']
    assert consumption['total_supply_cost'] == 8 * 1000 + 3 * 5000
    assert consumption['total_other_expenses'] == 7000 and consumption['total_cost'] == 23000 + 7000

    assert world.store['inventory']['flour']['current_stock'] == 42
    assert world.store['inventory']['cheese']['current_stock'] == 17
    assert world.store['inventory']['flour']['needs_restock'] is False

    movements = [m for m in world.store['inventory_movements'].values() if m['item_id'] == 'flour']
    movement, = movements
    assert movement['movement_type'] == 'sale' and movement['quantity'] == -8
    assert movement['reference_id'] == 'b1' and movement['reference_type'] == 'event_consumption'
    assert movement['stock_before'] == 50 and movement['stock_after'] == 42
    assert movement['notes'] == 'Consumo en evento - Fiesta'

    financials = world.store['bookings']['b1']['financials']
    assert financials['supply_cost'] == 23000 and financials['other_expenses'] == 7000 and financials['total_expenses'] == 30000
    assert 'profit' not in financials


def test_consumption_recomputes_profit_when_the_booking_has_income(client, world):
    world.store['bookings']['b1']['financials'] = {'income': 100000}
    _consume(client, [{'item_id': 'flour', 'actual_quantity_consumed': 10}], other=5000)
    assert world.store['bookings']['b1']['financials']['profit'] == 100000 - 15000


def test_consumption_from_returned_quantity_uses_the_estimate(client, world):
    _supplies(client, [{'item_id': 'flour', 'estimated_quantity': 10}])
    res = _consume(client, [{'item_id': 'flour', 'quantity_returned': 3}])
    item = res.get_json()['consumption']['items_consumed'][0]
    assert item['actual_quantity_consumed'] == 7 and item['estimated_quantity'] == 10
    assert item['quantity_returned'] == 3 and item['variance'] == -3
    assert world.store['inventory']['flour']['current_stock'] == 43


def test_returned_more_than_taken_is_rejected(client, world):
    _supplies(client, [{'item_id': 'flour', 'estimated_quantity': 10}])
    res = _consume(client, [{'item_id': 'flour', 'quantity_returned': 11}])
    assert res.status_code == 400
    assert res.get_json()['error'] == 'La cantidad que volvió (11.0) no puede ser mayor que lo llevado (10.0)'
    assert world.store['inventory']['flour']['current_stock'] == 50


def test_returned_without_an_estimate_falls_back_to_the_actual_quantity(client, world):
    item = _consume(client, [{'item_id': 'flour', 'quantity_returned': 3, 'actual_quantity_consumed': 4}]).get_json()['consumption']['items_consumed'][0]
    assert item['actual_quantity_consumed'] == 4 and item['variance'] is None


def test_consumption_item_validations(client, world):
    assert _consume(client, [{'actual_quantity_consumed': 1}]).status_code == 400
    res = _consume(client, [{'item_id': 'ghost', 'actual_quantity_consumed': 1}])
    assert res.status_code == 404 and res.get_json() == {'error': 'Inventory item ghost not found'}
    res = _consume(client, [{'item_id': 'flour', 'actual_quantity_consumed': 999}])
    assert res.status_code == 400
    assert res.get_json()['error'] == 'Insufficient stock for Harina. Available: 50, Required: 999.0'


def test_negative_consumption_is_clamped_to_zero_and_bad_expenses_to_zero(client, world):
    body = _consume(client, [{'item_id': 'flour', 'actual_quantity_consumed': -5}], other='mucho').get_json()['consumption']
    assert body['items_consumed'][0]['actual_quantity_consumed'] == 0 and body['total_other_expenses'] == 0
    assert world.store['inventory']['flour']['current_stock'] == 50


def test_consumption_rounds_stock_to_two_decimals(client, world):
    _consume(client, [{'item_id': 'flour', 'actual_quantity_consumed': 0.1 + 0.2}])
    assert world.store['inventory']['flour']['current_stock'] == 49.7


def test_registering_again_reverts_the_previous_movements_and_updates_the_same_document(client, world):
    first = _consume(client, [{'item_id': 'flour', 'actual_quantity_consumed': 10}]).get_json()
    second = _consume(client, [{'item_id': 'flour', 'actual_quantity_consumed': 4}], other=100)
    assert second.status_code == 201
    assert second.get_json()['consumption_id'] == first['consumption_id']
    assert len(world.store['event_consumption']) == 1
    assert world.store['inventory']['flour']['current_stock'] == 46  # 50 - 4, not 50 - 10 - 4
    movements = [m for m in world.store['inventory_movements'].values() if m['reference_type'] == 'event_consumption']
    assert len(movements) == 1 and movements[0]['quantity'] == -4
    assert world.store['event_consumption'][first['consumption_id']]['total_other_expenses'] == 100


def test_re_registering_can_reuse_stock_released_by_the_previous_consumption(client, world):
    _consume(client, [{'item_id': 'flour', 'actual_quantity_consumed': 45}])      # stock 5
    res = _consume(client, [{'item_id': 'flour', 'actual_quantity_consumed': 50}])  # needs the 45 back
    assert res.status_code == 201 and world.store['inventory']['flour']['current_stock'] == 0
    assert world.store['inventory']['flour']['needs_restock'] is True
