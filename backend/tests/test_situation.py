"""The situation snapshot given to the agent as data: bounded, id-free, never raises, off by default"""
import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask  # noqa: E402

from routes import ai_chat_routes  # noqa: E402
from services import situation  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402

NOW = datetime(2026, 10, 12, 15, 0, 0)     # Monday 12:00 in Chile


def _seed(db):
    for bid, who, when, status in [('SECRETID1', 'Carolina Soto', '2026-10-13T19:00:00', 'confirmed'),
                                   ('b2', 'Pedro', '2026-10-17T10:00:00', 'pending'),
                                   ('b3', 'Cancelado', '2026-10-14T11:00:00', 'cancelled'),
                                   ('b4', 'Lejano', '2026-12-01T11:00:00', 'confirmed'),
                                   ('b5', 'Pasado', '2026-10-01T11:00:00', 'confirmed')]:
        db.collection('bookings').document(bid).set({'client_name': who, 'event_date': when, 'status': status,
                                                    'service_type': 'workshop', 'location': 'Ñuñoa', 'participants': 12})
    db.collection('inventory').document('i1').set({'name': 'Queso mozzarella', 'unit': 'kg', 'current_stock': 3.2, 'min_stock': 5,
                                                   'needs_restock': True})
    db.collection('inventory').document('i2').set({'name': 'Harina', 'unit': 'kg', 'current_stock': 60, 'min_stock': 25,
                                                   'needs_restock': False})
    db.collection('contacts').document('c1').set({'name': 'Ana', 'subject': 'Cotización <b>', 'status': 'pending', 'priority': 'urgent'})
    db.collection('contacts').document('c2').set({'name': 'Luis', 'subject': 'Gracias', 'status': 'resolved'})


def test_flag_switches_it_off(monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_CONTEXT', 'false')
    assert situation.build(FakeFirestore(), NOW) == ''


def test_snapshot_lists_active_events_low_stock_and_open_inquiries_without_ids(monkeypatch):
    
    db = FakeFirestore()
    _seed(db)
    text = situation.build(db, NOW)
    assert 'mar 13/10 19:00 · Carolina Soto · Pizzeros en Acción · Ñuñoa · 12 pers. · confirmada' in text
    assert 'Pedro' in text and 'por confirmar' in text
    assert 'Cancelado' not in text and 'Lejano' not in text and 'Pasado' not in text      # window: today .. +14 days, not cancelled
    assert 'Queso mozzarella: 3,2 kg (mínimo 5)' in text and 'Harina' not in text
    assert 'Ana · Cotización b · urgent' in text and 'Luis' not in text
    assert 'SECRETID1' not in text and 'c1' not in text                                    # no ids: the person chooses the event


def test_empty_sections_say_so_and_a_failure_means_no_snapshot(monkeypatch):
    
    assert situation.build(FakeFirestore(), NOW).count('- ninguno') == 3

    class Broken(FakeFirestore):
        def collection(self, name):
            raise RuntimeError('down')
    assert situation.build(Broken(), NOW) == ''


def test_the_block_reaches_the_model_as_a_third_uncached_system_block_and_never_the_messages(monkeypatch):
    captured = {}

    class Messages:
        def create(self, **params):
            captured.update(params)
            return SimpleNamespace(content=[SimpleNamespace(type='text', text='ok')], stop_reason='end_turn', model='m',
                                   usage=SimpleNamespace(input_tokens=1, output_tokens=1))
    monkeypatch.setattr(ai_chat_routes, 'anthropic_client', SimpleNamespace(messages=Messages()))
    with Flask(__name__).test_request_context():
        ai_chat_routes.run_chat([{'role': 'user', 'content': 'qué tengo esta semana'}], {'uid': 'u', 'email': 'e'},
                                channel='whatsapp', extra_system='recent', situation='- mar 13 · X')
    system = captured['system']
    assert [('cache_control' in b) for b in system] == [True, False, False]
    assert '<situacion_actual>' in system[1]['text'] and '- mar 13 · X' in system[1]['text'] and 'SIN llamar herramientas' in system[1]['text']
    assert 'mar 13' not in str(captured['messages'])


def test_the_worker_passes_the_snapshot_unless_switched_off(monkeypatch):
    from routes import whatsapp_routes
    from services import whatsapp_agent as wa
    db = FakeFirestore()
    _seed(db)
    captured = []
    monkeypatch.setattr(ai_chat_routes, 'run_chat', lambda messages, user, channel='web', extra_system=None, **kw:
                        captured.append(kw) or {'response': 'ok'})
    monkeypatch.setattr(whatsapp_routes, 'get_db', lambda: db)
    monkeypatch.setattr(wa, 'process_inbox', lambda db_, sid, deps: deps.run_chat([{'role': 'user', 'content': 'hola'}],
                                                                              {'uid': 'u', 'email': 'e'}) and 'answered')

    # the snapshot is computed for the real clock: shift the seeded dates to it
    monkeypatch.setattr(situation.clock, 'today_cl', lambda now=None: NOW.date())
    monkeypatch.setenv('AI_WHATSAPP_CONTEXT', 'false')
    whatsapp_routes.process_inbox_message(Flask(__name__), 'SM-a')
    monkeypatch.delenv('AI_WHATSAPP_CONTEXT')                          # on by default
    whatsapp_routes.process_inbox_message(Flask(__name__), 'SM-b')
    assert captured[0] == {} and 'Carolina Soto' in captured[1]['situation']
