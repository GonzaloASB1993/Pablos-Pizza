"""MercadoPago webhook: x-signature verification (log-only by default), reference/amount checks, idempotent append"""
import hashlib
import hmac
import logging
import os
import sys
import time

import pytest
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes import payments_routes  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402

SECRET = 'test-webhook-secret'
BOOKING = 'booking-1'


def sign(data_id, request_id='req-1', ts=None, secret=SECRET):
    ts = str(ts if ts is not None else int(time.time() * 1000))
    parts = []
    if data_id is not None:
        data_id = data_id.lower() if data_id.isalnum() else data_id
        parts.append(f'id:{data_id};')
    if request_id is not None:
        parts.append(f'request-id:{request_id};')
    parts.append(f'ts:{ts};')
    digest = hmac.new(secret.encode(), ''.join(parts).encode(), hashlib.sha256).hexdigest()
    return {'x-signature': f'ts={ts},v1={digest}', **({'x-request-id': request_id} if request_id is not None else {})}


class FakeSdk:
    def __init__(self, payments):
        self.payments = payments
        self.asked = []

    def payment(self):
        return self

    def get(self, payment_id):
        self.asked.append(payment_id)
        return {'status': 200, 'response': self.payments.get(str(payment_id), {})}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('SKIP_NOTIFICATIONS', 'true')
    monkeypatch.delenv('MP_WEBHOOK_SECRET', raising=False)
    monkeypatch.delenv('MP_WEBHOOK_ENFORCE', raising=False)
    monkeypatch.setattr(payments_routes, '_secret_missing_logged', False)
    monkeypatch.setattr(payments_routes, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))


@pytest.fixture
def db(monkeypatch):
    fake = FakeFirestore()
    fake.collection('bookings').document(BOOKING).set({
        'id': BOOKING, 'client_name': 'Ana', 'estimated_price': 100000, 'payments': [],
        'payment_summary': {'payment_status': 'pending', 'balance_due': 100000}})
    fake.collection('mp_payments').document('mp-doc-1').set({
        'id': 'mp-doc-1', 'booking_id': BOOKING, 'amount': 30000, 'status': 'pending'})
    monkeypatch.setattr(payments_routes, 'get_db', lambda: fake)
    return fake


@pytest.fixture
def sdk(monkeypatch):
    fake = FakeSdk({'555': {'external_reference': BOOKING, 'status': 'approved', 'transaction_amount': 30000}})
    monkeypatch.setattr(payments_routes, 'get_mp_sdk', lambda: fake)
    return fake


@pytest.fixture
def client(db, sdk):
    app = Flask(__name__)
    app.register_blueprint(payments_routes.payments_bp)
    return app.test_client()


def _post(client, payment_id='555', headers=None, query=True):
    url = f'/api/payments/webhook?data.id={payment_id}&type=payment' if query else '/api/payments/webhook'
    return client.post(url, json={'type': 'payment', 'data': {'id': payment_id}}, headers=headers or {})


def _payments(db):
    return db.store['bookings'][BOOKING]['payments']


# ---------- signature ----------

def test_a_valid_signature_is_processed(client, db, monkeypatch):
    monkeypatch.setenv('MP_WEBHOOK_SECRET', SECRET)
    monkeypatch.setenv('MP_WEBHOOK_ENFORCE', 'true')
    assert _post(client, headers=sign('555')).status_code == 200
    assert len(_payments(db)) == 1


def test_enforce_rejects_a_bad_missing_old_or_foreign_signature_with_401(client, db, sdk, monkeypatch):
    monkeypatch.setenv('MP_WEBHOOK_SECRET', SECRET)
    monkeypatch.setenv('MP_WEBHOOK_ENFORCE', 'true')
    old = int((time.time() - 600) * 1000)
    for headers in ({}, sign('555', secret='other'), sign('555', ts=old), sign('999'), {'x-signature': 'garbage'}):
        assert _post(client, headers=headers).status_code == 401
    assert _payments(db) == [] and sdk.asked == []  # nothing was fetched from MP nor registered


def test_default_mode_only_logs_and_keeps_processing(client, db, monkeypatch, caplog):
    monkeypatch.setenv('MP_WEBHOOK_SECRET', SECRET)
    with caplog.at_level(logging.WARNING):
        assert _post(client, headers=sign('555', secret='other')).status_code == 200
    assert len(_payments(db)) == 1
    assert any('signature' in r.getMessage().lower() for r in caplog.records)
    assert SECRET not in caplog.text


