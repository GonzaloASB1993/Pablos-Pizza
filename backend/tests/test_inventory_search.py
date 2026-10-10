"""Tests for fuzzy inventory search"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import inventory_search as search  # noqa: E402
from services import inventory_service as inv  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402


@pytest.fixture
def db():
    fake = FakeFirestore()
    for name, category, unit in [('Harina 000', 'Secos', 'kg'), ('Queso mozzarella', 'Lácteos', 'kg'),
                                 ('Salsa de tomate', 'Salsas', 'lt'), ('Aceite de oliva', 'Aceites', 'lt'),
                                 ('Bolsas de papel', 'Envases', 'unidad')]:
        inv.create_item(fake, {'name': name, 'category': category, 'current_stock': 4, 'min_stock': 1,
                               'max_stock': 10, 'unit': unit, 'cost_per_unit': 1000})
    return fake


def test_contains_match_ranks_first(db):
    matches = search.search_items(db, 'harina')
    assert matches[0]['name'] == 'Harina 000' and matches[0]['match'] == 'contains'
    assert matches[0]['unit'] == 'kg' and matches[0]['current_stock'] == 4


def test_accents_case_and_typos_are_tolerated(db):
    assert search.search_items(db, 'QUESO MOZARELLA')[0]['name'] == 'Queso mozzarella'
    assert search.search_items(db, 'aceite oliba')[0]['name'] == 'Aceite de oliva'


def test_unrelated_query_finds_nothing(db):
    assert search.search_items(db, 'detergente') == []
    assert search.search_items(db, '   ') == []


def test_duplicates_only_returns_near_certain_matches(db):
    assert [m['name'] for m in search.find_duplicates(db, 'Harina')] == ['Harina 000']
    assert search.find_duplicates(db, 'Harina integral') == []  # similar, but not the same product


def test_vocabulary_lists_categories_and_units(db):
    categories, units = search.catalog_vocabulary(db)
    assert 'Lácteos' in categories and units == ['kg', 'lt', 'unidad']


def test_limit_is_respected(db):
    assert len(search.search_items(db, 'de', limit=1, threshold=0.0)) == 1


def test_search_inventory_tool(db, monkeypatch):
    from routes import ai_chat_routes
    monkeypatch.setattr(ai_chat_routes, 'get_db', lambda: db)
    result = ai_chat_routes.execute_tool('search_inventory', {'query': 'queso'})
    assert result['matches'][0]['name'] == 'Queso mozzarella'
    assert 'Lácteos' in result['known_categories'] and 'kg' in result['known_units']
    assert ai_chat_routes.execute_tool('search_inventory', {'query': 'zzzz'})['matches'] == []
