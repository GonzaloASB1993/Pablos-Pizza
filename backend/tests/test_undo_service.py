"""undo_service: every action type (happy path and each refusal), idempotency, atomicity, windows, the `undo` type"""
import copy
import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402,F401
from services import (booking_proposals, event_proposals, expense_proposals,  # noqa: E402,F401
                      inventory_proposals)
from services import inventory_service as inv  # noqa: E402
from services import pending_actions_service as pas  # noqa: E402
from services import undo_service  # noqa: E402
from tests import fakes  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402
from tests.undo_support import (PANEL_USER, USER, confirmed, count, doc, existing_line, expense_line,  # noqa: E402
                                item, new_line, no_audit, receipt_payload, seed_booking, seed_item)

CannotUndo = undo_service.CannotUndo


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))
    monkeypatch.setattr('services.booking_service.notify_new_booking', lambda booking: None)
    monkeypatch.setattr('utils.audit.log_audit', lambda *a, **k: None)


@pytest.fixture
def db():
    return FakeFirestore()


def run_undo(db, action, source='whatsapp', user=USER, **kwargs):
    return undo_service.undo(db, action['id'], user, source=source, audit=kwargs.pop('audit', no_audit), **kwargs)


def refused(db, action, reason, source='whatsapp'):
    """The undo is refused with `reason` and NOTHING outside the action's own undo marker changed"""
    before = _business(db)
    with pytest.raises(CannotUndo) as caught:
        run_undo(db, action, source)
    assert caught.value.reason == reason, caught.value.reason
    assert _business(db) == before
    return caught.value


def _business(db):
    return copy.deepcopy({k: v for k, v in db.store.items() if k != 'pending_actions'})


def undo_state(db, action):
    return (doc(db, 'pending_actions', action['id']).get('undo') or {}).get('state')


def strip_result(db, action, *keys):
    stored = doc(db, 'pending_actions', action['id'])['result']
    for key in keys:
        stored.pop(key, None)
    db.collection('pending_actions').document(action['id']).update({'result': stored})
    return pas.get(db, action['id'])


# ============ expense ============

def test_expense_is_deleted_with_a_snapshot(db):
    action = confirmed(db, 'expense', {'supplier': 'Copec', 'total': 20000, 'date': '2026-10-10'})
    expense_id = action['result']['expense_id']
    audits = []
    result = run_undo(db, action, audit=lambda *a, **k: audits.append((a, k)))
    assert doc(db, 'variable_expenses', expense_id) is None
    assert result['snapshots']['expenses'][expense_id]['data']['amount'] == 20000
    assert undo_state(db, action) == 'done' and doc(db, 'pending_actions', action['id'])['status'] == 'confirmed'
    (args, kwargs), = audits
    assert args[1:4] == ('undo', 'pending_action', action['id']) and kwargs['metadata']['source'] == 'whatsapp'
    assert kwargs['changes']['type'] == 'expense' and expense_id in kwargs['changes']['snapshots']['expenses']


def test_fixed_expense_is_deleted_too(db):
    action = confirmed(db, 'expense', {'supplier': 'Arriendo', 'total': 300000, 'date': '2026-10-01', 'kind': 'fixed'})
    run_undo(db, action)
    assert count(db, 'fixed_expenses') == 0


def test_an_edited_expense_is_refused(db):
    action = confirmed(db, 'expense', {'supplier': 'Copec', 'total': 20000, 'date': '2026-10-10'})
    ref = db.collection('variable_expenses').document(action['result']['expense_id'])
    ref.update({'updated_at': ref.get().to_dict()['created_at'] + timedelta(minutes=3), 'amount': 21000})
    refused(db, action, 'edited')


def test_an_expense_that_is_gone_is_refused(db):
    action = confirmed(db, 'expense', {'supplier': 'Copec', 'total': 20000, 'date': '2026-10-10'})
    db.collection('variable_expenses').document(action['result']['expense_id']).delete()
    refused(db, action, 'missing')


# ============ inventory_receipt ============