def test_missing_signature_in_default_mode_logs_a_warning_and_processes(client, db, monkeypatch, caplog):
    monkeypatch.setenv('MP_WEBHOOK_SECRET', SECRET)
    with caplog.at_level(logging.WARNING):
        assert _post(client).status_code == 200
    assert len(_payments(db)) == 1 and 'signature' in caplog.text.lower()


def test_without_a_secret_nothing_is_verified_and_the_log_happens_once(client, db, caplog):
    with caplog.at_level(logging.INFO):
        assert _post(client, headers={'x-signature': 'ts=1,v1=bad'}).status_code == 200
        _post(client, payment_id='556')
    assert len(_payments(db)) == 1
    assert caplog.text.count('MP_WEBHOOK_SECRET') == 1


def test_signature_uses_lowercased_alphanumeric_data_id_and_omits_missing_request_id(client, db, monkeypatch, sdk):
    monkeypatch.setenv('MP_WEBHOOK_SECRET', SECRET)
    monkeypatch.setenv('MP_WEBHOOK_ENFORCE', 'true')
    sdk.payments['ABC123'] = {'external_reference': BOOKING, 'status': 'approved', 'transaction_amount': 30000}
    assert _post(client, payment_id='ABC123', headers=sign('ABC123', request_id=None)).status_code == 200
    assert len(_payments(db)) == 1


def test_the_body_is_never_logged(client, db, capsys, caplog):
    caplog.set_level(logging.DEBUG)
    client.post('/api/payments/webhook?data.id=555', json={'type': 'payment', 'data': {'id': '555'}, 'secret_field': 'TOPSECRETBODY'})
    assert 'TOPSECRETBODY' not in capsys.readouterr().out + caplog.text


# ---------- reference / amount ----------

def test_unknown_reference_is_not_registered(client, db, sdk):
    sdk.payments['555']['external_reference'] = 'no-such-booking'
    assert _post(client).status_code == 200
    assert _payments(db) == []


def test_a_booking_without_any_mp_payment_is_not_registered(client, db):
    db.store['mp_payments'].clear()
    assert _post(client).status_code == 200 and _payments(db) == []


def test_an_amount_that_matches_no_preference_is_not_registered(client, db, sdk):
    sdk.payments['555']['transaction_amount'] = 99999
    assert _post(client).status_code == 200 and _payments(db) == []


# ---------- registration / idempotence ----------

def test_approved_payment_is_registered_once_with_summary_and_mp_doc_updated(client, db):
    assert _post(client).status_code == 200
    assert _post(client).status_code == 200  # MP retries the notification
    payments = _payments(db)
    assert len(payments) == 1 and payments[0]['amount'] == 30000 and payments[0]['mp_payment_id'] == '555'
    assert db.store['bookings'][BOOKING]['payment_summary']['total_paid'] == 30000
    assert db.store['mp_payments']['mp-doc-1']['status'] == 'approved'
    assert db.store['mp_payments']['mp-doc-1']['mp_payment_id'] == '555'


def test_legacy_payment_registered_only_in_notes_counts_as_registered(client, db):
    db.collection('bookings').document(BOOKING).update({'payments': [{'amount': 30000, 'notes': 'Pago online MercadoPago #555'}]})
    assert _post(client).status_code == 200
    assert len(_payments(db)) == 1


def test_a_crash_between_steps_is_recovered_by_the_retry(client, db):
    # the mp_payments doc already says approved for this id but the booking never got the payment
    db.collection('mp_payments').document('mp-doc-1').update({'status': 'approved', 'mp_payment_id': '555'})
    assert _post(client).status_code == 200
    assert len(_payments(db)) == 1


def test_non_approved_status_only_updates_the_mp_record(client, db, sdk):
    sdk.payments['555']['status'] = 'rejected'
    assert _post(client).status_code == 200
    assert _payments(db) == [] and db.store['mp_payments']['mp-doc-1']['status'] == 'rejected'


def test_internal_errors_still_answer_200(client, db, monkeypatch):
    def boom():
        raise RuntimeError('mp down')
    monkeypatch.setattr(payments_routes, 'get_mp_sdk', boom)
    assert _post(client).status_code == 200


def test_notification_without_payment_id_is_ignored(client):
    assert client.post('/api/payments/webhook', json={}).status_code == 200


# ---------- create-preference description ----------

def test_description_is_capped_at_200_chars(client, db):
    res = client.post('/api/payments/create-preference', json={'booking_id': BOOKING, 'amount': 1000, 'description': 'x' * 201})
    assert res.status_code == 400 and 'description' in res.get_json()['error']
