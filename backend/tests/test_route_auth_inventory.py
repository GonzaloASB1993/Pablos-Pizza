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

KNOWN_OPEN = {
    ('GET', '/api/bookings/'),
    ('DELETE', '/api/bookings/<booking_id>'),
    ('GET', '/api/bookings/<booking_id>'),
    ('PUT', '/api/bookings/<booking_id>'),
    ('POST', '/api/bookings/<booking_id>/payments'),
    ('DELETE', '/api/bookings/<booking_id>/payments/<payment_id>'),
    ('PUT', '/api/bookings/<booking_id>/payments/<payment_id>'),
    ('POST', '/api/bookings/migrate-source'),
    ('GET', '/api/contacts'),
    ('GET', '/api/contacts/'),
    ('POST', '/api/contacts/'),
    ('DELETE', '/api/contacts/<contact_id>'),
    ('GET', '/api/contacts/<contact_id>'),
    ('PUT', '/api/contacts/<contact_id>'),
    ('POST', '/api/contacts/<contact_id>/respond'),
    ('PUT', '/api/contacts/<contact_id>/respond'),
    ('GET', '/api/customers/'),
    ('POST', '/api/customers/'),
    ('DELETE', '/api/customers/<customer_id>'),
    ('GET', '/api/customers/<customer_id>'),
    ('PUT', '/api/customers/<customer_id>'),
    ('GET', '/api/customers/<customer_id>/bookings'),
    ('GET', '/api/customers/search'),
    ('POST', '/api/event-consumption/'),
    ('GET', '/api/event-consumption/event/<event_id>'),
    ('POST', '/api/event-supplies/'),
    ('PUT', '/api/event-supplies/<supplies_id>'),
    ('GET', '/api/event-supplies/booking/<booking_id>'),
    ('GET', '/api/event-supplies/status/<booking_id>'),
    ('GET', '/api/events/'),
    ('POST', '/api/events/'),
    ('GET', '/api/events/<event_id>'),
    ('PUT', '/api/events/<event_id>'),
    ('PUT', '/api/events/<event_id>/publish'),
    ('POST', '/api/events/generate-description'),
    ('GET', '/api/expenses/fixed'),
    ('POST', '/api/expenses/fixed'),
    ('DELETE', '/api/expenses/fixed/<expense_id>'),
    ('PUT', '/api/expenses/fixed/<expense_id>'),
    ('GET', '/api/expenses/tax'),
    ('POST', '/api/expenses/tax'),
    ('GET', '/api/expenses/variable'),
    ('POST', '/api/expenses/variable'),
    ('DELETE', '/api/expenses/variable/<expense_id>'),
    ('PUT', '/api/expenses/variable/<expense_id>'),
    ('GET', '/api/gallery/'),
    ('DELETE', '/api/gallery/<photo_id>'),
    ('PUT', '/api/gallery/<photo_id>/publish'),
    ('GET', '/api/gallery/event/<event_id>'),
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
    ('GET', '/api/reports/annual/<int:year>'),
    ('GET', '/api/reports/clients/top'),
    ('GET', '/api/reports/dashboard'),
    ('GET', '/api/reports/export/monthly/<int:year>/<int:month>'),
    ('GET', '/api/reports/monthly/<int:year>/<int:month>'),
    ('GET', '/api/reports/waste-summary'),
    ('PUT', '/api/settings/comunas-lejanas'),
    ('GET', '/api/vacuum-sales/'),
    ('POST', '/api/vacuum-sales/'),
    ('DELETE', '/api/vacuum-sales/<sale_id>'),
    ('GET', '/api/vacuum-sales/<sale_id>'),
    ('PUT', '/api/vacuum-sales/<sale_id>'),
    ('POST', '/api/vacuum-sales/<sale_id>/payments'),
    ('DELETE', '/api/vacuum-sales/<sale_id>/payments/<payment_id>'),
    ('PUT', '/api/vacuum-sales/<sale_id>/payments/<payment_id>'),
    ('GET', '/api/vacuum-sales/summary'),
}


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