def test_receipt_is_undone_line_by_line(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    action = confirmed(db, 'inventory_receipt', receipt_payload(existing_line(quantity=5, amount=6000), new_line(),
                                                                  expense_line()))
    existing, new, expense = action['result']['lines']
    assert item(db, 'flour')['current_stock'] == 15
    result = run_undo(db, action)

    flour = item(db, 'flour')
    assert flour['current_stock'] == 10 and flour['weighted_avg_cost'] == 1000 and flour['total_value'] == 10000
    assert doc(db, 'inventory', new['item_id']) is None                       # the item the receipt created is gone
    assert doc(db, 'variable_expenses', expense['expense_id']) is None
    original = doc(db, 'inventory_movements', existing['movement_id'])
    assert original['reverted'] is True and doc(db, 'inventory_movements', original['reversal_movement_id'])['movement_type'] == 'reversal'
    assert new['item_id'] in result['snapshots']['items'] and expense['expense_id'] in result['snapshots']['expenses']
    assert any('Harina' in line for line in result['effects'])


def test_receipt_with_a_later_movement_of_the_item_is_refused_with_the_alternative(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    action = confirmed(db, 'inventory_receipt', receipt_payload(existing_line(), expense_line()))
    inv.register_movement(db, 'flour', 'sale', 2, 1000, movement_id='later')
    error = refused(db, action, 'later_movements')
    assert 'Harina' in str(error) and 'conteo' in str(error)
    assert count(db, 'variable_expenses') == 1                                 # the expense line was not deleted either


def test_receipt_where_one_line_is_not_revertible_changes_nothing(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_item(db, 'oil', name='Aceite', stock=5, avg=2000)
    action = confirmed(db, 'inventory_receipt', receipt_payload(existing_line('flour'), existing_line('oil', 1, 2000, 'Aceite')))
    inv.set_stock(db, 'oil', 99)                                               # oil no longer matches what the receipt left
    refused(db, action, 'stock_changed')
    assert item(db, 'flour')['current_stock'] == 15


def test_receipt_with_two_lines_of_the_same_item_reverts_the_chain(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    action = confirmed(db, 'inventory_receipt', receipt_payload(existing_line(quantity=5, amount=6000),
                                                                  existing_line(quantity=3, amount=4500)))
    first, second = (line['movement_id'] for line in action['result']['lines'])
    stamp = datetime(2026, 10, 10, 12, 0, 0)
    db.collection('inventory_movements').document(first).update({'created_at': stamp})
    db.collection('inventory_movements').document(second).update({'created_at': stamp + timedelta(minutes=1)})
    assert item(db, 'flour')['current_stock'] == 18
    run_undo(db, action)
    assert item(db, 'flour')['current_stock'] == 10 and item(db, 'flour')['weighted_avg_cost'] == 1000


def test_receipt_whose_new_item_was_used_afterwards_is_refused(db):
    action = confirmed(db, 'inventory_receipt', receipt_payload(new_line('Queso', 2, 10000)))
    new_item = action['result']['lines'][0]['item_id']
    inv.register_movement(db, new_item, 'sale', 1, 5000, movement_id='sold')
    refused(db, action, 'later_movements')
    assert doc(db, 'inventory', new_item) is not None


def test_receipt_with_an_edited_expense_line_is_refused(db):
    seed_item(db, 'flour')
    action = confirmed(db, 'inventory_receipt', receipt_payload(existing_line(), expense_line()))
    ref = db.collection('variable_expenses').document(action['result']['lines'][1]['expense_id'])
    ref.update({'updated_at': ref.get().to_dict()['created_at'] + timedelta(hours=1)})
    refused(db, action, 'edited')
    assert item(db, 'flour')['current_stock'] == 15


def test_new_item_without_stock_is_deleted(db):
    action = confirmed(db, 'inventory_receipt', receipt_payload(new_line('Sal', 0, 0)))
    new_item = action['result']['lines'][0]['item_id']
    assert 'movement_id' not in action['result']['lines'][0]
    run_undo(db, action)
    assert doc(db, 'inventory', new_item) is None


# ============ inventory_update ============

def test_update_goes_back_to_the_before_values(db):
    seed_item(db, 'flour', name='Harina', supplier='Antes', min_stock=2, stock=10)
    action = confirmed(db, 'inventory_update', {'item_id': 'flour', 'changes': {'name': 'Harina 000', 'min_stock': 20}})
    assert action['result']['before'] == {'name': 'Harina', 'min_stock': 2} and item(db, 'flour')['needs_restock'] is True
    run_undo(db, action)
    stored = item(db, 'flour')
    assert stored['name'] == 'Harina' and stored['min_stock'] == 2 and stored['needs_restock'] is False


def test_update_edited_again_is_refused(db):
    seed_item(db, 'flour', name='Harina')
    action = confirmed(db, 'inventory_update', {'item_id': 'flour', 'changes': {'name': 'Harina 000'}})
    inv.update_item(db, 'flour', {'name': 'Otra cosa'})
    refused(db, action, 'edited')


def test_update_of_an_old_action_falls_back_to_the_context(db):
    seed_item(db, 'flour', name='Harina')
    action = confirmed(db, 'inventory_update', {'item_id': 'flour', 'changes': {'name': 'Harina 000'}},
                       context={'before': {'name': 'Harina'}})
    action = strip_result(db, action, 'before', 'after')
    run_undo(db, action)
    assert item(db, 'flour')['name'] == 'Harina'


def test_update_without_any_before_data_is_old(db):
    seed_item(db, 'flour', name='Harina')
    action = confirmed(db, 'inventory_update', {'item_id': 'flour', 'changes': {'name': 'Harina 000'}})
    action = strip_result(db, action, 'before', 'after')
    refused(db, action, 'old')


def test_update_that_changed_nothing_is_a_noop(db):
    seed_item(db, 'flour', name='Harina')
    action = confirmed(db, 'inventory_update', {'item_id': 'flour', 'changes': {'name': 'Harina'}})
    refused(db, action, 'noop')


# ============ stock_adjustment ============

def test_waste_is_reverted(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    action = confirmed(db, 'stock_adjustment', {'item_id': 'flour', 'mode': 'waste', 'quantity': 3})
    assert item(db, 'flour')['current_stock'] == 7
    run_undo(db, action)
    assert item(db, 'flour')['current_stock'] == 10
    assert doc(db, 'inventory_movements', action['result']['movement_id'])['reverted'] is True


def test_count_that_changed_nothing_has_nothing_to_undo(db):
    seed_item(db, 'flour', stock=10)
    action = confirmed(db, 'stock_adjustment', {'item_id': 'flour', 'mode': 'count', 'quantity': 10})
    refused(db, action, 'noop')


def test_adjustment_with_a_later_movement_is_refused(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    action = confirmed(db, 'stock_adjustment', {'item_id': 'flour', 'mode': 'waste', 'quantity': 3})
    inv.register_movement(db, 'flour', 'purchase', 1, 1000, movement_id='later')
    refused(db, action, 'later_movements')


# ============ event_supplies ============

def test_new_supplies_are_deleted_and_the_estimate_removed(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db)
    action = confirmed(db, 'event_supplies', {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'estimated_quantity': 4}]})
    assert action['result']['created'] is True and action['result']['prev_estimated_supply_cost'] is None
    run_undo(db, action)
    assert count(db, 'event_supplies') == 0
    assert 'estimated_supply_cost' not in (doc(db, 'bookings', 'b1').get('financials') or {})


def test_replaced_supplies_go_back_to_the_previous_estimate(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db)
    first = confirmed(db, 'event_supplies', {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'estimated_quantity': 4}],
                                             'notes': 'primera'})
    second = confirmed(db, 'event_supplies', {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'estimated_quantity': 6}]})
    assert second['result']['created'] is False and second['result']['prev_estimated_supply_cost'] == 4000
    run_undo(db, second)
    restored = doc(db, 'event_supplies', first['result']['supplies_id'])
    assert restored['items'][0]['estimated_quantity'] == 4 and restored['estimated_total_cost'] == 4000
    assert restored['notes'] == 'primera' and doc(db, 'bookings', 'b1')['financials']['estimated_supply_cost'] == 4000


