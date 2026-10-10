"""Tests for search_bookings, ask_choice (turn ends, buttons) and the 'user chose it' guard"""
import os
import sys
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from flask import Flask, g

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes import ai_chat_routes as routes  # noqa: E402
from services import booking_search as bs  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402
from tests.test_ai_chat_routes import _admin, _auth, client  # noqa: E402,F401


def _day(offset):
    return (date.today() + timedelta(days=offset)).isoformat()


@pytest.fixture
def db():
    fake = FakeFirestore()
    fake.store['bookings'] = {
        'b-martina': {'client_name': 'Martina Soto', 'status': 'confirmed', 'event_date': _day(5), 'event_time': '16:00',
                      'service_type': 'Pizzeros en Acción', 'participants': 12, 'location': 'Ñuñoa'},
        'b-martin': {'client_name': 'Martín Pérez', 'status': 'confirmed', 'event_date': _day(12), 'service_type': 'Pizza Party'},
        'b-past': {'client_name': 'Martina Soto', 'status': 'completed', 'event_date': _day(-30)},
        'b-cancel': {'client_name': 'Martina Soto', 'status': 'cancelled', 'event_date': _day(3)},
        'b-colegio': {'client_name': 'Colegio San José', 'status': 'pending', 'event_date': _day(8)},
    }
    fake.store['event_supplies'] = {'s1': {'id': 's1', 'booking_id': 'b-martina', 'estimated_total_cost': 12000}}
    return fake


# ---------- search_bookings ----------

def test_search_by_name_tolerates_accents_and_skips_cancelled(db):
    ids = [b['id'] for b in bs.search_bookings(db, client_name='martina')]
    # exact "martina" first (upcoming, then past), then the fuzzy "Martín"; the cancelled one is hidden
    assert ids == ['b-martina', 'b-past', 'b-martin']


def test_search_nearest_upcoming_first_without_filters(db):
    ids = [b['id'] for b in bs.search_bookings(db)]
    assert ids[:3] == ['b-martina', 'b-colegio', 'b-martin'] and ids[-1] == 'b-past'
    assert 'b-cancel' not in ids


def test_search_by_status_date_range_and_explicit_cancelled(db):
    assert [b['id'] for b in bs.search_bookings(db, status='confirmed')] == ['b-martina', 'b-martin']
    assert [b['id'] for b in bs.search_bookings(db, date_from=_day(6), date_to=_day(10))] == ['b-colegio']
    assert [b['id'] for b in bs.search_bookings(db, status='cancelled')] == ['b-cancel']


def test_search_result_shape_and_flags(db):
    martina = bs.search_bookings(db, client_name='Martina Soto', status='confirmed')[0]
    assert martina['day_of_week'] in bs.DAY_NAMES and martina['participants'] == 12 and martina['location'] == 'Ñuñoa'
    assert martina['has_supplies'] is True and martina['estimated_supply_cost'] == 12000
    assert martina['has_consumption'] is False
    assert bs.search_bookings(db, client_name='nadie') == []


def test_search_limit(db):
    assert len(bs.search_bookings(db, limit=2)) == 2


# ---------- ask_choice ----------

def _ctx():
    return Flask(__name__).test_request_context()


def test_ask_choice_validates_and_remembers_the_question():
    with _ctx():
        ok = routes.execute_tool('ask_choice', {
            'question': '¿A qué evento?', 'context': '5 kg harina',
            'options': [{'id': 'b1', 'label': 'Martina · sáb 17'}, {'id': 'b2', 'label': 'Colegio · lun 19'}]})
        assert ok['status'] == 'waiting_for_user_choice'
        assert g.ai_choice['options'][0] == {'id': 'b1', 'label': 'Martina · sáb 17'}


@pytest.mark.parametrize('payload', [
    {'question': '', 'options': [{'id': 'a', 'label': 'A'}, {'id': 'b', 'label': 'B'}]},
    {'question': 'Q', 'options': [{'id': 'a', 'label': 'A'}]},
    {'question': 'Q', 'options': [{'id': 'a', 'label': 'A'}, {'id': 'a', 'label': 'B'}]},
    {'question': 'Q', 'options': [{'id': 'a', 'label': ''}, {'id': 'b', 'label': 'B'}]},
    {'question': 'Q', 'options': [{'id': str(i), 'label': 'x'} for i in range(9)]},
    {'question': 'Q'},
])
def test_ask_choice_rejects_bad_options(payload):
    with _ctx():
        assert 'error' in routes.execute_tool('ask_choice', payload)
        assert getattr(g, 'ai_choice', None) is None


