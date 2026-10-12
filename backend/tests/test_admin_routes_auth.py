"""Admin routes must require a Firebase ID token from an allowed admin; public routes must keep working without one.

Every batch below lists the (method, rule) pairs that were hardened in that batch. For each one:
  - no token                      -> 401 and the handler never runs (no database access)
  - invalid token                 -> 401 and the handler never runs
  - valid token, non-admin email  -> 403 and the handler never runs
  - valid token, admin email      -> the handler runs (anything but 401/403)
"""
import asyncio
import os
import re
import socket
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402
from utils import auth  # noqa: E402

ADMIN = 'pablo@example.com'

# ---- batch 2: reads with personal / financial data ----
BATCH2 = [
    ('GET', '/api/customers/'),
    ('GET', '/api/customers/search'),
    ('GET', '/api/customers/<customer_id>'),
    ('GET', '/api/customers/<customer_id>/bookings'),
    ('GET', '/api/contacts'),
    ('GET', '/api/contacts/'),
    ('GET', '/api/contacts/<contact_id>'),
    ('GET', '/api/bookings/'),
    ('GET', '/api/bookings/<booking_id>'),
    ('GET', '/api/expenses/fixed'),
    ('GET', '/api/expenses/variable'),
    ('GET', '/api/expenses/tax'),
    ('GET', '/api/reports/annual/<int:year>'),
    ('GET', '/api/reports/clients/top'),
    ('GET', '/api/reports/dashboard'),
    ('GET', '/api/reports/export/monthly/<int:year>/<int:month>'),
    ('GET', '/api/reports/monthly/<int:year>/<int:month>'),
    ('GET', '/api/reports/waste-summary'),
    ('GET', '/api/vacuum-sales/'),
    ('GET', '/api/vacuum-sales/<sale_id>'),
    ('GET', '/api/vacuum-sales/summary'),
    ('GET', '/api/events/'),
    ('GET', '/api/events/<event_id>'),
    ('GET', '/api/gallery/'),
    ('GET', '/api/gallery/event/<event_id>'),
]

# ---- batch 3: low-traffic writes and the rest of the admin tools ----
BATCH3 = [
    ('POST', '/api/event-consumption/'),
    ('GET', '/api/event-consumption/event/<event_id>'),
    ('POST', '/api/event-supplies/'),
    ('PUT', '/api/event-supplies/<supplies_id>'),
    ('GET', '/api/event-supplies/booking/<booking_id>'),
    ('GET', '/api/event-supplies/status/<booking_id>'),
    ('POST', '/api/events/'),
    ('PUT', '/api/events/<event_id>'),
    ('PUT', '/api/events/<event_id>/publish'),
    ('POST', '/api/events/generate-description'),
    ('POST', '/api/expenses/fixed'),
    ('DELETE', '/api/expenses/fixed/<expense_id>'),
    ('PUT', '/api/expenses/fixed/<expense_id>'),
    ('POST', '/api/expenses/tax'),
    ('POST', '/api/expenses/variable'),
    ('DELETE', '/api/expenses/variable/<expense_id>'),
    ('PUT', '/api/expenses/variable/<expense_id>'),
    ('DELETE', '/api/gallery/<photo_id>'),
    ('PUT', '/api/gallery/<photo_id>/publish'),
    ('POST', '/api/gallery/upload'),
    ('GET', '/api/inventory-movements/'),
    ('GET', '/api/inventory/'),
    ('POST', '/api/inventory/'),
    ('DELETE', '/api/inventory/<item_id>'),
    ('GET', '/api/inventory/<item_id>'),
    ('PUT', '/api/inventory/<item_id>'),
    ('POST', '/api/inventory/<item_id>/auto-nutrition'),
    ('PUT', '/api/inventory/<item_id>/stock'),
    ('GET', '/api/inventory/alerts'),
    ('GET', '/api/inventory/categories'),
    ('POST', '/api/inventory/movements/'),
    ('GET', '/api/inventory/movements/<movement_id>'),
    ('POST', '/api/inventory/movements/<movement_id>/revert'),
    ('GET', '/api/inventory/nutrition-lookup'),
    ('GET', '/api/production-batches/'),
    ('POST', '/api/production-batches/'),
    ('DELETE', '/api/production-batches/<batch_id>'),
    ('POST', '/api/production-batches/<batch_id>/complete'),
    ('GET', '/api/production-batches/<batch_id>/label'),
    ('POST', '/api/production-batches/<batch_id>/simple-complete'),
    ('PUT', '/api/production-batches/<batch_id>/status'),
    ('GET', '/api/recipes/'),
    ('POST', '/api/recipes/'),
    ('DELETE', '/api/recipes/<recipe_id>'),
    ('GET', '/api/recipes/<recipe_id>'),
    ('PUT', '/api/recipes/<recipe_id>'),
    ('POST', '/api/recipes/<recipe_id>/calculate-cost'),
    ('GET', '/api/recipes/<recipe_id>/nutrition'),
    ('PUT', '/api/settings/comunas-lejanas'),
    ('POST', '/api/vacuum-sales/'),
    ('DELETE', '/api/vacuum-sales/<sale_id>'),
    ('PUT', '/api/vacuum-sales/<sale_id>'),
    ('POST', '/api/vacuum-sales/<sale_id>/payments'),
    ('DELETE', '/api/vacuum-sales/<sale_id>/payments/<payment_id>'),
    ('PUT', '/api/vacuum-sales/<sale_id>/payments/<payment_id>'),
]