def test_supplies_with_a_consumption_registered_are_refused(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db)
    action = confirmed(db, 'event_supplies', {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'estimated_quantity': 4}]})
    confirmed(db, 'event_consumption', {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'actual_quantity_consumed': 3}]})
    refused(db, action, 'consumption_exists')


def test_supplies_edited_afterwards_are_refused(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db)
    action = confirmed(db, 'event_supplies', {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'estimated_quantity': 4}]})
    db.collection('event_supplies').document(action['result']['supplies_id']).update(
        {'items': [{'item_id': 'flour', 'estimated_quantity': 9}]})
    refused(db, action, 'edited')


def test_supplies_without_the_new_data_are_old(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db)
    action = confirmed(db, 'event_supplies', {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'estimated_quantity': 4}]})
    refused(db, strip_result(db, action, 'created', 'previous', 'prev_estimated_supply_cost'), 'old')


# ============ event_consumption ============

CONSUME = {'booking_id': 'b1', 'total_other_expenses': 2000, 'items': [{'item_id': 'flour', 'actual_quantity_consumed': 3}]}


def test_consumption_gives_the_stock_back_and_deletes_its_movements(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db, financials={'income': 50000})
    action = confirmed(db, 'event_consumption', CONSUME)
    assert item(db, 'flour')['current_stock'] == 7
    result = run_undo(db, action)

    assert item(db, 'flour')['current_stock'] == 10
    assert count(db, 'event_consumption') == 0
    assert all(m['reference_type'] != 'event_consumption' for m in db.store['inventory_movements'].values())
    assert any(m['movement_type'] == 'reversal' for m in db.store['inventory_movements'].values())
    financials = doc(db, 'bookings', 'b1')['financials']
    assert financials == {'income': 50000}                                     # exactly what it had before
    assert result['snapshots']['consumption'] and result['snapshots']['movements']


