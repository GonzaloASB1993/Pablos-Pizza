"""Tests for services/booking_service.py: what creating a booking triggers (and what it never does)"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import booking_service as bks  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402


@pytest.fixture
def sent(monkeypatch):
    calls = {'whatsapp': [], 'email': []}

    async def fake_whatsapp(phone, template, booking):
        calls['whatsapp'].append((phone, template))

    monkeypatch.setattr(bks, 'send_whatsapp_template', fake_whatsapp)
    monkeypatch.setattr(bks, 'send_admin_email_notification', lambda booking: calls['email'].append(booking['id']))
    monkeypatch.setenv('ADMIN_WHATSAPP_NUMBER', '+56911111111')
    monkeypatch.setenv('PARTNER_WHATSAPP_NUMBER', '+56922222222')
    return calls


@pytest.fixture
def db():
    return FakeFirestore()


def _data(**o):
    data = {'client_name': 'Ana', 'client_email': 'ana@example.com', 'client_phone': '+56912345678',
            'service_type': 'workshop', 'event_date': '2026-11-14T16:00:00', 'participants': 12,
            'pizzeros_participants': 12, 'source': 'other', 'source_other': 'Asistente'}
    data.update(o)
    return data


def test_a_created_booking_notifies_only_the_admin_side_never_the_customer(db, sent):
    bks.create_booking(db, _data(client_phone='+56999999999'))
    assert [p for p, _ in sent['whatsapp']] == ['+56911111111', '+56922222222']
    assert {t for _, t in sent['whatsapp']} == {'new_booking'}
    assert '+56999999999' not in [p for p, _ in sent['whatsapp']]
    assert len(sent['email']) == 1


def test_bookings_are_always_created_pending(db, sent):
    assert bks.create_booking(db, _data(status='confirmed'))['status'] == 'pending'


def test_notify_false_sends_nothing(db, sent):
    bks.create_booking(db, _data(), notify=False)
    assert sent == {'whatsapp': [], 'email': []}


def test_explicit_id_is_idempotent_and_does_not_notify_twice(db, sent):
    first = bks.create_booking(db, _data(), booking_id='fixed')
    second = bks.create_booking(db, _data(participants=40), booking_id='fixed')
    assert first['id'] == second['id'] == 'fixed' and second['participants'] == 12
    assert len(db.store['bookings']) == 1 and len(sent['email']) == 1 and len(sent['whatsapp']) == 2


def test_the_input_is_not_mutated(db, sent):
    data = _data(source='website', source_other='x')
    bks.create_booking(db, data)
    assert data['source_other'] == 'x'


def test_price_helper_is_the_single_copy(db):
    import main
    from routes import bookings_routes
    assert main.calculate_estimated_price is bks.calculate_estimated_price
    assert bookings_routes.calculate_estimated_price is bks.calculate_estimated_price
