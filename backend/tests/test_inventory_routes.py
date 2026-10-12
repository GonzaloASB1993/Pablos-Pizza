"""Characterization tests for the inventory endpoints in main.py.

They pin the behavior that existed BEFORE the logic moved to services/inventory_service.py.
Deliberate changes made by the extraction are called out in comments (search for CHANGED).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402
from tests.conftest import authenticate_as_admin  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402


@pytest.fixture
def db(monkeypatch):
    fake = FakeFirestore()
    monkeypatch.setattr(main, 'get_db', lambda: fake)
    return fake


@pytest.fixture
def client(db, monkeypatch):
    main.limiter.enabled = False
    main.app.config['TESTING'] = True
    return authenticate_as_admin(monkeypatch, main.app.test_client())


def _item(**overrides):
    data = {'name': 'Harina', 'category': 'Secos', 'current_stock': 10, 'min_stock': 5, 'max_stock': 50,
            'unit': 'kg', 'cost_per_unit': 1000}
    data.update(overrides)
    return data


def _create(client, **overrides):
    res = client.post('/api/inventory/', json=_item(**overrides))
    assert res.status_code == 201, res.get_json()
    return res.get_json()


# ---------- create ----------

def test_create_item_defaults_and_computed_fields(client, db):
    item = _create(client)
    assert item['product_type'] == 'raw_material'
    assert item['current_stock'] == 10.0 and item['cost_per_unit'] == 1000.0
    assert item['supplier'] == '' and item['notes'] == ''
    assert item['batch_size'] is None and item['shelf_life_days'] is None
    assert item['needs_restock'] is False
    assert item['nutrition_info']['calories'] == 0 and item['nutrition_info']['allergens'] == ''
    assert db.store['inventory'][item['id']]['name'] == 'Harina'


def test_create_item_flags_restock_when_at_or_below_minimum(client):
    assert _create(client, current_stock=5, min_stock=5)['needs_restock'] is True


def test_create_item_nutrition_info_is_converted_to_float(client):
    item = _create(client, nutrition_info={'calories': '350', 'allergens': 'gluten'})
    assert item['nutrition_info']['calories'] == 350.0
    assert item['nutrition_info']['allergens'] == 'gluten'
    assert item['nutrition_info']['proteins'] == 0


def test_create_item_without_required_field_is_a_400(client):
    # CHANGED by the extraction: it used to be a KeyError surfaced as a 500
    data = _item()
    data.pop('category')
    res = client.post('/api/inventory/', json=data)
    assert res.status_code == 400 and res.get_json() == {'error': 'Missing category'}


# ---------- update ----------

def test_update_item_recomputes_needs_restock(client):
    item = _create(client)
    res = client.put(f"/api/inventory/{item['id']}", json={'current_stock': '2', 'name': 'Harina 000'})
    body = res.get_json()
    assert res.status_code == 200
    assert body['name'] == 'Harina 000' and body['current_stock'] == 2.0
    assert body['needs_restock'] is True and body['category'] == 'Secos'


def test_update_item_not_found(client):
    res = client.put('/api/inventory/nope', json={'name': 'x'})
    assert res.status_code == 404 and res.get_json() == {'error': 'Item not found'}


def test_update_item_clears_optional_numbers_when_empty(client):
    item = _create(client, batch_size=4, shelf_life_days=30)
    body = client.put(f"/api/inventory/{item['id']}", json={'batch_size': '', 'shelf_life_days': 0}).get_json()
    assert body['batch_size'] is None and body['shelf_life_days'] is None


# ---------- stock endpoint ----------

@pytest.mark.parametrize('operation,value,expected', [
    ('set', 7, 7.0), ('add', 2.5, 12.5), ('subtract', 4, 6.0), ('subtract', 99, 0.0),
])
def test_stock_operations(client, operation, value, expected):
    item = _create(client)
    res = client.put(f"/api/inventory/{item['id']}/stock", json={'new_stock': value, 'operation': operation})
    body = res.get_json()
    assert res.status_code == 200 and body['new_stock'] == expected
    assert body['needs_restock'] is (expected <= 5)


def test_stock_invalid_operation_and_missing_item(client):
    item = _create(client)
    assert client.put(f"/api/inventory/{item['id']}/stock", json={'new_stock': 1, 'operation': 'x'}).status_code == 400
    assert client.put('/api/inventory/nope/stock', json={'new_stock': 1}).status_code == 404


def test_stock_rounds_to_two_decimals(client):
    item = _create(client, current_stock=0)
    body = client.put(f"/api/inventory/{item['id']}/stock", json={'new_stock': 0.1 + 0.2, 'operation': 'add'}).get_json()
    assert body['new_stock'] == 0.3


# ---------- movements ----------

def _move(client, item_id, movement_type, quantity, cost=0, **extra):
    return client.post('/api/inventory/movements/', json={
        'item_id': item_id, 'movement_type': movement_type, 'quantity': quantity,
        'cost_per_unit': cost, **extra})


def test_purchase_on_empty_stock_sets_average_to_purchase_cost(client, db):
    item = _create(client, current_stock=0, cost_per_unit=0)
    res = _move(client, item['id'], 'purchase', 25, 1120, supplier='Mayorista', reference_type='receipt', reference_id='r1')
    body = res.get_json()
    assert res.status_code == 200
    assert (body['stock_before'], body['stock_after']) == (0, 25)
    assert body['avg_cost_after'] == 1120
    stored = db.store['inventory'][item['id']]
    assert stored['current_stock'] == 25 and stored['weighted_avg_cost'] == 1120 and stored['cost_per_unit'] == 1120
    assert stored['total_value'] == 25 * 1120
    movement = db.store['inventory_movements'][body['movement_id']]
    assert movement['movement_type'] == 'purchase' and movement['quantity'] == 25
    assert movement['total_cost'] == 25 * 1120 and movement['supplier'] == 'Mayorista'
    assert movement['reference_type'] == 'receipt' and movement['reference_id'] == 'r1'
    assert movement['item_name'] == 'Harina' and movement['unit'] == 'kg'


def test_purchase_uses_weighted_average_cost(client):
    item = _create(client, current_stock=10, cost_per_unit=1000)
    body = _move(client, item['id'], 'purchase', 10, 2000).get_json()
    assert body['stock_after'] == 20
    assert body['avg_cost_before'] == 1000 and body['avg_cost_after'] == 1500


def test_outbound_movement_keeps_average_and_reduces_stock(client, db):
    item = _create(client, current_stock=10, cost_per_unit=1000)
    res = _move(client, item['id'], 'consumption', 4)
    body = res.get_json()
    assert res.status_code == 200 and body['stock_after'] == 6 and body['avg_cost_after'] == 1000
    movement = db.store['inventory_movements'][body['movement_id']]
    assert movement['quantity'] == -4


def test_outbound_movement_with_insufficient_stock_is_rejected(client, db):
    item = _create(client, current_stock=3)
    res = _move(client, item['id'], 'waste', 5)
    assert res.status_code == 400
    assert res.get_json()['error'] == 'Stock insuficiente. Stock actual: 3.0, cantidad solicitada: 5.0'
    assert 'inventory_movements' not in db.store
    assert db.store['inventory'][item['id']]['current_stock'] == 3


def test_positive_adjustment_goes_through_weighted_average(client):
    item = _create(client, current_stock=10, cost_per_unit=1000)
    body = _move(client, item['id'], 'adjustment', 10, 3000).get_json()
    assert body['stock_after'] == 20 and body['avg_cost_after'] == 2000


def test_negative_adjustment_reduces_stock_at_average_cost(client, db):
    item = _create(client, current_stock=10, cost_per_unit=1000)
    body = _move(client, item['id'], 'adjustment', -3).get_json()
    assert body['stock_after'] == 7 and body['avg_cost_after'] == 1000
    assert db.store['inventory_movements'][body['movement_id']]['quantity'] == -3


def test_negative_adjustment_cannot_go_below_zero(client):
    item = _create(client, current_stock=2)
    assert _move(client, item['id'], 'adjustment', -9).get_json()['stock_after'] == 0


def test_zero_quantity_adjustment_records_a_zero_movement(client, db):
    item = _create(client, current_stock=2)
    body = _move(client, item['id'], 'adjustment', 0).get_json()
    assert body['stock_after'] == 2
    assert db.store['inventory_movements'][body['movement_id']]['quantity'] == 0


@pytest.mark.parametrize('movement_type,quantity', [('purchase', 0), ('purchase', -2), ('consumption', 0)])
def test_invalid_movements_are_rejected(client, movement_type, quantity):
    item = _create(client)
    res = _move(client, item['id'], movement_type, quantity, 100)
    assert res.status_code == 400
    assert res.get_json() == {'error': 'Invalid movement type or quantity'}


def test_unknown_movement_type_is_treated_as_outbound(client):
    # Latent quirk pinned on purpose: any type that is not inbound reduces stock.
    # The AI agent only emits known types, so it never relies on this.
    item = _create(client, current_stock=10)
    body = _move(client, item['id'], 'whatever', 1).get_json()
    assert body['stock_after'] == 9


def test_movement_for_unknown_item(client):
    res = _move(client, 'nope', 'purchase', 1, 1)
    assert res.status_code == 404 and res.get_json() == {'error': 'Item not found'}


def test_movement_flags_restock_needs(client, db):
    item = _create(client, current_stock=10, min_stock=5)
    body = _move(client, item['id'], 'consumption', 6).get_json()
    assert body['needs_restock'] is True
    assert db.store['inventory'][item['id']]['needs_restock'] is True
