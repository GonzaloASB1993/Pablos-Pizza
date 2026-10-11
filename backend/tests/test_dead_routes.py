"""Characterization: the blueprint wins the routes that main.py used to duplicate; debug routes are gone"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402


@pytest.mark.parametrize('method,path,endpoint', [
    ('GET', '/api/bookings/', 'bookings.get_bookings'),
    ('PUT', '/api/bookings/abc', 'bookings.update_booking'),
    ('DELETE', '/api/bookings/abc', 'bookings.delete_booking'),
    ('GET', '/api/gallery/event/abc', 'gallery.get_gallery_by_event'),
])
def test_blueprint_serves_the_route(method, path, endpoint):
    adapter = main.app.url_map.bind('localhost')
    assert adapter.match(path, method=method)[0] == endpoint


def test_no_duplicate_method_rule_pairs():
    seen = {}
    for rule in main.app.url_map.iter_rules():
        for m in rule.methods - {'HEAD', 'OPTIONS'}:
            key = (m, rule.rule)
            assert key not in seen, f'{key} served by {seen[key]} and {rule.endpoint}'
            seen[key] = rule.endpoint


def test_debug_test_movements_route_removed():
    assert '/api/inventory/test-movements' not in {r.rule for r in main.app.url_map.iter_rules()}
