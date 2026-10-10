"""Characterization tests for /api/expenses: pin current behavior before extracting services"""
import os
import sys
from datetime import datetime

import pytest
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes import expenses_routes  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402


@pytest.fixture
def db(monkeypatch):
    fake = FakeFirestore()
    monkeypatch.setattr(expenses_routes, "get_db", lambda: fake)
    return fake


@pytest.fixture
def client(db):
    app = Flask(__name__)
    app.register_blueprint(expenses_routes.expenses_bp)
    return app.test_client()


# ---------- fixed expenses ----------

def test_create_fixed_expense_applies_defaults(client, db):
    res = client.post('/api/expenses/fixed', json={'description': 'Arriendo', 'amount': '350000'})
    assert res.status_code == 201
    body = res.get_json()
    assert body['description'] == 'Arriendo'
    assert body['amount'] == 350000.0
    assert body['category'] == 'general'
    assert body['notes'] == ''
    assert body['is_active'] is True
    assert body['effective_from'] is None and body['effective_to'] is None
    assert db.store['fixed_expenses'][body['id']]['amount'] == 350000.0


def test_create_fixed_expense_keeps_optional_fields(client):
    res = client.post('/api/expenses/fixed', json={
        'description': 'Seguro', 'amount': 10000, 'category': 'seguros', 'notes': 'anual',
        'is_active': False, 'effective_from': '2026-01', 'effective_to': ''})
    body = res.get_json()
    assert body['category'] == 'seguros' and body['notes'] == 'anual'
    assert body['is_active'] is False
    assert body['effective_from'] == '2026-01'
    assert body['effective_to'] is None  # empty string normalized to None


@pytest.mark.parametrize('payload,missing', [
    ({'amount': 1}, 'description'),
    ({'description': 'x'}, 'amount'),
])
def test_create_fixed_expense_requires_fields(client, payload, missing):
    res = client.post('/api/expenses/fixed', json=payload)
    assert res.status_code == 400
    assert res.get_json() == {'error': f'Missing {missing}'}


def test_create_fixed_expense_without_body(client):
    res = client.post('/api/expenses/fixed', json={})
    assert res.status_code == 400
    assert res.get_json() == {'error': 'No data'}


def test_list_fixed_expenses_newest_first(client, db):
    first = client.post('/api/expenses/fixed', json={'description': 'A', 'amount': 1}).get_json()
    second = client.post('/api/expenses/fixed', json={'description': 'B', 'amount': 2}).get_json()
    # datetime.now() can repeat on Windows; pin the timestamps so the order is deterministic
    db.store['fixed_expenses'][first['id']]['created_at'] = datetime(2026, 1, 1)
    db.store['fixed_expenses'][second['id']]['created_at'] = datetime(2026, 1, 2)
    res = client.get('/api/expenses/fixed')
    assert res.status_code == 200
    ids = [e['id'] for e in res.get_json()]
    assert set(ids) == {first['id'], second['id']}
    assert ids[0] == second['id']


def test_update_fixed_expense_changes_only_given_fields(client):
    created = client.post('/api/expenses/fixed', json={'description': 'A', 'amount': 1, 'category': 'x'}).get_json()
    res = client.put(f"/api/expenses/fixed/{created['id']}", json={'amount': '99', 'effective_to': '2026-12'})
    assert res.status_code == 200
    body = res.get_json()
    assert body['amount'] == 99.0
    assert body['description'] == 'A' and body['category'] == 'x'
    assert body['effective_to'] == '2026-12'
    assert body['id'] == created['id']


def test_update_fixed_expense_not_found(client):
    res = client.put('/api/expenses/fixed/nope', json={'amount': 1})
    assert res.status_code == 404
    assert res.get_json() == {'error': 'Not found'}


def test_delete_fixed_expense(client, db):
    created = client.post('/api/expenses/fixed', json={'description': 'A', 'amount': 1}).get_json()
    res = client.delete(f"/api/expenses/fixed/{created['id']}")
    assert res.status_code == 200 and res.get_json() == {'message': 'Deleted'}
    assert created['id'] not in db.store['fixed_expenses']
    assert client.delete(f"/api/expenses/fixed/{created['id']}").status_code == 404


# ---------- variable expenses ----------

def test_create_variable_expense(client, db):
    res = client.post('/api/expenses/variable', json={
        'description': 'Bencina', 'amount': 25000, 'year': '2026', 'month': '10', 'category': 'transporte'})
    assert res.status_code == 201
    body = res.get_json()
    assert body['year'] == 2026 and body['month'] == 10
    assert body['amount'] == 25000.0 and body['category'] == 'transporte'
    assert body['id'] in db.store['variable_expenses']


@pytest.mark.parametrize('missing', ['description', 'amount', 'year', 'month'])
def test_create_variable_expense_requires_fields(client, missing):
    payload = {'description': 'x', 'amount': 1, 'year': 2026, 'month': 1}
    payload.pop(missing)
    res = client.post('/api/expenses/variable', json=payload)
    assert res.status_code == 400
    assert res.get_json() == {'error': f'Missing {missing}'}


def test_create_variable_expense_with_garbage_amount_is_500(client):
    # Current behavior (no validation): float() blows up and the route answers 500
    res = client.post('/api/expenses/variable', json={
        'description': 'x', 'amount': 'mucho', 'year': 2026, 'month': 1})
    assert res.status_code == 500


def test_list_variable_expenses_filters_by_year_and_month(client):
    for month in (9, 10, 10):
        client.post('/api/expenses/variable', json={'description': f'g{month}', 'amount': 1, 'year': 2026, 'month': month})
    client.post('/api/expenses/variable', json={'description': 'old', 'amount': 1, 'year': 2025, 'month': 10})

    assert len(client.get('/api/expenses/variable').get_json()) == 4
    assert len(client.get('/api/expenses/variable?year=2026').get_json()) == 3
    assert len(client.get('/api/expenses/variable?year=2026&month=10').get_json()) == 2
    assert client.get('/api/expenses/variable?year=2030').get_json() == []


def test_update_variable_expense(client):
    created = client.post('/api/expenses/variable', json={'description': 'a', 'amount': 1, 'year': 2026, 'month': 1}).get_json()
    res = client.put(f"/api/expenses/variable/{created['id']}", json={'month': '3', 'notes': 'ok'})
    body = res.get_json()
    assert res.status_code == 200
    assert body['month'] == 3 and body['notes'] == 'ok' and body['year'] == 2026


def test_update_and_delete_variable_expense_not_found(client):
    assert client.put('/api/expenses/variable/nope', json={'amount': 1}).status_code == 404
    assert client.delete('/api/expenses/variable/nope').status_code == 404


def test_delete_variable_expense(client, db):
    created = client.post('/api/expenses/variable', json={'description': 'a', 'amount': 1, 'year': 2026, 'month': 1}).get_json()
    assert client.delete(f"/api/expenses/variable/{created['id']}").status_code == 200
    assert created['id'] not in db.store['variable_expenses']


# ---------- monthly tax ----------

def test_tax_defaults_to_zero_and_roundtrips(client):
    assert client.get('/api/expenses/tax?year=2026&month=10').get_json() == {'amount': 0}
    res = client.post('/api/expenses/tax', json={'year': 2026, 'month': 10, 'amount': '1500'})
    assert res.status_code == 200
    assert client.get('/api/expenses/tax?year=2026&month=10').get_json() == {'amount': 1500.0}


def test_tax_requires_year_and_month(client):
    assert client.get('/api/expenses/tax').status_code == 400
    assert client.post('/api/expenses/tax', json={'year': 2026}).status_code == 400
