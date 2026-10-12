"""Per-IP rate limits on the public endpoints (in-memory storage: per instance, a mitigation, not a guarantee)"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402
from routes import payments_routes  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    fake = FakeFirestore()
    for module in (main, payments_routes):
        monkeypatch.setattr(module, 'get_db', lambda: fake)
    from routes import bookings_routes
    monkeypatch.setattr(bookings_routes, 'get_db', lambda: fake)
    monkeypatch.setattr(main.limiter, 'enabled', True)
    main.limiter.reset()
    monkeypatch.setitem(main.app.config, 'TESTING', True)
    yield main.app.test_client()
    main.limiter.reset()


def _hit(client, method, url, n, ip='203.0.113.7', **kwargs):
    return [getattr(client, method)(url, headers={'X-Forwarded-For': ip}, **kwargs) for _ in range(n)]


@pytest.mark.parametrize('method,url,allowed', [
    ('post', '/api/bookings/', 5),
    ('post', '/api/contacts', 5),
    ('post', '/api/payments/create-preference', 10),
    ('get', '/api/payments/status/abc', 60),
])
def test_the_request_after_the_per_minute_limit_is_a_json_429(client, method, url, allowed):
    kwargs = {'json': {}} if method == 'post' else {}
    results = _hit(client, method, url, allowed, **kwargs)
    assert all(r.status_code != 429 for r in results)
    blocked = getattr(client, method)(url, headers={'X-Forwarded-For': '203.0.113.7'}, **kwargs)
    assert blocked.status_code == 429 and blocked.is_json and blocked.get_json()['error']


def test_the_limit_is_per_ip(client):
    _hit(client, 'post', '/api/contacts', 5, json={})
    other = client.post('/api/contacts', headers={'X-Forwarded-For': '198.51.100.9'}, json={})
    assert other.status_code == 400  # validation answer, not 429


def test_the_limits_are_the_documented_ones(client):
    declared = {name.split('.')[-1]: sorted(str(g.limit_provider) for g in groups)
                for name, groups in main.limiter.limit_manager._decorated_limits.items()}
    assert declared['create_booking'] == ['30 per day', '5 per minute']
    assert declared['handle_contacts'] == ['20 per day', '5 per minute']
    assert declared['create_preference'] == ['10 per minute']
    assert declared['get_payment_status'] == ['60 per minute']
