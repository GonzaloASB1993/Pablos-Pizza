"""inventory_service primitives behind undo: exact or not done"""
import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402,F401
from services import inventory_service as inv  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402
from tests.undo_support import doc, item, seed_item  # noqa: E402


@pytest.fixture
def db():
    return FakeFirestore()


_CLOCK = [datetime(2026, 10, 1, 12, 0, 0)]


def _buy(db, movement_id, quantity=5, cost=1200, item_id='flour'):
    """A purchase stamped one minute after the previous one (the real clock can tie on a fast machine)"""
    moved = inv.register_movement(db, item_id, 'purchase', quantity, cost, movement_id=movement_id)
    _CLOCK[0] += timedelta(minutes=1)
    db.collection('inventory_movements').document(movement_id).update({'created_at': _CLOCK[0]})
    return moved


def test_revert_restores_stock_and_average_exactly(db):
    seed_item(db, stock=10, avg=1000)
    _buy(db, 'm1', quantity=5, cost=1600)                   # avg 1000 -> 1200, stock 15
    assert item(db)['weighted_avg_cost'] == pytest.approx(1200)
    batch = db.batch()
    done = inv.revert_movement_exact(db, 'm1', 'r1', 'Deshacer compra', batch)
    assert item(db)['current_stock'] == 15                  # nothing is written until the caller commits
    batch.commit()

    stored = item(db)
    assert stored['current_stock'] == 10 and stored['weighted_avg_cost'] == 1000 and stored['cost_per_unit'] == 1000
    assert stored['total_value'] == 10000 and stored['needs_restock'] is False
    original, reversal = doc(db, 'inventory_movements', 'm1'), doc(db, 'inventory_movements', 'r1')
    assert original['reverted'] is True and original['reversal_movement_id'] == 'r1'
    assert reversal['movement_type'] == 'reversal' and reversal['reverts_movement_id'] == 'm1' and reversal['quantity'] == -5
    assert (reversal['stock_before'], reversal['stock_after']) == (15, 10)
    assert done['reversals'] == [{'movement_id': 'm1', 'reversal_id': 'r1', 'item_id': 'flour'}]
    assert done['snapshots']['items']['flour']['current_stock'] == 15


def test_a_later_movement_of_the_same_item_blocks_the_revert(db):
    seed_item(db, stock=10, avg=1000)
    _buy(db, 'm1')
    _buy(db, 'm2', quantity=1)
    with pytest.raises(inv.MovementNotRevertible) as caught:
        inv.check_movement_revertible(db, 'm1')
    assert caught.value.code == 'later_movements' and 'Harina' in caught.value.message and 'conteo' in caught.value.message
    inv.check_movement_revertible(db, 'm2')                 # the newest one is fine


def test_a_movement_of_another_item_does_not_block(db):
    seed_item(db, stock=10, avg=1000)
    seed_item(db, 'cheese', name='Queso', stock=3, avg=5000)
    _buy(db, 'm1')
    inv.register_movement(db, 'cheese', 'purchase', 1, 5000, movement_id='m-cheese')
    inv.check_movement_revertible(db, 'm1')


def test_stock_edited_by_hand_blocks_the_revert(db):
    seed_item(db, stock=10, avg=1000)
    _buy(db, 'm1')
    inv.set_stock(db, 'flour', 99)                           # the legacy endpoint: no movement, but the state moved
    with pytest.raises(inv.MovementNotRevertible) as caught:
        inv.check_movement_revertible(db, 'm1')
    assert caught.value.code == 'stock_changed'


def test_average_changed_blocks_the_revert(db):
    seed_item(db, stock=10, avg=1000)
    _buy(db, 'm1')
    db.collection('inventory').document('flour').update({'weighted_avg_cost': 7777})
    with pytest.raises(inv.MovementNotRevertible) as caught:
        inv.check_movement_revertible(db, 'm1')
    assert caught.value.code == 'stock_changed'


def test_missing_reverted_reversal_and_missing_item(db):
    seed_item(db, stock=10, avg=1000)
    with pytest.raises(inv.MovementNotRevertible) as caught:
        inv.check_movement_revertible(db, 'nope')
    assert caught.value.code == 'missing'

    _buy(db, 'm1')
    batch = db.batch()
    inv.revert_movement_exact(db, 'm1', 'r1', 'x', batch)
    batch.commit()
    with pytest.raises(inv.MovementNotRevertible) as caught:
        inv.check_movement_revertible(db, 'm1')
    assert caught.value.code == 'already_reverted'
    with pytest.raises(inv.MovementNotRevertible) as caught:
        inv.check_movement_revertible(db, 'r1')
    assert caught.value.code == 'is_reversal'

    _buy(db, 'm2')
    db.collection('inventory').document('flour').delete()
    with pytest.raises(inv.MovementNotRevertible) as caught:
        inv.check_movement_revertible(db, 'm2')
    assert caught.value.code == 'item_missing'


def test_two_movements_of_one_item_are_reverted_together_newest_first(db):
    seed_item(db, stock=10, avg=1000)
    _buy(db, 'm1', quantity=5, cost=1600)
    _buy(db, 'm2', quantity=5, cost=2000)
    plan = inv.check_movements_revertible(db, ['m1', 'm2'])
    assert [m['id'] for m in plan['items']['flour']['chain']] == ['m1', 'm2']
    batch = db.batch()
    inv.revert_movements_exact(db, [('m1', 'r1'), ('m2', 'r2')], 'x', batch, plan=plan)
    batch.commit()
    assert item(db)['current_stock'] == 10 and item(db)['weighted_avg_cost'] == 1000
    assert doc(db, 'inventory_movements', 'r2')['stock_before'] == 20 and doc(db, 'inventory_movements', 'r1')['stock_after'] == 10


def test_a_broken_chain_is_refused(db):
    seed_item(db, stock=10, avg=1000)
    _buy(db, 'm1')
    _buy(db, 'm2')
    db.collection('inventory_movements').document('m2').update({'stock_before': 999})
    with pytest.raises(inv.MovementNotRevertible) as caught:
        inv.check_movements_revertible(db, ['m1', 'm2'])
    assert caught.value.code == 'chain'


def test_aware_timestamps_from_firestore_compare_correctly(db):
    from datetime import timezone
    seed_item(db, stock=10, avg=1000)
    _buy(db, 'm1')
    _buy(db, 'm2', quantity=1)
    later = datetime.now(timezone.utc) + timedelta(seconds=5)
    db.collection('inventory_movements').document('m1').update({'created_at': datetime.now(timezone.utc) - timedelta(hours=1)})
    db.collection('inventory_movements').document('m2').update({'created_at': later})
    with pytest.raises(inv.MovementNotRevertible):
        inv.check_movement_revertible(db, 'm1')
    inv.check_movement_revertible(db, 'm2')


def test_item_update_fields_matches_update_item(db):
    seed_item(db, stock=10, avg=1000, min_stock=2)
    current = item(db)
    fields = inv.item_update_fields({'name': 'Harina 000', 'min_stock': 20}, current)
    assert fields['name'] == 'Harina 000' and fields['min_stock'] == 20.0 and fields['needs_restock'] is True
    inv.update_item(db, 'flour', {'name': 'Harina 000', 'min_stock': 20})
    assert item(db)['needs_restock'] is True and item(db)['name'] == 'Harina 000'
