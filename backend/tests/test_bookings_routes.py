"""Characterization tests for POST /api/bookings/ and the (duplicated) price calculation.

Pins the behavior BEFORE the logic moves to services/booking_service.py. This endpoint is PUBLIC
(the website posts to it), so it must keep answering exactly the same.
"""
import itertools
import os
import sys

import pytest
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402
from routes import bookings_routes  # noqa: E402
from services import booking_service  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402


@pytest.fixture
def sent(monkeypatch):
    """Replace the outgoing notifications and record them"""
    calls = {'whatsapp': [], 'email': []}

    async def fake_whatsapp(phone, template, booking):
        calls['whatsapp'].append((phone, template, booking['id']))

    monkeypatch.setattr(booking_service, 'send_whatsapp_template', fake_whatsapp)
    monkeypatch.setattr(booking_service, 'send_admin_email_notification', lambda booking: calls['email'].append(booking['id']))
    monkeypatch.setenv('ADMIN_WHATSAPP_NUMBER', '+56911111111')
    monkeypatch.setenv('PARTNER_WHATSAPP_NUMBER', '+56922222222')
    return calls


@pytest.fixture
def db(monkeypatch):
    fake = FakeFirestore()
    monkeypatch.setattr(bookings_routes, 'get_db', lambda: fake)
    return fake


@pytest.fixture
def client(db, sent):
    app = Flask(__name__)
    app.register_blueprint(bookings_routes.bookings_bp)
    return app.test_client()


def _form(**overrides):
    data = {
        'client_name': 'Ana Pérez', 'client_email': 'Ana@Example.com', 'client_phone': '+56912345678',
        'service_type': 'workshop', 'event_type': 'birthday', 'event_date': '2026-11-14T16:00:00', 'event_time': '16:00',
        'location': 'Ñuñoa', 'duration_hours': 4, 'participants': 12, 'pizzeros_participants': 12,
        'party_participants': 0, 'pizza_quantity': 0, 'special_requests': 'Sin gluten', 'source': 'website',
    }
    data.update(overrides)
    return data


# ---------- validation ----------

def test_requires_a_body_service_type_and_source(client):
    assert client.post('/api/bookings/', json={}).get_json() == {'error': 'No data'}
    assert client.post('/api/bookings/', json=_form(service_type='')).get_json() == {'error': 'Missing service_type'}
    assert client.post('/api/bookings/', json=_form(source='')).get_json() == {'error': 'Missing source'}


def test_rejects_an_unknown_source(client):
    res = client.post('/api/bookings/', json=_form(source='carta'))
    assert res.status_code == 400 and res.get_json()['error'].startswith('Invalid source. Must be one of:')


def test_source_other_is_cleared_unless_the_source_is_other(client):
    assert client.post('/api/bookings/', json=_form(source='website', source_other='x')).get_json()['source_other'] == ''
    assert client.post('/api/bookings/', json=_form(source='other', source_other='Radio')).get_json()['source_other'] == 'Radio'


# ---------- creation ----------

def test_booking_is_created_pending_with_price_and_notes(client, db):
    res = client.post('/api/bookings/', json=_form())
    body = res.get_json()
    assert res.status_code == 201
    assert body['status'] == 'pending' and body['notes'] == 'Sin gluten'
    assert body['estimated_price'] == 12 * 10500  # 11-14 participants tier
    assert body['event_date'] == '2026-11-14T16:00:00'  # stored exactly as sent
    stored = db.store['bookings'][body['id']]
    assert stored['client_name'] == 'Ana Pérez' and stored['status'] == 'pending'


def test_comuna_lejana_extra_is_added_to_the_price(client):
    assert client.post('/api/bookings/', json=_form(comuna_lejana_extra=20000)).get_json()['estimated_price'] == 12 * 10500 + 20000


def test_notes_fall_back_to_notes_field(client):
    assert client.post('/api/bookings/', json=_form(special_requests='', notes='del admin')).get_json()['notes'] == 'del admin'


# ---------- customers ----------

def test_new_email_creates_a_customer_and_links_it(client, db):
    body = client.post('/api/bookings/', json=_form()).get_json()
    customer = db.store['customers'][body['customer_id']]
    assert customer['email'] == 'ana@example.com' and customer['name'] == 'Ana Pérez'
    assert customer['phone'] == '+56912345678' and customer['is_active'] is True
    # Latent quirk pinned on purpose: created with 1 and then incremented, so the first booking counts 2
    assert customer['total_bookings'] == 2


def test_known_email_links_the_existing_customer_and_counts_the_booking(client, db):
    first = client.post('/api/bookings/', json=_form()).get_json()
    second = client.post('/api/bookings/', json=_form(client_email='ANA@example.com ')).get_json()
    assert second['customer_id'] == first['customer_id'] and len(db.store['customers']) == 1


def test_no_email_means_no_customer(client, db):
    body = client.post('/api/bookings/', json=_form(client_email='')).get_json()
    assert body['customer_id'] is None and 'customers' not in db.store


# ---------- notifications ----------

def test_admin_and_partner_are_notified_by_whatsapp_and_the_admin_by_email(client, sent):
    body = client.post('/api/bookings/', json=_form()).get_json()
    assert sent['whatsapp'] == [('+56911111111', 'new_booking', body['id']), ('+56922222222', 'new_booking', body['id'])]
    assert sent['email'] == [body['id']]


def test_notification_failures_never_fail_the_booking(client, monkeypatch):
    async def boom(*args):
        raise RuntimeError('twilio down')

    def boom_email(booking):
        raise RuntimeError('smtp down')

    monkeypatch.setattr(booking_service, 'send_whatsapp_template', boom)
    monkeypatch.setattr(booking_service, 'send_admin_email_notification', boom_email)
    assert client.post('/api/bookings/', json=_form()).status_code == 201


# ---------- the two copies of calculate_estimated_price ----------

SERVICES = ['workshop', 'pizzeros', 'pizza_party', 'party', 'workshop,pizza_party', 'pizzeros,party', 'nope', '']
COUNTS = [0, 1, 8, 10, 11, 14, 15, 19, 20, 35]


@pytest.mark.parametrize('service', SERVICES)
def test_both_price_functions_agree_everywhere(service):
    for pizzeros, party, participants, pizzas in itertools.product(COUNTS, [0, 9, 20], [0, 12], [0, 10, 20]):
        a = main.calculate_estimated_price(service, pizzeros, party, participants, pizzas)
        b = bookings_routes.calculate_estimated_price(service, pizzeros, party, participants, pizzas)
        assert a == b, (service, pizzeros, party, participants, pizzas)


def test_known_prices():
    price = bookings_routes.calculate_estimated_price
    assert price('workshop', pizzeros_participants=8) == 135000          # minimum for up to 10
    assert price('workshop', pizzeros_participants=12) == 126000
    assert price('workshop', pizzeros_participants=20) == 180000
    assert price('pizza_party', pizza_quantity=10) == 119900
    assert price('pizza_party', pizza_quantity=20) == 20 * 10791          # 10 % off from 20 pizzas
    assert price('workshop,pizza_party', pizzeros_participants=12, pizza_quantity=10) == 126000 + 119900
    assert price('workshop', participants=12) == 126000                  # legacy field
    assert price('workshop', pizzeros_participants=8, comuna_lejana_extra=20000) == 155000
