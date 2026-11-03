"""Night surcharge: percentage from settings/recargo_nocturno applied to the SERVICES subtotal (never to the comuna charge)"""
import os
import sys

import pytest
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes import bookings_routes, settings_routes  # noqa: E402
from services import booking_service as bks  # noqa: E402
from tests.conftest import authenticate_as_admin  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402


@pytest.mark.parametrize('hhmm,expected', [
    ('21:30', False), ('21:59', False), ('22:00', True), ('23:30', True), ('23:59', True), ('00:00', True),
    ('03:15', True), ('07:59', True), ('08:00', False), ('12:00', False), ('7:30', True), ('9:00', False),
    ('', False), (None, False), ('noche', False), ('25:00', False), ('22:99', False), (22, False),
])
def test_is_night_time(hhmm, expected):
    assert bks.is_night_time(hhmm) is expected


class _Broken:
    def collection(self, name):
        raise RuntimeError('firestore down')


def test_default_is_20_percent_when_there_is_no_setting():
    db = FakeFirestore()
    assert bks.recargo_nocturno_pct(db, '2026-10-20T22:00:00', '22:00') == 20
    assert bks.recargo_nocturno_pct(db, '2026-10-20T21:30:00', '21:30') == 0


def test_configured_percentage_zero_turns_it_off_and_invalid_values_fall_back():
    db = FakeFirestore()
    for value, expected in [(35, 35), (0, 0), ('abc', 20), (-5, 20), (101, 20), (True, 20), (12.5, 20), (None, 20)]:
        db.store['settings'] = {'recargo_nocturno': {'porcentaje': value}}
        assert bks.recargo_nocturno_pct(db, '2026-10-20T23:00:00', '23:00') == expected, value


def test_firestore_failure_uses_the_default_and_no_db_too():
    assert bks.recargo_nocturno_pct(_Broken(), '2026-10-20T23:00:00', '23:00') == 20
    assert bks.recargo_nocturno_pct(None, '2026-10-20T23:00:00', '23:00') == 20


def test_either_the_time_or_the_hour_inside_the_date_triggers_it():
    db = FakeFirestore()
    assert bks.recargo_nocturno_pct(db, '2026-10-20T10:00:00', '23:00') == 20   # event_time is night
    assert bks.recargo_nocturno_pct(db, '2026-10-20T23:00:00', '10:00') == 20   # hour in the date is night: no dodging
    assert bks.recargo_nocturno_pct(db, '2026-10-20T10:00:00', '10:00') == 0
    assert bks.recargo_nocturno_pct(db, '2026-10-20T10:00:00', '') == 0


def test_a_date_without_hour_is_not_midnight():
    db = FakeFirestore()
    assert bks.recargo_nocturno_pct(db, '2026-10-20', '') == 0
    assert bks.recargo_nocturno_pct(db, '2026-10-20', '15:00') == 0
    assert bks.recargo_nocturno_pct(db, '2026-10-20', '00:00') == 20
    assert bks.recargo_nocturno_pct(db, '2026-10-20T00:00:00', '') == 20


def test_price_surcharge_is_on_services_only():
    price = bks.calculate_estimated_price
    assert price('workshop', pizzeros_participants=12, recargo_nocturno_pct=0) == 126000
    assert price('workshop', pizzeros_participants=12, recargo_nocturno_pct=20) == 151200
    # the comuna charge stays fixed: it is added after the surcharge
    assert price('pizza_party', pizza_quantity=10, comuna_lejana_extra=20000, recargo_nocturno_pct=20) == 119900 + 23980 + 20000


def test_the_tie_rounds_half_up_like_js_math_round(monkeypatch):
    monkeypatch.setattr(bks.PricingConfig, 'get_pizza_party_price', staticmethod(lambda n: 50), raising=False)
    # 50 CLP * 25 % = 12.5 -> 13 (Python's round() would give 12)
    assert bks.calculate_estimated_price('pizza_party', pizza_quantity=1, recargo_nocturno_pct=25) == 50 + 13


# ---------- public route ----------

@pytest.fixture
def db(monkeypatch):
    fake = FakeFirestore()
    monkeypatch.setattr(bookings_routes, 'get_db', lambda: fake)
    monkeypatch.setattr(settings_routes, 'get_db', lambda: fake)
    monkeypatch.setattr(bks, 'send_admin_email_notification', lambda booking: None)

    async def fake_whatsapp(*a, **k):
        return None
    monkeypatch.setattr(bks, 'send_whatsapp_template', fake_whatsapp)
    return fake


