"""Tests for propose_booking: the agent creates PENDING bookings only, with the side effects documented"""
import os
import sys
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.clock import today_cl  # noqa: E402

from routes import ai_chat_routes as routes  # noqa: E402
from services import booking_proposals as bp  # noqa: E402
from services import booking_service as bks  # noqa: E402
from services import pending_actions_service as pas  # noqa: E402
from services.inventory_proposals import ProposalError  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402

USER = {'uid': 'u1', 'email': 'admin@example.com'}


def _day(offset=10):
    return (today_cl() + timedelta(days=offset)).isoformat()


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))
    monkeypatch.setattr('utils.audit.log_audit', lambda *a, **k: None)


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


def _booking(**o):
    data = {'client_name': 'Martina Soto', 'client_email': 'martina@example.com', 'client_phone': '+56912345678',
            'services': ['pizzeros'], 'event_date': _day(), 'event_time': '16:30', 'location': 'Av. Irarrázaval 1234, Ñuñoa',
            'comuna': 'Ñuñoa', 'pizzeros_participants': 12, 'event_type': 'birthday', 'special_requests': 'Una niña celíaca'}
    data.update(o)
    return data


# ---------- validation ----------

@pytest.mark.parametrize('bad', [
    {'client_name': ''}, {'services': []}, {'services': ['pizzeros', 'pizzeros']}, {'services': ['catering']},
    {'event_time': '25:00'}, {'event_time': 'tarde'}, {'client_email': 'sin-arroba'}, {'location': ''},
    {'pizzeros_participants': 0}, {'event_type': 'boda'}, {'event_date': 'pronto'},
])
def test_invalid_proposals_are_rejected(bad):
    with pytest.raises(ValidationError):
        bp.BookingPayload.model_validate(_booking(**bad))


def test_each_service_needs_its_own_quantity():
    with pytest.raises(ValidationError):
        bp.BookingPayload.model_validate(_booking(services=['party']))  # no pizzas
    ok = bp.BookingPayload.model_validate(_booking(services=['party'], pizza_quantity=15, pizzeros_participants=0))
    assert ok.pizza_quantity == 15


def test_chilean_date_and_time_formats_are_accepted():
    payload = bp.BookingPayload.model_validate(_booking(event_date='20-11-2030', event_time='9:05'))
    assert payload.event_date == date(2030, 11, 20) and payload.event_time == '09:05'


def test_a_past_date_is_an_error_for_the_model(db):
    with pytest.raises(ProposalError) as err:
        bp.propose_booking(db, _booking(event_date=_day(-2)), USER)
    assert 'ya pasó' in str(err.value)


# ---------- propose does not create anything or notify ----------

def test_proposing_creates_no_booking_and_sends_nothing(db, sent):
    action = bp.propose_booking(db, _booking(), USER)
    assert action['status'] == 'pending' and action['type'] == 'booking'
    assert 'bookings' not in db.store and 'customers' not in db.store
    assert sent == {'whatsapp': [], 'email': []}
    assert 'Martina Soto' in action['summary'] and '$126.000' in action['summary']  # 12 kids x $10.500


def test_the_card_explains_who_gets_notified(db):
    action = bp.propose_booking(db, _booking(), USER)
    assert any('WhatsApp' in w and 'El cliente no recibe nada' in w and 'PENDIENTE' in w for w in action['warnings'])


# ---------- confirming ----------

def test_confirming_creates_a_pending_booking_with_the_same_shape_as_the_website(db, sent):
    action = bp.propose_booking(db, _booking(), USER)
    result = pas.confirm(db, action['id'], USER)['result']
    booking, = db.store['bookings'].values()

    assert booking['status'] == 'pending' and result['status'] == 'pending' and result['booking_id'] == booking['id']
    assert booking['client_name'] == 'Martina Soto' and booking['service_type'] == 'workshop'
    assert booking['event_date'] == f"{_day()}T16:30:00" and booking['event_time'] == '16:30'  # website format
    assert booking['pizzeros_participants'] == 12 and booking['participants'] == 12 and booking['services_selected'] == ['pizzeros']
    assert booking['location'].startswith('Av. Irarrázaval') and booking['notes'] == 'Una niña celíaca'
    assert booking['estimated_price'] == 126000 and booking['source'] == 'other' and booking['source_other'] == 'Asistente IA'
    assert booking['created_via'] == 'ai_agent' and booking['created_by'] == 'admin@example.com'


def test_confirming_notifies_the_admin_side_and_never_the_customer(db, sent):
    action = bp.propose_booking(db, _booking(client_phone='+56999999999'), USER)
    pas.confirm(db, action['id'], USER)
    assert [phone for phone, _ in sent['whatsapp']] == ['+56911111111', '+56922222222']
    assert '+56999999999' not in [phone for phone, _ in sent['whatsapp']]
    assert {template for _, template in sent['whatsapp']} == {'new_booking'}   # not the customer's "confirmed" template
    assert len(sent['email']) == 1


def test_confirming_twice_creates_one_booking_and_notifies_once(db, sent):
    action = bp.propose_booking(db, _booking(), USER)
    pas.confirm(db, action['id'], USER)
    pas.confirm(db, action['id'], USER)
    assert len(db.store['bookings']) == 1 and len(sent['email']) == 1 and len(sent['whatsapp']) == 2


