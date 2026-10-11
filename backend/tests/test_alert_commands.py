"""Tests for the deterministic alert-preference commands (silencia ..., avisos): no model, personal settings only"""
import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402,F401  (imported at collection time: it loads backend/.env, which must not happen mid-test)
from services import alerts_service as alerts  # noqa: E402
from services import pending_actions_service as pas  # noqa: E402
from services import whatsapp_agent as wa  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402

ADMIN = '+56911111111'
NOW = datetime(2026, 10, 12, 13, 0, 0)


class Sent(list):
    def __call__(self, phone, body):
        self.append((phone, body))

    @property
    def bodies(self):
        return [b for _, b in self]


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_ENABLED', 'true')
    monkeypatch.setenv('ADMIN_WHATSAPP_NUMBER', ADMIN)
    monkeypatch.setenv('PARTNER_WHATSAPP_NUMBER', '+56922222222')
    monkeypatch.delenv('AI_WHATSAPP_ALLOWED', raising=False)
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))


@pytest.fixture
def db():
    return FakeFirestore()


def _say(db, text, sid='SM1', **extra):
    """Send `text` through the real worker; the model must never be called"""
    sent = Sent()

    def no_model(messages, user):
        raise AssertionError('a command must not reach the model')

    wa.store_inbound(db, {'MessageSid': sid, 'From': f'whatsapp:{ADMIN}', 'Body': text, 'NumMedia': '0', **extra})
    deps = wa.Deps(send=sent, run_chat=no_model, download_media=lambda u: b'', now=lambda: NOW)
    return wa.process_inbox(db, sid, deps), sent


def _prefs(db):
    return db.store['whatsapp_contacts'][ADMIN]['alert_prefs']


def _digest(db):
    db.collection('whatsapp_contacts').document(ADMIN).set(
        {'last_digest': {'at': NOW - timedelta(hours=1), 'detail': 'x', 'items': ['low_stock:harina', 'booking_pending:b1'],
                         'labels': ['Harina', 'Ana (sáb 17/10)']}}, merge=True)


@pytest.mark.parametrize('text,group,types', [
    ('silencia stock', 'stock', ['low_stock']),
    ('Silenciar reservas', 'reservas', ['booking_pending', 'booking_pending_urgent']),
    ('silencia eventos', 'eventos', ['event_tomorrow']),
    ('silencia propuestas.', 'propuestas', ['proposal_pending']),
    ('silencia inventario', 'stock', ['low_stock']),
])
def test_silencing_a_type_is_saved_and_confirmed_without_the_model(db, text, group, types):
    status, sent = _say(db, text)
    assert status == 'command' and 'no te aviso más' in sent.bodies[0] and 'avísame de nuevo' in sent.bodies[0]
    assert _prefs(db)['muted_types'] == types


def test_silencing_two_types_accumulates_and_repeating_does_not_duplicate(db):
    _say(db, 'silencia stock', sid='SM1')
    _say(db, 'silencia reservas', sid='SM2')
    _say(db, 'silencia stock', sid='SM3')
    assert _prefs(db)['muted_types'] == ['low_stock', 'booking_pending', 'booking_pending_urgent']


def test_silencing_by_number_uses_the_last_digest(db):
    _digest(db)
    status, sent = _say(db, 'silencia 2')
    assert status == 'command' and 'Ana' in sent.bodies[0]
    assert list(_prefs(db)['muted_keys']) == ['booking_pending:b1']


def test_silencing_a_number_without_a_recent_digest_explains_instead_of_guessing(db):
    _, sent = _say(db, 'silencia 1')
    assert 'No encuentro' in sent.bodies[0] and 'alert_prefs' not in db.store.get('whatsapp_contacts', {}).get(ADMIN, {})
    _digest(db)
    _, sent = _say(db, 'silencia 7', sid='SM2')
    assert 'No encuentro' in sent.bodies[0]
    db.store['whatsapp_contacts'][ADMIN]['last_digest']['at'] = NOW - timedelta(hours=50)
    _, sent = _say(db, 'silencia 1', sid='SM3')
    assert 'No encuentro' in sent.bodies[0] and 'alert_prefs' not in db.store['whatsapp_contacts'][ADMIN]


