"""Characterization of the confirm executors BEFORE undo adds data to their `result`.

Other modules read `result` (WhatsApp messages, the web card), so these tests pin what each executor
already stores (a subset check: new keys may be added, none may disappear or change) and the writes they make.
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402,F401  (loads backend/.env at collection time, not mid-test)
from services import (booking_proposals, event_proposals, expense_proposals,  # noqa: E402,F401
                      inventory_proposals)
from services import pending_actions_service as pas  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402
from tests.undo_support import (confirmed, count, doc, existing_line, expense_line, item, new_line,  # noqa: E402
                                receipt_payload, seed_booking, seed_item)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))
    monkeypatch.setattr('services.booking_service.notify_new_booking', lambda booking: None)


@pytest.fixture
def db():
    return FakeFirestore()


def _id(action_id, key):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'{action_id}:{key}'))


# ---------- inventory_receipt ----------

def test_receipt_result_and_writes(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    action = confirmed(db, 'inventory_receipt', receipt_payload(existing_line(quantity=5, amount=6000), new_line(),
                                                                  expense_line()))
    result, aid = action['result'], action['id']
    assert result['inventory_lines'] == 2 and result['expense_lines'] == 1
    existing, new, expense = result['lines']
    assert existing['classification'] == 'existing' and existing['item_id'] == 'flour'
    assert existing['movement_id'] == _id(aid, '0:movement') and existing['stock_after'] == 15
    assert new['classification'] == 'new' and new['item_id'] == _id(aid, '1:item') and new['movement_id'] == _id(aid, '1:movement')
    assert expense['classification'] == 'expense' and expense['expense_id'] == _id(aid, '2:expense')

    movement = doc(db, 'inventory_movements', existing['movement_id'])
    assert (movement['stock_before'], movement['stock_after'], movement['movement_type']) == (10, 15, 'purchase')
    assert movement['avg_cost_before'] == 1000 and round(movement['avg_cost_after'], 4) == round((10 * 1000 + 6000) / 15, 4)
    assert item(db, 'flour')['current_stock'] == 15
    created = item(db, new['item_id'])
    assert created['current_stock'] == 2 and created['weighted_avg_cost'] == 5000
    assert doc(db, 'variable_expenses', expense['expense_id'])['amount'] == 8000
    assert count(db, 'inventory_movements') == 2


def test_receipt_confirm_twice_does_not_duplicate(db):
    seed_item(db, 'flour')
    action = confirmed(db, 'inventory_receipt', receipt_payload(existing_line()))
    again = pas.confirm(db, action['id'], {'uid': 'x', 'email': 'x'}, audit=lambda *a, **k: None)
    assert again['already_confirmed'] is True and count(db, 'inventory_movements') == 1


# ---------- inventory_update ----------

def test_update_result_and_write(db):
    seed_item(db, 'flour', name='Harina', supplier='Antes')
    action = confirmed(db, 'inventory_update', {'item_id': 'flour', 'changes': {'name': 'Harina 000', 'min_stock': 4}})
    assert {'item_id': 'flour', 'changed': ['min_stock', 'name']}.items() <= action['result'].items()
    stored = item(db, 'flour')
    assert stored['name'] == 'Harina 000' and stored['min_stock'] == 4 and stored['needs_restock'] is False


# ---------- stock_adjustment ----------

def test_adjustment_waste_count_and_noop(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    waste = confirmed(db, 'stock_adjustment', {'item_id': 'flour', 'mode': 'waste', 'quantity': 3, 'reason': 'se mojó'})
    assert waste['result']['movement_id'] == _id(waste['id'], 'adjustment') and waste['result']['stock_after'] == 7
    count_up = confirmed(db, 'stock_adjustment', {'item_id': 'flour', 'mode': 'count', 'quantity': 9})
    assert count_up['result']['stock_after'] == 9 and item(db, 'flour')['current_stock'] == 9
    noop = confirmed(db, 'stock_adjustment', {'item_id': 'flour', 'mode': 'count', 'quantity': 9})
    assert noop['result'] == {'item_id': 'flour', 'delta': 0, 'stock_after': 9}
    assert count(db, 'inventory_movements') == 2


# ---------- event_supplies ----------

def test_supplies_create_then_replace(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db)
    first = confirmed(db, 'event_supplies', {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'estimated_quantity': 4}]})
    assert first['result']['supplies_id'] == _id(first['id'], 'supplies')
    assert first['result']['estimated_total_cost'] == 4000 and first['result']['replaced'] is False
    assert doc(db, 'bookings', 'b1')['financials']['estimated_supply_cost'] == 4000

    second = confirmed(db, 'event_supplies', {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'estimated_quantity': 6}]})
    assert second['result']['supplies_id'] == first['result']['supplies_id'] and second['result']['replaced'] is True
    assert second['result']['estimated_total_cost'] == 6000
    assert count(db, 'event_supplies') == 1 and item(db, 'flour')['current_stock'] == 10   # an estimate never moves stock


# ---------- event_consumption ----------

def test_consumption_result_and_writes(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db, financials={'income': 50000})
    action = confirmed(db, 'event_consumption', {'booking_id': 'b1', 'total_other_expenses': 2000,
                                                 'items': [{'item_id': 'flour', 'actual_quantity_consumed': 3}]})
    result = action['result']
    assert result['consumption_id'] == _id(action['id'], 'consumption')
    assert (result['total_cost'], result['total_supply_cost'], result['items']) == (5000, 3000, 1)
    movement = doc(db, 'inventory_movements', _id(action['id'], 'movement:0'))
    assert movement['quantity'] == -3 and movement['reference_id'] == 'b1' and movement['reference_type'] == 'event_consumption'
    assert item(db, 'flour')['current_stock'] == 7
    financials = doc(db, 'bookings', 'b1')['financials']
    assert (financials['total_expenses'], financials['supply_cost'], financials['other_expenses'], financials['profit']) \
        == (5000, 3000, 2000, 45000)


def test_consumption_replaced_gives_the_old_stock_back(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db)
    confirmed(db, 'event_consumption', {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'actual_quantity_consumed': 3}]})
    second = confirmed(db, 'event_consumption', {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'actual_quantity_consumed': 2}]})
    assert item(db, 'flour')['current_stock'] == 8 and count(db, 'event_consumption') == 1
    assert count(db, 'inventory_movements') == 1 and second['result']['total_supply_cost'] == 2000


# ---------- booking ----------

BOOKING = {'client_name': 'Carla Soto', 'client_email': 'carla@example.com', 'client_phone': '+56955555555',
           'services': ['party'], 'event_date': '2026-12-20', 'event_time': '15:00', 'location': 'Calle 1', 'comuna': 'Lampa',
           'pizza_quantity': 12}


def test_booking_result_and_customer_link(db):
    action = confirmed(db, 'booking', BOOKING)
    result = action['result']
    assert result['booking_id'] == _id(action['id'], 'booking') and result['status'] == 'pending'
    assert result['estimated_price'] > 0 and result['customer_id']
    customer = doc(db, 'customers', result['customer_id'])
    assert customer['email'] == 'carla@example.com' and customer['total_bookings'] >= 1
    booking = doc(db, 'bookings', result['booking_id'])
    assert booking['status'] == 'pending' and booking['created_via'] == 'ai_agent'


# ---------- expense ----------

def test_expense_result_variable_and_fixed(db):
    variable = confirmed(db, 'expense', {'supplier': 'Copec', 'total': 20000, 'date': '2026-10-10', 'category': 'general'})
    assert variable['result'] == {'collection': 'variable_expenses', 'expense_id': _id(variable['id'], 'expense')}
    stored = doc(db, 'variable_expenses', variable['result']['expense_id'])
    assert stored['amount'] == 20000 and stored['source'] == 'ai_agent' and stored['created_at'] and stored['updated_at']

    fixed = confirmed(db, 'expense', {'supplier': 'Arriendo', 'total': 300000, 'date': '2026-10-01', 'kind': 'fixed',
                                      'category': 'arriendo'})
    assert fixed['result'] == {'collection': 'fixed_expenses', 'expense_id': _id(fixed['id'], 'expense')}
