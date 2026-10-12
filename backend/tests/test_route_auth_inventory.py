"""Route auth inventory: every route must be admin-protected, explicitly public, or listed as known debt.

KNOWN_OPEN is security debt: admin endpoints that still have no auth. Each hardening batch must REMOVE the entries
it protects (the test fails if an entry is already protected, forcing the list to shrink). A brand-new route that is
not decorated with require_admin / require_scheduler_or_admin and not in PUBLIC_ALLOWED fails the first test.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402

PUBLIC_ALLOWED = {
    ('GET', '/'),
    ('GET', '/api/health'),
    ('GET', '/api/ai-chat/health'),
    ('GET', '/cal/<booking_id>'),
    ('GET', '/api/gallery/public'),
    ('GET', '/api/settings/comunas-lejanas'),
    ('POST', '/api/bookings/'),
    ('POST', '/api/contacts'),
    ('POST', '/api/payments/create-preference'),
    ('GET', '/api/payments/status/<booking_id>'),
    ('POST', '/api/payments/webhook'),
    ('POST', '/api/whatsapp/webhook'),  # Twilio signature
}

# Debt paid off: every non-public route is admin-protected. Keep empty; a new unprotected route must be public on purpose.
KNOWN_OPEN = set()


def _routes():
    for rule in main.app.url_map.iter_rules():
        if rule.endpoint == 'static':
            continue
        view = main.app.view_functions[rule.endpoint]
        for method in sorted(rule.methods - {'HEAD', 'OPTIONS'}):
            yield method, rule.rule, bool(getattr(view, '_requires_admin', False))


def test_every_route_is_protected_public_or_known_debt():
    offenders = [
        (m, r) for m, r, protected in _routes()
        if not protected and (m, r) not in PUBLIC_ALLOWED and (m, r) not in KNOWN_OPEN
    ]
    assert not offenders, f'Routes without auth (decorate with require_admin or list them on purpose): {offenders}'


def test_known_open_has_no_protected_or_stale_entries():
    protected = {(m, r) for m, r, p in _routes() if p}
    existing = {(m, r) for m, r, _ in _routes()}
    assert not (KNOWN_OPEN & protected), f'Already protected, remove from KNOWN_OPEN: {sorted(KNOWN_OPEN & protected)}'
    assert not (KNOWN_OPEN - existing), f'Route no longer exists, remove from KNOWN_OPEN: {sorted(KNOWN_OPEN - existing)}'


def test_public_allowed_is_not_protected_and_exists():
    protected = {(m, r) for m, r, p in _routes() if p}
    existing = {(m, r) for m, r, _ in _routes()}
    assert not (PUBLIC_ALLOWED & protected)
    assert PUBLIC_ALLOWED <= existing, sorted(PUBLIC_ALLOWED - existing)