@pytest.mark.parametrize('text', ['silencia todo', 'pausa avisos', 'Pausar los avisos'])
def test_pausing_everything(db, text):
    _say(db, text)
    assert _prefs(db)['paused'] is True


@pytest.mark.parametrize('text', ['avísame de nuevo', 'Avisame de nuevo!', 'activa avisos', 'reactivar avisos'])
def test_reactivating_clears_every_mute(db, text):
    _digest(db)
    _say(db, 'silencia stock', sid='SM1')
    _say(db, 'silencia 1', sid='SM2')
    _say(db, 'pausa avisos', sid='SM3')
    _, sent = _say(db, text, sid='SM4')
    assert 'vuelvo a avisarte' in sent.bodies[0]
    assert _prefs(db) == {'muted_types': [], 'muted_keys': {}, 'paused': False}


def test_avisos_shows_the_current_state(db):
    _, sent = _say(db, 'avisos')
    assert 'activos' in sent.bodies[0] and 'silenciar' in sent.bodies[0]
    _say(db, 'silencia stock', sid='SM2')
    _, sent = _say(db, 'avisos', sid='SM3')
    assert 'stock bajo' in sent.bodies[0]
    _say(db, 'pausa avisos', sid='SM4')
    _, sent = _say(db, 'avisos', sid='SM5')
    assert 'pausa' in sent.bodies[0]


def test_saving_preferences_keeps_the_rest_of_the_contact_record(db):
    wa.touch_contact(db, ADMIN, now=NOW - timedelta(hours=1))
    _say(db, 'silencia stock')
    contact = db.store['whatsapp_contacts'][ADMIN]
    assert contact['last_user_message_at'] == NOW - timedelta(hours=1) and contact['alert_prefs']['muted_types'] == ['low_stock']


def test_a_muted_type_really_stops_the_alerts(db):
    db.collection('inventory').document('harina').set(
        {'name': 'Harina', 'current_stock': 1, 'min_stock': 5, 'unit': 'kg', 'needs_restock': True})
    active = alerts.evaluate(db, NOW)
    _say(db, 'silencia stock')
    assert alerts.announceable(active, ADMIN, alerts.get_prefs(db, ADMIN), NOW) == []


def test_similar_sentences_still_go_to_the_agent(db):
    for sid, text in enumerate(['silencia el stock de la harina por favor', 'cuántos avisos hay', 'no me avises de la harina'], 1):
        calls = []
        wa.store_inbound(db, {'MessageSid': f'SM{sid}', 'From': f'whatsapp:{ADMIN}', 'Body': text, 'NumMedia': '0'})
        deps = wa.Deps(send=Sent(), run_chat=lambda m, u: calls.append(m) or {'response': 'ok', 'pending_actions': [], 'choices': []},
                       download_media=lambda u: b'', now=lambda: NOW)
        assert wa.process_inbox(db, f'SM{sid}', deps) == 'answered' and len(calls) == 1


def test_forwarded_messages_are_not_commands(db):
    calls = []
    wa.store_inbound(db, {'MessageSid': 'SM1', 'From': f'whatsapp:{ADMIN}', 'Body': 'silencia todo', 'NumMedia': '0', 'Forwarded': 'true'})
    deps = wa.Deps(send=Sent(), run_chat=lambda m, u: calls.append(m) or {'response': 'ok', 'pending_actions': [], 'choices': []},
                   download_media=lambda u: b'', now=lambda: NOW)
    wa.process_inbox(db, 'SM1', deps)
    assert calls and 'alert_prefs' not in db.store.get('whatsapp_contacts', {}).get(ADMIN, {})