def test_consumption_undone_then_registered_again_does_not_give_stock_back_twice(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db)
    first = confirmed(db, 'event_consumption', CONSUME)
    run_undo(db, first)
    assert item(db, 'flour')['current_stock'] == 10
    second = confirmed(db, 'event_consumption', {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'actual_quantity_consumed': 2}]})
    assert second['result']['replaced'] is False
    assert item(db, 'flour')['current_stock'] == 8                             # 10 - 2, no phantom +3 from the undone one


def test_consumption_restores_previous_financials_with_profit(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db, financials={'income': 50000, 'total_expenses': 111, 'profit': 222})
    action = confirmed(db, 'event_consumption', CONSUME)
    run_undo(db, action)
    assert doc(db, 'bookings', 'b1')['financials'] == {'income': 50000, 'total_expenses': 111, 'profit': 222}


def test_consumption_with_fractional_quantities_survives_the_two_decimal_rounding(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db)
    action = confirmed(db, 'event_consumption', {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'actual_quantity_consumed': 0.125}]})
    run_undo(db, action)
    assert item(db, 'flour')['current_stock'] == 10


def test_consumption_that_replaced_another_is_refused(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db)
    confirmed(db, 'event_consumption', CONSUME)
    second = confirmed(db, 'event_consumption', {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'actual_quantity_consumed': 2}]})
    assert second['result']['replaced'] is True
    refused(db, second, 'replaced')


def test_consumption_of_a_completed_event_is_refused(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db)
    action = confirmed(db, 'event_consumption', CONSUME)
    db.collection('bookings').document('b1').update({'status': 'completed'})
    refused(db, action, 'booking_completed')


def test_consumption_with_a_later_movement_is_refused(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db)
    action = confirmed(db, 'event_consumption', CONSUME)
    inv.register_movement(db, 'flour', 'purchase', 5, 1000, movement_id='later')
    refused(db, action, 'later_movements')


def test_consumption_whose_event_numbers_changed_is_refused(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db)
    action = confirmed(db, 'event_consumption', CONSUME)
    db.collection('bookings').document('b1').update({'financials': {'total_expenses': 1, 'supply_cost': 1, 'other_expenses': 0}})
    refused(db, action, 'financials_changed')