def test_a_retry_after_a_failed_confirmation_does_not_duplicate_the_booking(db, sent, monkeypatch):
    action = bp.propose_booking(db, _booking(), USER)
    real = bks.create_booking
    state = {'calls': 0}

    def flaky(db_, data, booking_id=None, notify=True):
        state['calls'] += 1
        booking = real(db_, data, booking_id=booking_id, notify=False)  # written...
        if state['calls'] == 1:
            raise RuntimeError('timeout after the write')                # ...but the call "failed"
        return booking

    monkeypatch.setattr(bks, 'create_booking', flaky)
    with pytest.raises(RuntimeError):
        pas.confirm(db, action['id'], USER)
    pas.confirm(db, action['id'], USER)
    assert len(db.store['bookings']) == 1


def test_the_agent_cannot_confirm_or_cancel_bookings():
    names = {t['name'] for t in routes.TOOLS}
    assert 'propose_booking' in names
    assert not any(word in name for name in names for word in ('confirm_booking', 'cancel_booking', 'update_booking'))


def test_an_edited_payload_is_revalidated_at_confirm(db, sent):
    action = bp.propose_booking(db, _booking(), USER)
    with pytest.raises(pas.InvalidPayload):
        pas.confirm(db, action['id'], USER, edited_payload={**action['payload'], 'event_time': '99:99'})
    assert 'bookings' not in db.store
    pas.confirm(db, action['id'], USER, edited_payload={**action['payload'], 'pizzeros_participants': 20, 'event_time': '11:00'})
    booking, = db.store['bookings'].values()
    assert booking['pizzeros_participants'] == 20 and booking['event_time'] == '11:00' and booking['estimated_price'] == 180000


# ---------- price, surcharge, warnings ----------

def test_distant_commune_surcharge_from_settings_defaults(db):
    action = bp.propose_booking(db, _booking(comuna='Quilicura', location='Calle X 1, Quilicura'), USER)
    assert action['context']['estimated_price'] == 126000 + 20000 and action['context']['comuna_lejana'] is True
    assert any('comuna lejana' in w for w in action['warnings'])


def test_distant_commune_list_and_charge_come_from_the_settings_collection(db):
    db.store['settings'] = {'comunas_lejanas': {'comunas': ['Ñuñoa'], 'cargo': 5000}}
    action = bp.propose_booking(db, _booking(), USER)
    assert action['context']['estimated_price'] == 126000 + 5000


def test_pizza_party_pricing_and_minimum_warning(db):
    action = bp.propose_booking(db, _booking(services=['party'], pizzeros_participants=0, pizza_quantity=8), USER)
    assert action['context']['estimated_price'] == 8 * 11990
    assert any('mínimo habitual' in w for w in action['warnings'])
    both = bp.propose_booking(db, _booking(services=['pizzeros', 'party'], pizza_quantity=20), USER)
    assert both['context']['estimated_price'] == 126000 + 20 * 10791


def test_warns_about_other_bookings_the_same_day_in_either_date_format(db):
    db.store['bookings'] = {
        'a': {'client_name': 'Ana', 'status': 'confirmed', 'event_date': f'{_day()}T10:00:00', 'event_time': '10:00'},
        'b': {'client_name': 'Beto', 'status': 'pending', 'event_date': _day(), 'event_time': '19:00'},
        'c': {'client_name': 'Cancelada', 'status': 'cancelled', 'event_date': _day()},
        'd': {'client_name': 'Otro día', 'status': 'confirmed', 'event_date': _day(11)},
    }
    action = bp.propose_booking(db, _booking(), USER)
    warning = next(w for w in action['warnings'] if 'Ese día ya hay' in w)
    assert '2 reserva(s)' in warning and 'Ana' in warning and 'Beto' in warning and 'Cancelada' not in warning


def test_known_customer_and_missing_contact_warnings(db):
    db.store['customers'] = {'c1': {'name': 'Martina Soto', 'email': 'martina@example.com'}}
    known = bp.propose_booking(db, _booking(), USER)
    assert any('Ya existe el cliente Martina Soto' in w for w in known['warnings'])
    anonymous = bp.propose_booking(db, _booking(client_email=None, client_phone=None, client_name='Pedro Rojo'), USER)
    assert any('Sin correo ni teléfono' in w for w in anonymous['warnings'])


def test_the_same_request_twice_warns_as_duplicate(db):
    bp.propose_booking(db, _booking(), USER)
    again = bp.propose_booking(db, _booking(), USER)
    assert any('Posible duplicado' in w for w in again['warnings'])
    other_time = bp.propose_booking(db, _booking(event_time='18:00'), USER)
    assert not any('Posible duplicado' in w for w in other_time['warnings'])


# ---------- through the chat tool ----------

def test_the_tool_returns_a_card_and_writes_nothing(db, sent, monkeypatch):
    from flask import Flask, g
    monkeypatch.setattr(routes, 'get_db', lambda: db)
    with Flask(__name__).test_request_context():
        g.current_user = USER
        result = routes.execute_tool('propose_booking', _booking())
        assert result['status'] == 'pending_confirmation' and 'NO está guardada' in result['message']
        assert g.ai_pending_actions[0]['type'] == 'booking'
        past = routes.execute_tool('propose_booking', _booking(event_date=_day(-1)))
        assert 'error' in past and 'ya pasó' in past['error']
    assert 'bookings' not in db.store and sent == {'whatsapp': [], 'email': []}


def test_the_prompt_says_the_agent_cannot_confirm_and_who_is_notified():
    prompt = routes.SYSTEM_PROMPT
    assert 'tú NO puedes confirmarla ni cancelarla' in prompt
    assert 'avisa al cliente por WhatsApp y correo' in prompt
