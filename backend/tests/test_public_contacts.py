"""Hardening of the PUBLIC contact form: POST /api/contacts (no token)"""
import os
import sys

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
def client(db, monkeypatch):
    monkeypatch.setattr(main.limiter, 'enabled', False)
    monkeypatch.setitem(main.app.config, 'TESTING', True)
    return main.app.test_client()


def _msg(**overrides):
    data = {'name': 'Ana', 'email': 'ana@example.com', 'phone': '+56912345678', 'subject': 'Cotización',
            'message': 'Hola, quiero cotizar', 'priority': 'normal'}
    data.update(overrides)
    return data


def test_a_legitimate_message_is_created(client, db):
    res = client.post('/api/contacts', json=_msg())
    body = res.get_json()
    assert res.status_code == 201
    stored = db.store['contacts'][body['id']]
    assert stored['name'] == 'Ana' and stored['status'] == 'pending' and stored['response_sent'] is False


def test_priority_is_never_chosen_by_the_client(client, db):
    body = client.post('/api/contacts', json=_msg(priority='urgent')).get_json()
    assert body['priority'] == 'normal' and db.store['contacts'][body['id']]['priority'] == 'normal'


def test_extra_fields_are_dropped(client, db):
    body = client.post('/api/contacts', json=_msg(status='resolved', response_sent=True, assigned_to='me', admin_notes='x',
                                                   id='forced')).get_json()
    stored = db.store['contacts'][body['id']]
    assert stored['status'] == 'pending' and stored['response_sent'] is False and stored['id'] != 'forced'
    assert 'assigned_to' not in stored and 'admin_notes' not in stored


@pytest.mark.parametrize('field,value', [
    ('email', 'no-es-email'), ('email', ''), ('name', ''), ('name', 'x' * 101), ('subject', ''), ('subject', 'x' * 201),
    ('message', ''), ('message', 'x' * 1001), ('phone', '1' * 21), ('email', 'a@b.cl' + 'x' * 120), ('name', 123),
], ids=lambda v: str(v)[:20])
def test_invalid_values_are_a_400(client, field, value):
    res = client.post('/api/contacts', json=_msg(**{field: value}))
    assert res.status_code == 400 and res.get_json()['error']


def test_missing_required_field_and_non_object_body_are_400(client):
    data = _msg()
    del data['subject']
    assert client.post('/api/contacts', json=data).status_code == 400
    assert client.post('/api/contacts', json=['x']).status_code == 400
    assert client.post('/api/contacts', json={}).status_code == 400


def test_phone_is_optional_and_limits_are_inclusive(client):
    data = _msg(name='n' * 100, subject='s' * 200, message='m' * 1000)
    del data['phone']
    assert client.post('/api/contacts', json=data).status_code == 201