def test_consumption_without_the_new_data_is_old(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    seed_booking(db)
    action = confirmed(db, 'event_consumption', CONSUME)
    refused(db, strip_result(db, action, 'replaced', 'prev_financials', 'movement_ids'), 'old')


# ============ booking ============

BOOKING = {'client_name': 'Carla Soto', 'client_email': 'carla@example.com', 'client_phone': '+56955555555',
           'services': ['party'], 'event_date': '2026-12-20', 'event_time': '15:00', 'location': 'Calle 1', 'comuna': 'Lampa',
           'pizza_quantity': 12}


def test_pending_booking_is_cancelled_without_notifying_anyone(db, monkeypatch):
    sent = []
    monkeypatch.setattr('services.booking_service.notify_new_booking', lambda booking: sent.append(booking['id']))
    action = confirmed(db, 'booking', BOOKING)
    assert action['result']['customer_created'] is True and len(sent) == 1       # the "new booking" notice of the creation
    booking_id, customer_id = action['result']['booking_id'], action['result']['customer_id']
    bookings_before = doc(db, 'customers', customer_id)['total_bookings']

    result = run_undo(db, action)
    stored = doc(db, 'bookings', booking_id)
    assert stored['status'] == 'cancelled' and 'Deshecho' in stored['cancel_reason'] and stored['cancelled_at']
    assert doc(db, 'customers', customer_id)['total_bookings'] == bookings_before - 1
    assert len(sent) == 1                                                       # undoing notified nobody
    assert 'ya les llegó' in ' '.join(result['warnings'])


def test_booking_linked_to_an_existing_customer_decrements_that_customer(db):
    first = confirmed(db, 'booking', BOOKING)
    second = confirmed(db, 'booking', {**BOOKING, 'event_date': '2026-12-21'})
    assert second['result']['customer_created'] is False
    customer_id = second['result']['customer_id']
    before = doc(db, 'customers', customer_id)['total_bookings']
    run_undo(db, second)
    assert doc(db, 'customers', customer_id)['total_bookings'] == before - 1
    assert doc(db, 'bookings', first['result']['booking_id'])['status'] == 'pending'


def test_confirmed_booking_is_refused_with_the_panel_alternative(db):
    action = confirmed(db, 'booking', BOOKING)
    db.collection('bookings').document(action['result']['booking_id']).update({'status': 'confirmed'})
    error = refused(db, action, 'booking_confirmed')
    assert 'cancélala desde el panel' in str(error)


@pytest.mark.parametrize('status', ['completed', 'in_progress'])
def test_completed_booking_is_refused(db, status):
    action = confirmed(db, 'booking', BOOKING)
    db.collection('bookings').document(action['result']['booking_id']).update({'status': status})
    refused(db, action, 'booking_confirmed')


def test_booking_that_is_already_cancelled_is_refused(db):
    action = confirmed(db, 'booking', BOOKING)
    db.collection('bookings').document(action['result']['booking_id']).update({'status': 'cancelled'})
    refused(db, action, 'booking_not_pending')


def test_booking_with_supplies_is_refused(db):
    action = confirmed(db, 'booking', BOOKING)
    db.collection('event_supplies').document('s1').set({'id': 's1', 'booking_id': action['result']['booking_id'], 'items': []})
    refused(db, action, 'has_supplies')


def test_booking_without_the_new_data_is_old(db):
    action = confirmed(db, 'booking', BOOKING)
    refused(db, strip_result(db, action, 'customer_created'), 'old')


def test_cancel_pending_booking_only_touches_pending_ones(db):
    from services import booking_service
    seed_booking(db, 'p1', status='pending')
    seed_booking(db, 'c1', status='confirmed')
    booking_service.cancel_pending_booking(db, 'p1', 'x')
    assert doc(db, 'bookings', 'p1')['status'] == 'cancelled'
    with pytest.raises(booking_service.BookingError) as caught:
        booking_service.cancel_pending_booking(db, 'c1', 'x')
    assert caught.value.status_code == 409 and doc(db, 'bookings', 'c1')['status'] == 'confirmed'
    with pytest.raises(booking_service.BookingError):
        booking_service.cancel_pending_booking(db, 'ghost', 'x')


# ============ engine: idempotency, atomicity, windows, the undo type ============

def _stock_scene(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    return confirmed(db, 'stock_adjustment', {'item_id': 'flour', 'mode': 'waste', 'quantity': 3})


def test_undoing_twice_does_not_duplicate_anything(db):
    action = _stock_scene(db)
    first = run_undo(db, action)
    after_first = _business(db)
    second = run_undo(db, action)
    assert second['already_undone'] is True and 'already_undone' not in first
    assert _business(db) == after_first and item(db, 'flour')['current_stock'] == 10
    assert count(db, 'inventory_movements') == 2                                # the original + ONE reversal


def test_an_undo_cannot_be_undone(db):
    action = _stock_scene(db)
    proposal = undo_service.propose_undo(db, action['id'], USER)
    done = pas.confirm(db, proposal['id'], USER, audit=no_audit)
    assert done['result']['undone_type'] == 'stock_adjustment'
    refused(db, pas.get(db, proposal['id']), 'is_undo')
    with pytest.raises(CannotUndo) as caught:
        undo_service.propose_undo(db, proposal['id'], USER)
    assert caught.value.reason == 'is_undo'


def test_a_pending_or_unknown_action_has_nothing_to_undo(db):
    seed_item(db, 'flour')
    pending_action = pas.create(db, 'stock_adjustment', {'item_id': 'flour', 'mode': 'waste', 'quantity': 1}, 's', USER)
    refused(db, pending_action, 'not_confirmed')
    with pytest.raises(CannotUndo) as caught:
        undo_service.undo(db, 'nope', USER, source='panel', audit=no_audit)
    assert caught.value.reason == 'not_found'


def test_window_is_24_hours_from_whatsapp_and_7_days_from_the_panel(db):
    action = _stock_scene(db)
    two_days_ago = datetime.utcnow() - timedelta(days=2)
    db.collection('pending_actions').document(action['id']).update({'confirmed_at': two_days_ago})
    error = refused(db, action, 'window')
    assert 'panel' in str(error)
    run_undo(db, action, source='panel', user=PANEL_USER)                        # still inside the 7 days
    assert item(db, 'flour')['current_stock'] == 10


def test_panel_window_expires_after_7_days(db):
    action = _stock_scene(db)
    db.collection('pending_actions').document(action['id']).update({'confirmed_at': datetime.utcnow() - timedelta(days=8)})
    refused(db, action, 'window', source='panel')


def test_a_failed_commit_leaves_everything_untouched_and_can_be_retried(db, monkeypatch):
    action = _stock_scene(db)
    before = _business(db)

    def boom(self, *args, **kwargs):   # the fake applies a transaction's writes at once: failing the FIRST one = a failed commit
        raise RuntimeError('firestore down')
    monkeypatch.setattr(fakes.FakeTransaction, 'set', boom)
    with pytest.raises(RuntimeError):
        run_undo(db, action)
    assert _business(db) == before and undo_state(db, action) == 'failed'
    monkeypatch.undo()                                                            # restores commit (and the autouse patches)
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))
    run_undo(db, action)
    assert undo_state(db, action) == 'done' and item(db, 'flour')['current_stock'] == 10
    assert count(db, 'inventory_movements') == 2