@pytest.fixture
def app(db):
    app = Flask(__name__)
    app.register_blueprint(bookings_routes.bookings_bp)
    app.register_blueprint(settings_routes.settings_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _form(**overrides):
    data = {
        'client_name': 'Ana Pérez', 'client_email': 'ana@example.com', 'client_phone': '+56912345678',
        'service_type': 'workshop', 'event_type': 'birthday', 'event_date': '2026-11-14T16:00:00', 'event_time': '16:00',
        'location': 'Ñuñoa', 'duration_hours': 4, 'participants': 12, 'pizzeros_participants': 12,
        'party_participants': 0, 'pizza_quantity': 0, 'source': 'website',
    }
    data.update(overrides)
    return data


def _stored(client, db, **overrides):
    res = client.post('/api/bookings/', json=_form(**overrides))
    assert res.status_code == 201, res.get_json()
    return db.store['bookings'][res.get_json()['id']]


def test_night_booking_stores_pct_and_extra_and_prices_it(client, db):
    stored = _stored(client, db, event_date='2026-11-14T22:00:00', event_time='22:00')
    assert stored['recargo_nocturno_pct'] == 20 and stored['recargo_nocturno_extra'] == 25200
    assert stored['estimated_price'] == 126000 + 25200


def test_day_booking_stores_zeros(client, db):
    stored = _stored(client, db)
    assert stored['recargo_nocturno_pct'] == 0 and stored['recargo_nocturno_extra'] == 0
    assert stored['estimated_price'] == 126000


def test_comuna_lejana_is_not_surcharged(client, db):
    stored = _stored(client, db, event_date='2026-11-14T23:30:00', event_time='23:30', selected_comuna='Quilicura')
    assert stored['estimated_price'] == 126000 + 25200 + 20000


def test_the_client_cannot_choose_the_percentage(client, db):
    assert _stored(client, db, recargo_nocturno_pct=50, recargo_nocturno_extra=999999)['recargo_nocturno_pct'] == 0
    night = _stored(client, db, event_time='00:00', event_date='2026-11-14', recargo_nocturno_pct=0)
    assert night['recargo_nocturno_pct'] == 20 and night['estimated_price'] == 126000 + 25200


def test_date_only_with_day_time_has_no_surcharge(client, db):
    assert _stored(client, db, event_date='2026-11-14', event_time='15:00')['recargo_nocturno_pct'] == 0


def test_hour_in_the_date_cannot_dodge_the_surcharge(client, db):
    assert _stored(client, db, event_date='2026-11-14T23:00:00', event_time='10:00')['recargo_nocturno_pct'] == 20


def test_configured_percentage_is_used(client, db):
    db.store['settings'] = {'recargo_nocturno': {'porcentaje': 10}}
    stored = _stored(client, db, event_date='2026-11-14T22:00:00', event_time='22:00')
    assert stored['recargo_nocturno_pct'] == 10 and stored['recargo_nocturno_extra'] == 12600


def test_percentage_zero_turns_it_off(client, db):
    db.store['settings'] = {'recargo_nocturno': {'porcentaje': 0}}
    stored = _stored(client, db, event_date='2026-11-14T22:00:00', event_time='22:00')
    assert stored['recargo_nocturno_pct'] == 0 and stored['estimated_price'] == 126000


def test_create_booking_internal_callers_default_to_no_surcharge(db):
    booking = bks.create_booking(db, {'service_type': 'workshop', 'source': 'other', 'pizzeros_participants': 12}, notify=False)
    assert booking['recargo_nocturno_pct'] == 0 and booking['recargo_nocturno_extra'] == 0


# ---------- settings routes ----------

def test_get_is_public_and_defaults_to_20(client):
    res = client.get('/api/settings/recargo-nocturno')
    assert res.status_code == 200 and res.get_json()['porcentaje'] == 20


def test_get_returns_the_configured_value_including_zero(client, db):
    db.store['settings'] = {'recargo_nocturno': {'porcentaje': 0}}
    assert client.get('/api/settings/recargo-nocturno').get_json()['porcentaje'] == 0


def test_get_falls_back_to_default_for_a_corrupt_value(client, db):
    db.store['settings'] = {'recargo_nocturno': {'porcentaje': 'x'}}
    assert client.get('/api/settings/recargo-nocturno').get_json()['porcentaje'] == 20


def test_put_requires_admin(client):
    assert client.put('/api/settings/recargo-nocturno', json={'porcentaje': 10}).status_code == 401


def test_put_saves_and_validates(app, db, monkeypatch):
    admin = authenticate_as_admin(monkeypatch, app.test_client())
    res = admin.put('/api/settings/recargo-nocturno', json={'porcentaje': 15})
    assert res.status_code == 200 and res.get_json()['porcentaje'] == 15
    assert db.store['settings']['recargo_nocturno']['porcentaje'] == 15
    assert admin.put('/api/settings/recargo-nocturno', json={'porcentaje': 0}).status_code == 200
    assert db.store['settings']['recargo_nocturno']['porcentaje'] == 0
    assert admin.put('/api/settings/recargo-nocturno', json={'porcentaje': 100}).status_code == 200
    for bad in (True, False, -1, 101, 12.5, '20', None, [20], {}):
        assert admin.put('/api/settings/recargo-nocturno', json={'porcentaje': bad}).status_code == 400, bad
    assert admin.put('/api/settings/recargo-nocturno', json={}).status_code == 400
    assert db.store['settings']['recargo_nocturno']['porcentaje'] == 100