# ---- batch 4: critical writes (bookings, contacts, customers) ----
BATCH4 = [
    ('DELETE', '/api/bookings/<booking_id>'),
    ('PUT', '/api/bookings/<booking_id>'),
    ('POST', '/api/bookings/<booking_id>/payments'),
    ('DELETE', '/api/bookings/<booking_id>/payments/<payment_id>'),
    ('PUT', '/api/bookings/<booking_id>/payments/<payment_id>'),
    ('POST', '/api/bookings/migrate-source'),
    ('POST', '/api/contacts/'),
    ('DELETE', '/api/contacts/<contact_id>'),
    ('PUT', '/api/contacts/<contact_id>'),
    ('POST', '/api/contacts/<contact_id>/respond'),
    ('PUT', '/api/contacts/<contact_id>/respond'),
    ('POST', '/api/customers/'),
    ('DELETE', '/api/customers/<customer_id>'),
    ('PUT', '/api/customers/<customer_id>'),
]

BATCHES = {
    'batch2': BATCH2,
    'batch3': BATCH3,
    'batch4': BATCH4,
}
ALL_ADMIN = [pair for batch in BATCHES.values() for pair in batch]

PUBLIC = [
    ('POST', '/api/bookings/'),
    ('POST', '/api/contacts'),
    ('GET', '/api/gallery/public'),
    ('GET', '/api/settings/comunas-lejanas'),
    ('POST', '/api/payments/create-preference'),
    ('GET', '/api/payments/status/<booking_id>'),
    ('GET', '/api/health'),
]


def _url(rule):
    rule = re.sub(r'<int:year>', '2024', rule)
    rule = re.sub(r'<int:month>', '1', rule)
    return re.sub(r'<[^>]+>', 'abc', rule)


def _ids(pairs):
    return [f'{m} {r}' for m, r in pairs]


def _call(client, method, rule, headers=None):
    kwargs = {'headers': headers or {}}
    if method in ('POST', 'PUT', 'DELETE'):
        kwargs['json'] = {}
    return getattr(client, method.lower())(_url(rule), **kwargs)


@pytest.fixture
def handler_db_calls(monkeypatch):
    """Record every database access made by handlers (the auth module keeps its own, harmless binding)."""
    calls = []

    def recorder(*args, **kwargs):
        calls.append(1)
        return None

    for name, module in list(sys.modules.items()):
        if module is None or module is auth or not hasattr(module, 'get_db'):
            continue
        if name == 'main' or name == 'database' or name.split('.')[0] in ('routes', 'services', 'repositories', 'utils', 'models'):
            monkeypatch.setattr(module, 'get_db', recorder)
    monkeypatch.setattr(auth, 'get_db', lambda: object())
    return calls


@pytest.fixture
def client(monkeypatch, handler_db_calls):
    main.limiter.enabled = False
    monkeypatch.setitem(main.app.config, 'TESTING', True)
    monkeypatch.setitem(main.app.config, 'PROPAGATE_EXCEPTIONS', False)
    monkeypatch.setenv('ADMIN_EMAILS', ADMIN)
    monkeypatch.delenv('ENVIRONMENT', raising=False)
    # nothing under test may reach the network
    def no_network(*a, **k):
        raise OSError('network disabled in tests')
    monkeypatch.setattr(socket.socket, 'connect', no_network)
    return main.app.test_client()


def _sign_in(monkeypatch, email):
    monkeypatch.setattr(auth.firebase_auth, 'verify_id_token', lambda token: {'uid': 'u1', 'email': email})


# ---------- admin routes are closed ----------