def test_check_and_apply_run_inside_one_transaction(db, monkeypatch):
    action = _stock_scene(db)
    check, apply = undo_service.HANDLERS['stock_adjustment']
    seen = {}

    def spying_apply(db_, action_, plan, undo_id, writer, now):
        seen['writer'] = writer
        return apply(db_, action_, plan, undo_id, writer, now)
    monkeypatch.setitem(undo_service.HANDLERS, 'stock_adjustment', (check, spying_apply))
    run_undo(db, action)
    assert isinstance(seen['writer'], fakes.FakeTransaction)


def test_a_movement_that_lands_between_the_check_and_the_apply_aborts_the_undo(db, monkeypatch):
    action = _stock_scene(db)
    check, apply = undo_service.HANDLERS['stock_adjustment']

    def racing_check(db_, action_):
        plan = check(db_, action_)       # the check saw the stock as the movement left it ...
        db_.collection('inventory').document('flour').update({'current_stock': 4})   # ... and then a sale landed
        return plan
    monkeypatch.setitem(undo_service.HANDLERS, 'stock_adjustment', (racing_check, apply))
    with pytest.raises(CannotUndo) as caught:
        run_undo(db, action)
    assert caught.value.reason == 'stock_changed'
    assert item(db, 'flour')['current_stock'] == 4 and count(db, 'inventory_movements') == 1   # nothing overwritten
    assert undo_state(db, action) == 'failed'


