"""Tests for what services/event_inventory_service.py guarantees beyond the legacy endpoints"""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import event_inventory_service as ev  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402


@pytest.fixture
def db():
    fake = FakeFirestore()
    fake.store['bookings'] = {'b1': {'id': 'b1', 'status': 'confirmed', 'financials': {'income': 100000}}}
    fake.store['inventory'] = {
        'flour': {'id': 'flour', 'name': 'Harina', 'unit': 'kg', 'current_stock': 50, 'min_stock': 2, 'cost_per_unit': 1000},
        'cheese': {'id': 'cheese', 'name': 'Queso', 'unit': 'kg', 'current_stock': 3, 'min_stock': 1, 'cost_per_unit': 6000},
    }
    return fake


def _snapshot(db):
    return copy.deepcopy(db.store)


def test_failure_halfway_changes_nothing_and_keeps_the_previous_consumption(db):
    ev.save_consumption(db, 'b1', [{'item_id': 'flour', 'actual_quantity_consumed': 10}], 0)
    before = _snapshot(db)

    # 2nd item does not have enough stock: legacy code had already reverted the first consumption by then
    with pytest.raises(ev.EventInventoryError) as err:
        ev.save_consumption(db, 'b1', [{'item_id': 'flour', 'actual_quantity_consumed': 5},
                                       {'item_id': 'cheese', 'actual_quantity_consumed': 99}], 0)
    assert err.value.status_code == 400 and 'Insufficient stock for Queso' in err.value.message
    assert _snapshot(db) == before  # stock, movements, consumption and booking untouched


def test_every_validation_error_leaves_the_database_untouched(db):
    before = _snapshot(db)
    for items in ([{'actual_quantity_consumed': 1}],
                  [{'item_id': 'ghost', 'actual_quantity_consumed': 1}],
                  [{'item_id': 'flour', 'actual_quantity_consumed': 999}]):
        with pytest.raises(ev.EventInventoryError):
            ev.save_consumption(db, 'b1', items, 0)
    assert _snapshot(db) == before


def test_plan_does_not_write_anything(db):
    before = _snapshot(db)
    plan = ev.plan_consumption(db, 'b1', [{'item_id': 'flour', 'actual_quantity_consumed': 4}], 500)
    assert plan['total_supply_cost'] == 4000 and plan['total_cost'] == 4500 and plan['stock']['flour'] == 46
    assert _snapshot(db) == before


def test_give_back_uses_what_the_movements_really_took_out(db):
    ev.save_consumption(db, 'b1', [{'item_id': 'flour', 'actual_quantity_consumed': 10}], 0)
    # The consumption document says 10, but the movement on record took out 12 (inconsistent data):
    # stock must get back what the MOVEMENT took, because that is what really left the shelf.
    movement = next(iter(db.store['inventory_movements'].values()))
    movement['quantity'] = -12
    db.store['inventory']['flour']['current_stock'] = 38
    ev.save_consumption(db, 'b1', [{'item_id': 'flour', 'actual_quantity_consumed': 4}], 0)
    assert db.store['inventory']['flour']['current_stock'] == 46  # 38 + 12 - 4
    assert len([m for m in db.store['inventory_movements'].values() if m['reference_type'] == 'event_consumption']) == 1


def test_items_dropped_from_a_re_registration_are_given_back(db):
    ev.save_consumption(db, 'b1', [{'item_id': 'flour', 'actual_quantity_consumed': 10}], 0)
    ev.save_consumption(db, 'b1', [{'item_id': 'cheese', 'actual_quantity_consumed': 1}], 0)
    assert db.store['inventory']['flour']['current_stock'] == 50
    assert db.store['inventory']['cheese']['current_stock'] == 2


def test_deterministic_ids_make_a_retry_rewrite_the_same_documents(db):
    ids = lambda index: f'move-{index}'  # noqa: E731
    ev.save_consumption(db, 'b1', [{'item_id': 'flour', 'actual_quantity_consumed': 10}], 0,
                        consumption_id='c-fixed', movement_ids=ids)
    ev.save_consumption(db, 'b1', [{'item_id': 'flour', 'actual_quantity_consumed': 10}], 0,
                        consumption_id='c-fixed', movement_ids=ids)
    assert list(db.store['event_consumption']) == ['c-fixed']
    assert list(db.store['inventory_movements']) == ['move-0']
    assert db.store['inventory']['flour']['current_stock'] == 40  # not 30


def test_booking_financials_follow_the_consumption(db):
    ev.save_consumption(db, 'b1', [{'item_id': 'flour', 'actual_quantity_consumed': 10}], 2000)
    fin = db.store['bookings']['b1']['financials']
    assert fin['supply_cost'] == 10000 and fin['other_expenses'] == 2000 and fin['total_expenses'] == 12000
    assert fin['profit'] == 100000 - 12000 and fin['income'] == 100000


def test_unknown_booking(db):
    with pytest.raises(ev.BookingNotFound):
        ev.save_consumption(db, 'nope', [], 0)


# ---------- supplies ----------

def test_create_supplies_with_explicit_id_is_idempotent(db):
    first_id, first = ev.create_supplies(db, {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'estimated_quantity': 5}]},
                                         supplies_id='s-fixed')
    second_id, second = ev.create_supplies(db, {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'estimated_quantity': 9}]},
                                           supplies_id='s-fixed')
    assert first_id == second_id == 's-fixed'
    assert second['items'][0]['estimated_quantity'] == 5 and len(db.store['event_supplies']) == 1


def test_update_supplies_items_without_ids_is_a_400_not_a_crash(db):
    sid, _ = ev.create_supplies(db, {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'estimated_quantity': 5}]})
    with pytest.raises(ev.EventInventoryError) as err:
        ev.update_supplies(db, sid, {'items': [{'estimated_quantity': 1}]})
    assert err.value.status_code == 400  # CHANGED: it used to surface as a 500 KeyError


def test_supplies_lookup_helpers(db):
    assert ev.get_supplies_for_booking(db, 'b1') is None and ev.get_consumption_for_booking(db, 'b1') is None
    ev.create_supplies(db, {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'estimated_quantity': 5}]})
    ev.save_consumption(db, 'b1', [{'item_id': 'flour', 'quantity_returned': 1}], 0)
    assert ev.get_supplies_for_booking(db, 'b1')['booking_id'] == 'b1'
    assert ev.get_consumption_for_booking(db, 'b1')['items_consumed'][0]['actual_quantity_consumed'] == 4
