"""Tests for what services/inventory_service.py does beyond the original endpoints"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import inventory_service as inv  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402


@pytest.fixture
def db():
    return FakeFirestore()


def _data(**overrides):
    data = {'name': 'Harina', 'category': 'Secos', 'current_stock': 0, 'min_stock': 5, 'max_stock': 50,
            'unit': 'kg', 'cost_per_unit': 1120}
    data.update(overrides)
    return data


def test_create_item_initializes_weighted_average_cost(db):
    item = inv.create_item(db, _data())
    assert item['weighted_avg_cost'] == 1120.0
    assert db.store['inventory'][item['id']]['weighted_avg_cost'] == 1120.0


@pytest.mark.parametrize('field', inv.REQUIRED_ITEM_FIELDS)
def test_create_item_reports_the_missing_field(db, field):
    data = _data()
    data.pop(field)
    with pytest.raises(inv.MissingField) as err:
        inv.create_item(db, data)
    assert str(err.value) == f'Missing {field}'
    assert 'inventory' not in db.store


def test_create_item_with_explicit_id_is_idempotent(db):
    first = inv.create_item(db, _data(), item_id='fixed-id')
    second = inv.create_item(db, _data(name='Otro nombre'), item_id='fixed-id')
    assert first['id'] == second['id'] == 'fixed-id'
    assert second['name'] == 'Harina'  # the stored item wins, nothing is overwritten
    assert len(db.store['inventory']) == 1


def test_create_item_extra_fields_are_stored(db):
    item = inv.create_item(db, _data(), extra={'source': 'ai_agent'})
    assert db.store['inventory'][item['id']]['source'] == 'ai_agent'


def test_movement_with_same_id_is_applied_once(db):
    item = inv.create_item(db, _data())
    first = inv.register_movement(db, item['id'], 'purchase', 25, 1120, movement_id='m1')
    second = inv.register_movement(db, item['id'], 'purchase', 25, 1120, movement_id='m1')

    assert first['already_applied'] is False and second['already_applied'] is True
    assert second['stock_after'] == first['stock_after'] == 25
    assert db.store['inventory'][item['id']]['current_stock'] == 25
    assert len(db.store['inventory_movements']) == 1


def test_stock_and_movement_are_written_in_a_single_batch(db, monkeypatch):
    item = inv.create_item(db, _data(current_stock=10))
    batches = []
    original = db.batch

    def spy():
        batch = original()
        batches.append(batch)
        return batch

    monkeypatch.setattr(db, 'batch', spy)
    inv.register_movement(db, item['id'], 'consumption', 3)
    assert len(batches) == 1


def test_rejected_movement_writes_nothing(db):
    item = inv.create_item(db, _data(current_stock=2))
    with pytest.raises(inv.InsufficientStock):
        inv.register_movement(db, item['id'], 'waste', 5)
    with pytest.raises(inv.InvalidMovement):
        inv.register_movement(db, item['id'], 'purchase', 0, 100)
    assert 'inventory_movements' not in db.store
    assert db.store['inventory'][item['id']]['current_stock'] == 2


def test_two_purchases_accumulate_weighted_cost_exactly(db):
    item = inv.create_item(db, _data())
    inv.register_movement(db, item['id'], 'purchase', 25, 1120)
    result = inv.register_movement(db, item['id'], 'purchase', 25, 1320)
    assert result['stock_after'] == 50 and result['avg_cost_after'] == 1220
