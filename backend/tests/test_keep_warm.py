"""Tests for the free keep-warm: it wakes main and the worker, cleans up after itself and never costs a message"""
import os
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes import whatsapp_routes as routes  # noqa: E402
from services import keep_warm as kw  # noqa: E402
from services import pending_actions_service as pas  # noqa: E402
from services import whatsapp_agent as wa  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402

NOW = datetime(2026, 10, 12, 15, 0, 0)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_ENABLED', 'true')
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))


def test_it_pings_main_and_leaves_a_marker_for_the_worker():
    db, pinged = FakeFirestore(), []
    result = kw.keep_warm(db, http_get=lambda url, timeout: pinged.append(url) or SimpleNamespace(status_code=200), now=NOW)
    assert pinged == ['https://main-4kqeqojbsq-uc.a.run.app/api/ai-chat/health'] and result['main_status'] == 200
    marker = db.store['whatsapp_inbox'][result['marker']]
    assert marker['status'] == 'warmup' and result['marker'].startswith('warmup-')


def test_old_markers_are_removed_and_fresh_ones_kept():
    db = FakeFirestore()
    db.store['whatsapp_inbox'] = {
        'warmup-1': {'status': 'warmup', 'created_at': NOW - timedelta(hours=2)},
        'warmup-2': {'status': 'warmup', 'created_at': NOW - timedelta(minutes=5)},
        'SM1': {'status': 'done', 'created_at': NOW - timedelta(days=3)},   # real messages are never touched
    }
    result = kw.keep_warm(db, http_get=lambda url, timeout: SimpleNamespace(status_code=200), now=NOW)
    assert result['removed'] == 1
    assert 'warmup-1' not in db.store['whatsapp_inbox'] and {'warmup-2', 'SM1', result['marker']} <= set(db.store['whatsapp_inbox'])


def test_a_failed_ping_does_not_fail_the_schedule():
    db = FakeFirestore()

    def boom(url, timeout):
        raise RuntimeError('main is cold')

    result = kw.keep_warm(db, http_get=boom, now=NOW)
    assert result['main_status'] is None and 'marker' in result


def test_it_does_nothing_while_the_channel_is_off(monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_ENABLED', 'false')
    db = FakeFirestore()
    assert kw.keep_warm(db, http_get=lambda *a, **k: 1 / 0) == {'skipped': 'channel off'}
    assert 'whatsapp_inbox' not in db.store


def test_the_worker_ignores_markers_and_only_preloads(monkeypatch):
    called = []
    monkeypatch.setattr(kw, 'prewarm', lambda: called.append('sdk'))
    from flask import Flask
    assert routes.process_inbox_message(Flask(__name__), 'warmup-123') == 'warm' and called == ['sdk']


def test_a_marker_is_never_processed_as_a_message():
    db = FakeFirestore()
    db.store['whatsapp_inbox'] = {'warmup-1': {'status': 'warmup', 'created_at': NOW}}
    deps = wa.Deps(send=lambda *a: 1 / 0, run_chat=lambda *a: 1 / 0, download_media=lambda u: b'', now=lambda: NOW)
    assert wa.process_inbox(db, 'warmup-1', deps) == 'skipped'


def test_the_sdk_client_is_built_once_and_only_on_demand(monkeypatch):
    from routes import ai_chat_routes
    monkeypatch.setattr(ai_chat_routes, 'anthropic_client', None)
    monkeypatch.setattr(ai_chat_routes, 'ANTHROPIC_API_KEY', '')
    assert ai_chat_routes.get_anthropic_client() is None          # no key: never imports the SDK
    monkeypatch.setattr(ai_chat_routes, 'ANTHROPIC_API_KEY', 'sk-test')
    first = ai_chat_routes.get_anthropic_client()
    assert first is not None and ai_chat_routes.get_anthropic_client() is first


def test_prewarm_refreshes_the_prompt_cache_at_most_once_per_interval(monkeypatch):
    from routes import ai_chat_routes
    sent = []
    monkeypatch.setattr(ai_chat_routes, 'get_anthropic_client', lambda: object())
    monkeypatch.setattr(ai_chat_routes, 'warm_prompt_cache', lambda: sent.append(1))
    monkeypatch.setattr(kw, '_last_cache_warm', 0.0)
    t = [100000.0]
    monkeypatch.setattr(kw.time, 'time', lambda: t[0])
    kw.prewarm()
    kw.prewarm()
    assert len(sent) == 1
    t[0] += kw.CACHE_WARM_EVERY + 1
    kw.prewarm()
    assert len(sent) == 2


def test_a_failing_cache_refresh_never_breaks_the_warmup(monkeypatch):
    from routes import ai_chat_routes
    monkeypatch.setattr(ai_chat_routes, 'get_anthropic_client', lambda: object())
    monkeypatch.setattr(ai_chat_routes, 'warm_prompt_cache', lambda: 1 / 0)
    monkeypatch.setattr(kw, '_last_cache_warm', 0.0)
    kw.prewarm()  # must not raise


def test_warm_prompt_cache_sends_the_whatsapp_prefix_with_a_tiny_budget(monkeypatch):
    from routes import ai_chat_routes
    seen = {}

    def fake_create(system_prompt, messages, extra_system=None, channel='web', max_tokens=None):
        seen.update(system=system_prompt, channel=channel, max_tokens=max_tokens)

    monkeypatch.setattr(ai_chat_routes, 'create_ai_message', fake_create)
    ai_chat_routes.warm_prompt_cache()
    assert seen['channel'] == 'whatsapp' and seen['max_tokens'] <= 32
    assert seen['system'] == ai_chat_routes.build_system_prompt('whatsapp')
