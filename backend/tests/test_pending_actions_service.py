"""Tests for the propose -> confirm workflow"""
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import pending_actions_service as pas  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402

USER = {'uid': 'u1', 'email': 'admin@example.com'}


class DummyPayload(BaseModel):
    description: str = Field(min_length=1)
    amount: int = Field(gt=0)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    # Fake transactions apply writes immediately, so the decorator is a passthrough
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))
    monkeypatch.setattr(pas, '_registry', {})


@pytest.fixture
def executed():
    return []


@pytest.fixture
def db(executed):
    def executor(db, payload, user):
        executed.append(payload)
        return {'dummy_id': f'd{len(executed)}'}

    pas.register_action_type('dummy', DummyPayload, executor)
    return FakeFirestore()


@pytest.fixture
def audits():
    calls = []
    return calls, (lambda *args, **kwargs: calls.append((args, kwargs)))


def _create(db, **overrides):
    params = dict(payload={'description': 'Bencina', 'amount': 25000}, summary='Gasto: Bencina', user=USER)
    params.update(overrides)
    return pas.create(db, 'dummy', **params)


def test_create_stores_a_pending_action_with_expiry(db):
    action = _create(db, warnings=['total no cuadra'], dedupe_hash='h1')
    stored = db.store['pending_actions'][action['id']]
    assert stored['status'] == 'pending'
    assert stored['created_by'] == USER
    assert stored['warnings'] == ['total no cuadra']
    assert stored['expires_at'] - stored['created_at'] == timedelta(hours=24)
    assert stored['payload'] == {'description': 'Bencina', 'amount': 25000}


def test_create_does_not_run_the_executor(db, executed):
    _create(db)
    assert executed == []


def test_create_rejects_invalid_payload(db):
    with pytest.raises(pas.InvalidPayload) as err:
        _create(db, payload={'description': '', 'amount': -5})
    assert err.value.errors
    assert 'pending_actions' not in db.store


def test_unknown_type_is_rejected(db):
    with pytest.raises(pas.PendingActionError):
        pas.create(db, 'nope', payload={}, summary='x', user=USER)


def test_confirm_executes_once_and_audits(db, executed, audits):
    calls, audit = audits
    action = _create(db)
    result = pas.confirm(db, action['id'], USER, audit=audit)

    assert len(executed) == 1
    assert result['status'] == 'confirmed'
    assert result['result'] == {'dummy_id': 'd1'}
    stored = db.store['pending_actions'][action['id']]
    assert stored['status'] == 'confirmed' and stored['confirmed_at'] is not None

    (args, kwargs), = calls
    assert args[:4] == ('admin@example.com', 'confirm', 'pending_action', action['id'])
    assert kwargs['metadata'] == {'source': 'ai_agent', 'uid': 'u1'}


def test_confirming_twice_does_not_duplicate(db, executed, audits):
    _, audit = audits
    action = _create(db)
    first = pas.confirm(db, action['id'], USER, audit=audit)
    second = pas.confirm(db, action['id'], USER, audit=audit)

    assert len(executed) == 1
    assert second['already_confirmed'] is True
    assert second['result'] == first['result']


def test_confirm_uses_edited_payload_and_revalidates(db, executed, audits):
    _, audit = audits
    action = _create(db)

    with pytest.raises(pas.InvalidPayload):
        pas.confirm(db, action['id'], USER, edited_payload={'description': 'x', 'amount': 0}, audit=audit)
    assert executed == []
    assert db.store['pending_actions'][action['id']]['status'] == 'pending'

    pas.confirm(db, action['id'], USER, edited_payload={'description': 'Peaje', 'amount': 3000}, audit=audit)
    assert executed[0].description == 'Peaje' and executed[0].amount == 3000
    assert db.store['pending_actions'][action['id']]['payload']['description'] == 'Peaje'


def test_cancelled_action_cannot_be_confirmed(db, executed, audits):
    _, audit = audits
    action = _create(db)
    pas.cancel(db, action['id'])
    with pytest.raises(pas.ActionConflict):
        pas.confirm(db, action['id'], USER, audit=audit)
    assert executed == []


def test_expired_action_cannot_be_confirmed(db, executed, audits):
    _, audit = audits
    action = _create(db)
    db.store['pending_actions'][action['id']]['expires_at'] = datetime.utcnow() - timedelta(minutes=1)
    with pytest.raises(pas.ActionExpired):
        pas.confirm(db, action['id'], USER, audit=audit)
    assert db.store['pending_actions'][action['id']]['status'] == 'expired'
    assert executed == []


def test_timezone_aware_expiry_from_firestore_is_handled(db):
    action = _create(db)
    db.store['pending_actions'][action['id']]['expires_at'] = datetime.now(timezone.utc) + timedelta(hours=1)
    assert pas.get(db, action['id'])['status'] == 'pending'
    db.store['pending_actions'][action['id']]['expires_at'] = datetime.now(timezone.utc) - timedelta(hours=1)
    assert pas.get(db, action['id'])['status'] == 'expired'


def test_executor_failure_marks_failed_and_allows_retry(db, audits):
    _, audit = audits
    attempts = []

    def flaky(db, payload, user):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError('firestore down')
        return {'ok': True}

    pas.register_action_type('flaky', DummyPayload, flaky)
    action = pas.create(db, 'flaky', payload={'description': 'x', 'amount': 1}, summary='s', user=USER)

    with pytest.raises(RuntimeError):
        pas.confirm(db, action['id'], USER, audit=audit)
    stored = db.store['pending_actions'][action['id']]
    assert stored['status'] == 'failed' and 'firestore down' in stored['error']

    result = pas.confirm(db, action['id'], USER, audit=audit)
    assert result['status'] == 'confirmed' and len(attempts) == 2


def test_processing_action_is_a_conflict(db, executed, audits):
    _, audit = audits
    action = _create(db)
    db.store['pending_actions'][action['id']]['status'] = 'processing'
    with pytest.raises(pas.ActionConflict):
        pas.confirm(db, action['id'], USER, audit=audit)
    assert executed == []


def test_cancel_rules(db, audits):
    _, audit = audits
    action = _create(db)
    assert pas.cancel(db, action['id'])['status'] == 'cancelled'
    assert pas.cancel(db, action['id'])['status'] == 'cancelled'  # idempotent

    other = _create(db)
    pas.confirm(db, other['id'], USER, audit=audit)
    with pytest.raises(pas.ActionConflict):
        pas.cancel(db, other['id'])


def test_get_unknown_action(db):
    with pytest.raises(pas.ActionNotFound):
        pas.get(db, 'missing')


def test_find_by_dedupe_hash_ignores_cancelled(db):
    kept = _create(db, dedupe_hash='h1')
    gone = _create(db, dedupe_hash='h1')
    pas.cancel(db, gone['id'])
    _create(db, dedupe_hash='other')

    found = pas.find_by_dedupe_hash(db, 'h1')
    assert [a['id'] for a in found] == [kept['id']]
    assert pas.find_by_dedupe_hash(db, None) == []


def test_serialize_makes_datetimes_json_friendly(db):
    action = pas.serialize(_create(db))
    assert action['created_at'].endswith('Z') and action['expires_at'].endswith('Z')
    assert action['confirmed_at'] is None