def test_only_one_question_per_turn_and_the_first_one_stands():
    first = {'question': 'Primera', 'options': [{'id': 'a', 'label': 'A'}, {'id': 'b', 'label': 'B'}]}
    second = {'question': 'Segunda', 'options': [{'id': 'c', 'label': 'C'}, {'id': 'd', 'label': 'D'}]}
    with _ctx():
        assert routes.execute_tool('ask_choice', first)['status'] == 'waiting_for_user_choice'
        assert 'error' in routes.execute_tool('ask_choice', second)
        assert g.ai_choice['question'] == 'Primera'


class ChoosingMessages:
    """Model that searches bookings, then asks which one, then (should never be called again) answers"""

    def __init__(self):
        self.calls = []

    def create(self, **params):
        self.calls.append(params)
        usage = SimpleNamespace(input_tokens=1, output_tokens=1)
        if len(self.calls) == 1:
            block = SimpleNamespace(type='tool_use', id='t1', name='search_bookings', input={'client_name': 'martina'})
            return SimpleNamespace(content=[block], stop_reason='tool_use', usage=usage, model='m')
        if len(self.calls) == 2:
            ask = SimpleNamespace(type='tool_use', id='t2', name='ask_choice', input={
                'question': '¿A qué evento corresponde?', 'context': '- Harina: 5 kg\n- Queso: 2 kg',
                'options': [{'id': 'b-martina', 'label': 'Martina · en 5 días'}, {'id': 'b-past', 'label': 'Martina · mes pasado'}]})
            return SimpleNamespace(content=[SimpleNamespace(type='text', text='Veo estos eventos.'), ask],
                                   stop_reason='tool_use', usage=usage, model='m')
        raise AssertionError('the model must not be called again after ask_choice')


def test_chat_ends_the_turn_with_buttons_and_does_not_call_the_model_again(client, db, monkeypatch):
    _admin(monkeypatch)
    monkeypatch.setattr(routes, 'get_db', lambda: db)
    model = SimpleNamespace(messages=ChoosingMessages())
    monkeypatch.setattr(routes, 'anthropic_client', model)

    res = client.post('/api/ai-chat/', json={'messages': [{'role': 'user', 'content': 'insumos del evento de Martina'}]}, headers=_auth())
    body = res.get_json()

    assert res.status_code == 200 and body['stop_reason'] == 'ask_choice'
    assert [c['id'] for c in body['choices']] == ['b-martina', 'b-past']
    assert 'Veo estos eventos.' in body['response'] and 'Harina: 5 kg' in body['response']
    assert body['response'].rstrip().endswith('¿A qué evento corresponde?')
    assert len(model.messages.calls) == 2


def test_chat_response_has_no_choices_normally(client, monkeypatch):
    from tests.test_ai_chat_routes import FakeMessages
    _admin(monkeypatch)
    monkeypatch.setattr(routes, 'anthropic_client', SimpleNamespace(messages=FakeMessages()))
    body = client.post('/api/ai-chat/', json={'messages': [{'role': 'user', 'content': 'hola'}]}, headers=_auth()).get_json()
    assert body['choices'] == []


# ---------- the "user chose it" guard ----------

def test_user_said_only_sees_what_the_user_wrote(client, db, monkeypatch):
    _admin(monkeypatch)
    monkeypatch.setattr(routes, 'get_db', lambda: db)
    seen = {}

    class Probe:
        def create(self, **params):
            seen['guard'] = (routes.user_said('b-martina'), routes.user_said('b-other'), routes.user_said(''))
            return SimpleNamespace(content=[SimpleNamespace(type='text', text='ok')], stop_reason='end_turn',
                                   usage=SimpleNamespace(input_tokens=1, output_tokens=1), model='m')

    monkeypatch.setattr(routes, 'anthropic_client', SimpleNamespace(messages=Probe()))
    client.post('/api/ai-chat/', json={'messages': [
        {'role': 'user', 'content': 'mira'},
        {'role': 'assistant', 'content': 'Opciones: b-other'},          # model output does not count
        {'role': 'user', 'content': 'Martina · en 5 días [id: b-martina]'}]}, headers=_auth())
    assert seen['guard'] == (True, False, False)
