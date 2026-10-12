"""Instant (no model) answers for stock of X and today's / tomorrow's events: precise or silent"""
import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import quick_queries as qq  # noqa: E402
from services import whatsapp_agent as wa  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402
from tests.test_whatsapp import NOW, Sent, _deps, _env, _inbox, db  # noqa: E402,F401

# NOW = 2026-10-12 15:00 UTC = Monday 12:00 in Chile


def _seed(db):
    for i, (name, unit, stock, minimum, restock) in enumerate([
            ('Queso mozzarella', 'kg', 3.2, 5, True), ('Queso parmesano', 'kg', 2, 1, False),
            ('Harina 000', 'kg', 60, 25, False), ('Salsa de tomate', 'kg', 8, 6, False)]):
        db.collection('inventory').document(f'i{i}').set({'name': name, 'unit': unit, 'current_stock': stock,
                                                          'min_stock': minimum, 'needs_restock': restock})
    for bid, who, when, status, cancelled in [('b1', 'Carolina Soto', '2026-10-13T19:00:00', 'confirmed', False),
                                              ('b2', 'Pedro', '2026-10-13T10:00:00', 'pending', False),
                                              ('b3', 'Cancelado', '2026-10-13T11:00:00', 'cancelled', True),
                                              ('b4', 'Hoy Cliente', '2026-10-12T16:00:00', 'confirmed', False)]:
        db.collection('bookings').document(bid).set({'client_name': who, 'event_date': when, 'status': status,
                                                    'service_type': 'pizza_party', 'location': 'La Reina', 'participants': 20})


@pytest.mark.parametrize('text,expected', [
    ('qué hay de stock de queso', ('stock', 'queso')),
    ('Stock de harina', ('stock', 'harina')),
    ('cuánto queda de salsa de tomate?', ('stock', 'salsa de tomate')),
    ('cuántos hay de queso', ('stock', 'queso')),
    ('tengo algo mañana?', ('events', 'manana')),
    ('¿qué eventos tengo hoy?', ('events', 'hoy')),
    ('eventos de mañana', ('events', 'manana')),
])
def test_recognizes_only_the_exact_shapes(text, expected):
    assert qq.parse(text) == expected


@pytest.mark.parametrize('text', [
    'stock', 'qué hay de nuevo', 'cuánto vendimos este mes', 'qué hay pendiente', 'stock de queso y harina para el sábado',
    'registra stock de queso 5 kg', 'qué eventos tengo esta semana', 'tengo algo mañana en la tarde con Juan',
    'cuánto queda de todo', 'stock bajo', 'eventos de ayer', 'stock de un queso muy especial de importacion',
])
def test_anything_else_goes_to_the_agent(text):
    assert qq.parse(text) is None


def test_stock_answer_shows_only_items_that_are_that_item(db):
    _seed(db)
    reply = qq.answer(db, 'qué hay de stock de queso', NOW)
    assert 'Queso mozzarella: 3,2 kg (mínimo 5) ⚠️ bajo' in reply and 'Queso parmesano: 2 kg' in reply and 'Harina' not in reply
    assert 'Harina 000: 60 kg' in qq.answer(db, 'stock de harina', NOW)


def test_stock_with_no_exact_word_match_is_left_to_the_agent(db):
    _seed(db)
    assert qq.answer(db, 'cuántos hay de sal', NOW) is None            # "sal" is only a prefix of "Salsa de tomate"
    assert qq.answer(db, 'stock de pepperoni', NOW) is None            # unknown item: the agent can search / ask


def test_events_answer_lists_active_bookings_of_the_day_in_chile(db):
    _seed(db)
    tomorrow = qq.answer(db, 'tengo algo mañana?', NOW)
    assert tomorrow.startswith('📅 Mañana (martes 13)') and 'Pedro' in tomorrow and 'Carolina Soto' in tomorrow
    assert 'Cancelado' not in tomorrow and 'Pizza Party' in tomorrow
    assert tomorrow.index('Pedro') < tomorrow.index('Carolina Soto')     # by time
    assert 'Hoy Cliente' in qq.answer(db, 'qué eventos tengo hoy', NOW)
    assert qq.answer(FakeFirestore(), 'eventos de hoy', NOW) == 'Hoy (lunes 12): no tienes eventos 🙌'


def test_a_failure_means_the_agent_answers(db, monkeypatch):
    monkeypatch.setattr(qq.inventory_search, 'scored_items', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('boom')))
    assert qq.answer(db, 'stock de queso', NOW) is None


# ---- through the worker ----

def _turn(db, text, sent, calls, **kw):
    deps = _deps(lambda m, u: calls.append(m) or {'response': 'del agente', 'pending_actions': [], 'choices': []}, sent)
    return wa.process_inbox(db, _inbox(db, **kw, body=text), deps)


def test_worker_answers_instantly_without_calling_the_model_and_remembers_it(db):
    _seed(db)
    sent, calls = Sent(), []
    assert _turn(db, 'qué hay de stock de queso', sent, calls, sid='SM800') == 'command'
    assert calls == [] and 'Queso mozzarella' in sent.bodies[0]
    history = db.store['whatsapp_conversations']['+56911111111']['history']
    assert history[0]['content'] == 'qué hay de stock de queso' and 'Queso mozzarella' in history[1]['content']


def test_worker_falls_back_to_the_model_when_unsure(db):
    _seed(db)
    sent, calls = Sent(), []
    assert _turn(db, 'cuántos hay de sal', sent, calls, sid='SM801') == 'answered'
    assert len(calls) == 1 and sent.bodies == ['del agente']


def test_flag_switches_it_off(db, monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_FAST_QUERIES', 'false')
    _seed(db)
    sent, calls = Sent(), []
    assert _turn(db, 'qué hay de stock de queso', sent, calls, sid='SM802') == 'answered' and len(calls) == 1


def test_a_photo_or_a_forwarded_message_is_never_a_quick_query(db):
    _seed(db)
    sent, calls = Sent(), []
    deps = _deps(lambda m, u: calls.append(m) or {'response': 'del agente', 'pending_actions': [], 'choices': []}, sent)
    sid = _inbox(db, 'SM803', body='stock de queso', media=[('https://x/p.jpg', 'image/jpeg')])
    assert wa.process_inbox(db, sid, deps) == 'answered' and len(calls) == 1
