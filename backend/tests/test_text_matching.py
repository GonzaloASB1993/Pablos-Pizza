"""Tests for utils.text_matching"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.text_matching import calculate_similarity, normalize_text  # noqa: E402


def test_normalize_text_strips_accents_case_and_spaces():
    assert normalize_text('  Azúcar Flor ') == 'azucar flor'
    assert normalize_text('PIÑA') == 'pina'


def test_normalize_text_handles_empty_values():
    assert normalize_text(None) == ''
    assert normalize_text('') == ''


def test_similarity_exact_and_containment():
    assert calculate_similarity('Harina', 'harina') == 1.0
    assert calculate_similarity('Harina 000', 'Harina') == 0.9


def test_similarity_unrelated_is_low_and_related_is_higher():
    unrelated = calculate_similarity('tomate', 'detergente')
    related = calculate_similarity('queso mozzarella', 'queso mozarella')
    assert related > unrelated
    assert related > 0.7