@pytest.mark.parametrize('method,rule', ALL_ADMIN, ids=_ids(ALL_ADMIN))
def test_no_token_is_401_and_handler_does_not_run(client, handler_db_calls, method, rule):
    res = _call(client, method, rule)
    assert res.status_code == 401
    assert handler_db_calls == []


@pytest.mark.parametrize('method,rule', ALL_ADMIN, ids=_ids(ALL_ADMIN))
def test_invalid_token_is_401_and_handler_does_not_run(client, handler_db_calls, monkeypatch, method, rule):
    def boom(token):
        raise ValueError('bad token')
    monkeypatch.setattr(auth.firebase_auth, 'verify_id_token', boom)
    res = _call(client, method, rule, {'Authorization': 'Bearer forged'})
    assert res.status_code == 401
    assert handler_db_calls == []


@pytest.mark.parametrize('method,rule', ALL_ADMIN, ids=_ids(ALL_ADMIN))
def test_non_admin_email_is_403_and_handler_does_not_run(client, handler_db_calls, monkeypatch, method, rule):
    _sign_in(monkeypatch, 'cliente@example.com')
    res = _call(client, method, rule, {'Authorization': 'Bearer good'})
    assert res.status_code == 403
    assert handler_db_calls == []


@pytest.mark.parametrize('method,rule', ALL_ADMIN, ids=_ids(ALL_ADMIN))
def test_admin_email_reaches_the_handler(client, monkeypatch, method, rule):
    _sign_in(monkeypatch, ADMIN.upper())   # allowlist match is case-insensitive
    res = _call(client, method, rule, {'Authorization': 'Bearer good'})
    assert res.status_code not in (401, 403)


# ---------- public routes keep working without a token ----------

@pytest.mark.parametrize('method,rule', PUBLIC, ids=_ids(PUBLIC))
def test_public_routes_do_not_ask_for_a_token(client, method, rule):
    res = _call(client, method, rule)
    assert res.status_code not in (401, 403)


def test_public_contact_post_creates_while_get_is_admin_only(client, monkeypatch):
    # same URL, two audiences
    assert client.get('/api/contacts').status_code == 401
    res = client.post('/api/contacts', json={})
    assert res.status_code == 400   # validation error from the handler, not an auth error


# ---------- decorator mechanics ----------

def test_decorator_keeps_working_with_async_handlers(monkeypatch, handler_db_calls):
    """require_admin returns the coroutine of an `async def` view untouched, so Flask/asgiref can await it.
    (The app has no async views today and asgiref is not installed, so this exercises the wrapper directly.)"""
    from utils.auth import require_admin

    ran = []

    @require_admin
    async def async_view():
        ran.append(1)
        return 'async-ok'

    assert async_view._requires_admin is True
    assert asyncio.iscoroutinefunction(async_view.__wrapped__)
    monkeypatch.setenv('ADMIN_EMAILS', ADMIN)

    with main.app.test_request_context('/x'):
        body, status = async_view()                       # no token: rejected before the coroutine is created
        assert status == 401 and ran == []

    _sign_in(monkeypatch, ADMIN)
    with main.app.test_request_context('/x', headers={'Authorization': 'Bearer good'}):
        result = async_view()
        assert asyncio.iscoroutine(result)
        assert asyncio.run(result) == 'async-ok' and ran == [1]


# ---------- CORS: the manual wildcard headers are gone from the upload view ----------

def test_upload_preflight_answers_with_flask_cors_headers_not_a_wildcard(client):
    origin = main.cors_origins[0].strip()
    res = client.options('/api/gallery/upload', headers={
        'Origin': origin,
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'authorization,content-type',
    })
    assert res.status_code == 200
    assert res.headers.get_all('Access-Control-Allow-Origin') == [origin]       # exactly one value, the real origin
    assert 'authorization' in res.headers['Access-Control-Allow-Headers'].lower()
    assert 'POST' in res.headers['Access-Control-Allow-Methods']


def test_upload_responses_carry_a_single_cors_origin_header(client, monkeypatch):
    origin = main.cors_origins[0].strip()
    _sign_in(monkeypatch, ADMIN)
    res = client.post('/api/gallery/upload', headers={'Origin': origin, 'Authorization': 'Bearer good'})
    assert res.status_code == 400   # no file: validation error from the handler
    assert res.headers.get_all('Access-Control-Allow-Origin') == [origin]


def test_unauthorized_upload_still_gets_cors_headers_so_the_browser_can_read_the_401(client):
    origin = main.cors_origins[0].strip()
    res = client.post('/api/gallery/upload', headers={'Origin': origin})
    assert res.status_code == 401
    assert res.headers.get_all('Access-Control-Allow-Origin') == [origin]
