"""Security of /api/scheduler/check-overdue-events: it writes data and sends WhatsApp, so it must not be public"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402
from services import scheduler_service  # noqa: E402
from utils import auth  # noqa: E402

URL = '/api/scheduler/check-overdue-events'
TOKEN = 'k3Zq-test-scheduler-secret-0123456789abcdef'


@pytest.fixture
def calls(monkeypatch):
    seen = {'normal': 0, 'forced': 0}

    async def normal():
        seen['normal'] += 1
        return {'success': True, 'overdue_count': 0, 'reminders_sent': 0}

    async def manual(force=False):
        seen['forced'] += 1
        return {'success': True, 'overdue_count': 0, 'reminders_sent': 0}

    monkeypatch.setattr(scheduler_service, 'check_overdue_events', normal)
    monkeypatch.setattr(scheduler_service, 'manual_check_overdue_events', manual)
    monkeypatch.setenv('SCHEDULER_AUTH_TOKEN', TOKEN)
    monkeypatch.setattr(auth, 'get_db', lambda: object())
    return seen


@pytest.fixture
def client():
    main.limiter.enabled = False
    main.app.config['TESTING'] = True
    return main.app.test_client()


def _ran(calls):
    return calls['normal'] + calls['forced']


# ---------- the attacks that worked before ----------

@pytest.mark.parametrize('method,query', [('get', '?force=true'), ('get', ''), ('post', ''), ('post', '?force=true')])
def test_anonymous_callers_cannot_run_it(client, calls, method, query):
    res = getattr(client, method)(URL + query)
    assert res.status_code == 401 and _ran(calls) == 0


def test_the_cloudscheduler_jobname_header_is_not_a_credential(client, calls):
    # what the old code "checked": any client can send this
    res = client.post(URL, headers={'X-CloudScheduler-JobName': 'check-overdue-events'})
    assert res.status_code == 401 and _ran(calls) == 0


@pytest.mark.parametrize('given', ['wrong', TOKEN[:-1], TOKEN + 'x', TOKEN.upper(), ' ', 'ñ' * 40])
def test_wrong_tokens_are_rejected(client, calls, given):
    res = client.post(URL, headers={auth.SCHEDULER_HEADER: given})
    assert res.status_code == 401 and _ran(calls) == 0


# ---------- fails closed ----------

@pytest.mark.parametrize('configured', ['', 'short', 'your_secure_random_token_here_change_in_production', 'changeme'])
def test_a_missing_weak_or_placeholder_secret_closes_the_endpoint(client, calls, monkeypatch, configured):
    monkeypatch.setenv('SCHEDULER_AUTH_TOKEN', configured)
    for given in (configured, 'anything', ''):
        res = client.post(URL, headers={auth.SCHEDULER_HEADER: given})
        assert res.status_code == 401 and _ran(calls) == 0


def test_no_secret_configured_at_all(client, calls, monkeypatch):
    monkeypatch.delenv('SCHEDULER_AUTH_TOKEN', raising=False)
    assert client.post(URL, headers={auth.SCHEDULER_HEADER: 'x' * 40}).status_code == 401 and _ran(calls) == 0


# ---------- the legitimate callers ----------

def test_cloud_scheduler_with_the_secret_runs_the_daily_check(client, calls):
    res = client.post(URL, headers={auth.SCHEDULER_HEADER: TOKEN})
    assert res.status_code == 200 and calls == {'normal': 1, 'forced': 0}


def test_force_is_ignored_on_the_scheduler_post(client, calls):
    client.post(URL + '?force=true', headers={auth.SCHEDULER_HEADER: TOKEN})
    assert calls == {'normal': 1, 'forced': 0}


def test_an_authorized_manual_get_can_force(client, calls):
    res = client.get(URL + '?force=true', headers={auth.SCHEDULER_HEADER: TOKEN})
    assert res.status_code == 200 and calls == {'normal': 0, 'forced': 1}


def test_dry_run_proves_access_without_running_anything(client, calls):
    ok = client.post(URL + '?dry_run=true', headers={auth.SCHEDULER_HEADER: TOKEN})
    assert ok.status_code == 200 and ok.get_json() == {'success': True, 'dry_run': True, 'caller': 'cloud-scheduler'}
    assert client.post(URL + '?dry_run=true').status_code == 401   # and it does not open a hole of its own
    assert _ran(calls) == 0


def test_a_signed_in_admin_can_run_it_manually(client, calls, monkeypatch):
    monkeypatch.setenv('ADMIN_EMAILS', 'pablo@example.com')
    monkeypatch.setattr(auth.firebase_auth, 'verify_id_token', lambda token: {'uid': 'u1', 'email': 'Pablo@Example.com'})
    res = client.get(URL + '?force=true', headers={'Authorization': 'Bearer good'})
    assert res.status_code == 200 and calls['forced'] == 1


def test_a_signed_in_non_admin_cannot(client, calls, monkeypatch):
    monkeypatch.setenv('ADMIN_EMAILS', 'pablo@example.com')
    monkeypatch.setattr(auth.firebase_auth, 'verify_id_token', lambda token: {'uid': 'u2', 'email': 'cliente@example.com'})
    assert client.get(URL + '?force=true', headers={'Authorization': 'Bearer good'}).status_code == 403 and _ran(calls) == 0


def test_an_invalid_firebase_token_cannot(client, calls, monkeypatch):
    def boom(token):
        raise ValueError('bad token')
    monkeypatch.setattr(auth.firebase_auth, 'verify_id_token', boom)
    assert client.get(URL, headers={'Authorization': 'Bearer forged'}).status_code == 401 and _ran(calls) == 0


def test_the_secret_header_does_not_unlock_other_admin_endpoints(client, calls):
    # it is a scheduler credential only: the AI endpoints still need a Firebase admin session
    assert client.post('/api/ai-chat/', json={'messages': []}, headers={auth.SCHEDULER_HEADER: TOKEN}).status_code == 401
    assert client.get('/api/ai-chat/pending/x', headers={auth.SCHEDULER_HEADER: TOKEN}).status_code == 401
