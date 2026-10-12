"""Latency instrumentation: fine-grained stage timings are recorded without changing behaviour"""
import os
import sys
from types import SimpleNamespace

import pytest
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes import ai_chat_routes  # noqa: E402
from services import whatsapp_agent as wa  # noqa: E402
from tests.test_whatsapp import _answer, _deps, _env, _inbox, db  # noqa: E402,F401  (fixtures + helpers)


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