def test_an_undo_in_progress_blocks_a_second_one_until_it_goes_stale(db):
    action = _stock_scene(db)
    marker = {'state': 'processing', 'undo_id': 'x', 'at': datetime.utcnow(), 'by': 'someone'}
    db.collection('pending_actions').document(action['id']).update({'undo': marker})
    refused(db, action, 'busy')
    marker['at'] = datetime.utcnow() - timedelta(minutes=30)
    db.collection('pending_actions').document(action['id']).update({'undo': marker})
    run_undo(db, action)
    assert undo_state(db, action) == 'done'


def test_unsupported_types_are_refused(db):
    db.collection('pending_actions').document('weird').set(
        {'id': 'weird', 'type': 'mystery', 'status': 'confirmed', 'confirmed_at': datetime.utcnow(), 'result': {}})
    with pytest.raises(CannotUndo) as caught:
        undo_service.undo(db, 'weird', USER, source='panel', audit=no_audit)
    assert caught.value.reason == 'unsupported'


def test_the_undo_action_type_goes_through_propose_and_confirm(db):
    action = _stock_scene(db)
    proposal = undo_service.propose_undo(db, action['id'], USER)
    assert proposal['type'] == 'undo' and proposal['status'] == 'pending' and 'Deshacer' in proposal['summary']
    assert item(db, 'flour')['current_stock'] == 7                               # proposing writes nothing
    done = pas.confirm(db, proposal['id'], USER, audit=no_audit)
    assert done['result']['target_action_id'] == action['id'] and item(db, 'flour')['current_stock'] == 10
    assert undo_state(db, action) == 'done'
    again = pas.confirm(db, proposal['id'], USER, audit=no_audit)                # SI twice: the stored result, nothing new
    assert again['already_confirmed'] is True and count(db, 'inventory_movements') == 2


def test_propose_undo_refuses_early_with_the_reason(db):
    action = _stock_scene(db)
    inv.register_movement(db, 'flour', 'purchase', 1, 1000, movement_id='later')
    with pytest.raises(CannotUndo) as caught:
        undo_service.propose_undo(db, action['id'], USER)
    assert caught.value.reason == 'later_movements'
    assert count(db, 'pending_actions') == 1                                     # no proposal was created


def test_confirming_an_undo_that_became_impossible_fails_with_the_reason(db):
    action = _stock_scene(db)
    proposal = undo_service.propose_undo(db, action['id'], USER)
    inv.register_movement(db, 'flour', 'purchase', 1, 1000, movement_id='later')   # happens between the proposal and the SI
    with pytest.raises(CannotUndo):
        pas.confirm(db, proposal['id'], USER, audit=no_audit)
    assert item(db, 'flour')['current_stock'] == 8 and pas.get(db, proposal['id'])['status'] == 'failed'


def test_labels_are_short_and_human(db):
    seed_item(db, 'flour')
    receipt = confirmed(db, 'inventory_receipt', receipt_payload(existing_line(amount=23450)))
    assert undo_service.label(receipt) == 'Compra Líder $23.450'
    expense = confirmed(db, 'expense', {'supplier': 'Copec', 'total': 20000, 'date': '2026-10-10'})
    assert undo_service.label(expense) == 'Gasto Copec $20.000'
    assert undo_service.label({'type': 'booking', 'payload': {'client_name': 'Ana'}}) == 'Reserva de Ana'
