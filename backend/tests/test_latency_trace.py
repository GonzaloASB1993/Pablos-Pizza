"""Latency instrumentation: fine-grained stage timings are recorded without changing behaviour"""
import os
import sys
from types import SimpleNamespace

import pytest
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes import ai_chat_routes  # noqa: E402
from services import whatsapp_agent as wa  # noqa: E402
from tests.test_whatsapp import _answer, _deps, _env, _form, _inbox, db, hook  # noqa: E402,F401  (fixtures + helpers)


def _reply(blocks, stop, cache_read=0):
    return SimpleNamespace(content=blocks, stop_reason=stop, model='m',
                           usage=SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=cache_read,
                                                 cache_creation_input_tokens=0))


def test_run_chat_traces_every_model_round_and_tool(monkeypatch):
    tool = SimpleNamespace(type='tool_use', name='get_inventory_status', input={}, id='t1')
    replies = iter([_reply([tool], 'tool_use', cache_read=100), _reply([SimpleNamespace(type='text', text='ok')], 'end_turn', 100)])
    monkeypatch.setattr(ai_chat_routes, 'create_ai_message', lambda *a, **k: next(replies))
    monkeypatch.setattr(ai_chat_routes, 'execute_tool', lambda name, inp: {'ok': True})
    with Flask(__name__).test_request_context():
        result = ai_chat_routes.run_chat([{'role': 'user', 'content': 'stock'}], {'uid': 'u', 'email': 'e'}, channel='whatsapp')
    rounds, tools = result['trace']['rounds'], result['trace']['tools']
    assert [r['stop'] for r in rounds] == ['tool_use', 'end_turn'] and rounds[0]['cache_read'] == 100
    assert all(r['ms'] >= 0 and r['in'] == 10 and r['out'] == 5 for r in rounds)
    assert [(t['name'], t['round']) for t in tools] == [('get_inventory_status', 1)] and tools[0]['ms'] >= 0


def test_process_inbox_stores_the_infrastructure_stages_and_the_agent_trace(db):
    trace = {'rounds': [{'ms': 900, 'stop': 'end_turn'}], 'tools': [{'name': 'x', 'ms': 3, 'round': 1}]}
    wa.process_inbox(db, _inbox(db, 'SM900'), _deps(_answer(trace=trace)))
    timings = db.store['whatsapp_inbox']['SM900']['timings']
    assert {'claim_ms', 'typing_ms', 'quota_ms', 'lock_ms', 'gather_ms', 'load_conv_ms', 'commands_ms', 'agent_ms',
            'send_ms', 'save_ms', 'total_ms'} <= set(timings)
    assert timings['rounds'] == trace['rounds'] and timings['tools'] == trace['tools']


# ============ typing indicator off the critical path ============

def test_worker_typing_runs_in_the_background_and_is_joined_before_the_turn_ends(db, monkeypatch):
    import threading
    started, release, finished = threading.Event(), threading.Event(), []

    def slow_typing(sid):
        started.set()
        release.wait(1.5)
        finished.append(sid)

    seen = []

    def agent(messages, user):
        # the model is already running while the (slow) indicator is still in flight
        seen.append((started.wait(1), finished[:]))
        release.set()
        return {'response': 'ok', 'pending_actions': [], 'choices': []}

    deps = wa.Deps(send=lambda p, b: None, run_chat=agent, download_media=lambda u: b'', typing=slow_typing)
    assert wa.process_inbox(db, _inbox(db, 'SM700'), deps) == 'answered'
    assert seen == [(True, [])] and finished == ['SM700']      # not awaited by the agent, but done when process_inbox returns


def test_worker_typing_can_be_made_sequential_again(db, monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_TYPING_ASYNC', 'false')
    order = []
    deps = wa.Deps(send=lambda p, b: None, download_media=lambda u: b'', typing=lambda sid: order.append('typing'),
                   run_chat=lambda m, u: order.append('agent') or {'response': 'ok', 'pending_actions': [], 'choices': []})
    wa.process_inbox(db, _inbox(db, 'SM701'), deps)
    assert order == ['typing', 'agent']


def test_a_failing_typing_call_never_breaks_the_turn(db):
    def boom(sid):
        raise RuntimeError('twilio down')
    deps = wa.Deps(send=lambda p, b: None, download_media=lambda u: b'', typing=boom,
                   run_chat=lambda m, u: {'response': 'ok', 'pending_actions': [], 'choices': []})
    assert wa.process_inbox(db, _inbox(db, 'SM702'), deps) == 'answered'


def test_webhook_typing_overlaps_the_store_and_is_finished_before_the_response(hook, db, monkeypatch):
    import threading
    from services import whatsapp_agent as agent
    release, finished = threading.Event(), []
    original = agent.store_inbound

    def slow_typing(sid):
        release.wait(1.5)
        finished.append(sid)

    def store(db_, form):
        release.set()                       # the store runs while the indicator request is still in flight
        return original(db_, form)

    monkeypatch.setattr(agent, 'send_typing', slow_typing)
    monkeypatch.setattr(agent, 'store_inbound', store)
    res = hook(_form(body='cuánto gasté este mes', sid='SM710'))
    assert res.status_code == 200 and 'SM710' in db.store['whatsapp_inbox'] and finished == ['SM710']


def test_webhook_typing_keeps_the_old_order_when_async_is_off(hook, db, monkeypatch):
    from services import whatsapp_agent as agent
    monkeypatch.setenv('AI_WHATSAPP_TYPING_ASYNC', 'false')
    order = []
    original = agent.store_inbound
    monkeypatch.setattr(agent, 'send_typing', lambda sid: order.append('typing'))
    monkeypatch.setattr(agent, 'store_inbound', lambda d, f: order.append('store') or original(d, f))
    hook(_form(body='cuánto gasté este mes', sid='SM711'))
    assert order == ['store', 'typing']
