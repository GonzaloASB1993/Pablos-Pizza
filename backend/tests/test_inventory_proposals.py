"""Tests for AI inventory proposals: receipts (existing / new / expense lines), updates, adjustments"""
import os
import sys
from datetime import date

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.clock import today_cl  # noqa: E402

from services import inventory_proposals as ip  # noqa: E402
from services import inventory_service as inv  # noqa: E402
from services import pending_actions_service as pas  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402

USER = {'uid': 'u1', 'email': 'admin@example.com'}
TODAY = today_cl().isoformat()


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))
    monkeypatch.setattr('utils.audit.log_audit', lambda *a, **k: None)


@pytest.fixture
def db():
    fake = FakeFirestore()
    for name, category, unit, stock, cost in [('Harina 000', 'Secos', 'kg', 10, 1000), ('Queso mozzarella', 'Lácteos', 'kg', 4, 6000)]:
        inv.create_item(fake, {'name': name, 'category': category, 'current_stock': stock, 'min_stock': 2,
                               'max_stock': 50, 'unit': unit, 'cost_per_unit': cost})
    return fake


def _item_id(db, name):
    return next(i for i, d in db.store['inventory'].items() if d['name'] == name)


def _existing(db, name='Harina 000', **overrides):
    line = {'description': name, 'classification': 'existing', 'item_id': _item_id(db, name),
            'quantity': 25, 'unit': 'kg', 'amount': 28000}
    line.update(overrides)
    return line


def _new(**overrides):
    line = {'description': 'Saco de sal 10 kg', 'classification': 'new', 'name': 'Sal fina', 'category': 'Secos',
            'unit': 'kg', 'quantity': 10, 'amount': 5000}
    line.update(overrides)
    return line


def _expense(**overrides):
    line = {'description': 'Bencina', 'classification': 'expense', 'amount': 20000, 'expense_category': 'otros'}
    line.update(overrides)
    return line


def _receipt(lines, **overrides):
    data = {'supplier': 'Mayorista Lo Valledor', 'date': TODAY, 'document_type': 'boleta', 'folio': '9981', 'lines': lines}
    data.update(overrides)
    return data


# ---------- validation ----------

@pytest.mark.parametrize('bad', [
    {'classification': 'existing', 'item_id': None},
    {'classification': 'existing', 'quantity': 0},
    {'classification': 'new', 'name': None},
    {'classification': 'new', 'unit': None},
    {'classification': 'new', 'category': None},
    {'classification': 'new', 'quantity': 5, 'amount': 0},
    {'classification': 'new', 'min_stock': 10, 'max_stock': 5},
    {'classification': 'expense', 'amount': 0},
    {'classification': 'whatever'},
])
def test_invalid_lines_are_rejected(db, bad):
    line = {'description': 'x', 'amount': 1000, 'item_id': _item_id(db, 'Harina 000'), 'quantity': 1, 'name': 'N',
            'unit': 'kg', 'category': 'C', 'classification': 'new'}
    line.update(bad)
    with pytest.raises(ValidationError):
        ip.ReceiptPayload.model_validate(_receipt([line]))


def test_receipt_needs_at_least_one_line():
    with pytest.raises(ValidationError):
        ip.ReceiptPayload.model_validate(_receipt([]))


def test_chilean_amounts_and_dates_are_accepted(db):
    payload = ip.ReceiptPayload.model_validate(_receipt([_existing(db, amount='$28.000')], date='10-10-2026', total='28.000'))
    assert payload.lines[0].amount == 28000 and payload.total == 28000 and payload.date == date(2026, 10, 10)


# ---------- propose does not write ----------

def test_propose_writes_no_inventory_or_expense(db):
    before = {k: dict(v) for k, v in db.store['inventory'].items()}
    action = ip.propose_receipt(db, _receipt([_existing(db), _new(), _expense()]), USER)
    assert action['status'] == 'pending' and action['type'] == 'inventory_receipt'
    assert db.store['inventory'] == before
    assert 'inventory_movements' not in db.store and 'variable_expenses' not in db.store


def test_summary_counts_each_kind_of_line(db):
    action = ip.propose_receipt(db, _receipt([_existing(db), _new(), _expense()], total=53000), USER)
    assert 'Mayorista Lo Valledor' in action['summary'] and '$53.000' in action['summary']
    assert '1 compra de insumo' in action['summary'] and '1 insumo nuevo' in action['summary'] and '1 gasto' in action['summary']


# ---------- confirm: the three line kinds ----------

def test_confirm_applies_each_line_exactly_once_without_double_counting(db):
    lines = [_existing(db, amount=28000), _new(amount=5000), _expense(amount=20000)]
    action = ip.propose_receipt(db, _receipt(lines, total=53000), USER)
    result = pas.confirm(db, action['id'], USER)['result']

    flour = db.store['inventory'][_item_id(db, 'Harina 000')]
    assert flour['current_stock'] == 35  # 10 + 25
    assert flour['weighted_avg_cost'] == pytest.approx((10 * 1000 + 28000) / 35)

    salt = next(d for d in db.store['inventory'].values() if d['name'] == 'Sal fina')
    assert salt['current_stock'] == 10 and salt['weighted_avg_cost'] == 500 and salt['source'] == 'ai_agent'
    assert salt['min_stock'] == 0 and salt['max_stock'] == 0

    expense, = db.store['variable_expenses'].values()
    assert expense['amount'] == 20000 and expense['category'] == 'otros' and 'Bencina' in expense['description']
    assert expense['source'] == 'ai_agent' and expense['folio'] == '9981'

    # anti double count: money in stock + money in expenses == the document, nothing counted twice
    stock_value = sum(m['total_cost'] for m in db.store['inventory_movements'].values())
    assert stock_value + expense['amount'] == 53000
    assert len(db.store['inventory_movements']) == 2
    assert result['inventory_lines'] == 2 and result['expense_lines'] == 1


def test_movements_reference_the_action_and_supplier(db):
    action = ip.propose_receipt(db, _receipt([_existing(db)]), USER)
    pas.confirm(db, action['id'], USER)
    movement, = db.store['inventory_movements'].values()
    assert movement['reference_type'] == 'ai_receipt' and movement['reference_id'] == action['id']
    assert movement['supplier'] == 'Mayorista Lo Valledor' and movement['movement_type'] == 'purchase'
    assert movement['cost_per_unit'] == 1120  # 28000 / 25 kg


def test_new_item_without_initial_stock_creates_no_movement(db):
    action = ip.propose_inventory_item(db, {'name': 'Orégano', 'category': 'Especias', 'unit': 'kg'}, USER)
    pas.confirm(db, action['id'], USER)
    oregano = next(d for d in db.store['inventory'].values() if d['name'] == 'Orégano')
    assert oregano['current_stock'] == 0
    assert 'inventory_movements' not in db.store


def test_confirm_twice_does_not_duplicate_anything(db):
    action = ip.propose_receipt(db, _receipt([_existing(db), _new(), _expense()]), USER)
    pas.confirm(db, action['id'], USER)
    pas.confirm(db, action['id'], USER)
    assert db.store['inventory'][_item_id(db, 'Harina 000')]['current_stock'] == 35
    assert len(db.store['inventory_movements']) == 2 and len(db.store['variable_expenses']) == 1
    assert len([d for d in db.store['inventory'].values() if d['name'] == 'Sal fina']) == 1


def test_retry_after_a_failed_line_does_not_repeat_the_applied_ones(db):
    lines = [_existing(db), _new(), _expense()]
    action = ip.propose_receipt(db, _receipt(lines), USER)
    flour_id = _item_id(db, 'Harina 000')

    # line 2 (new item) fails the first time
    real_create = inv.create_item
    calls = {'n': 0}

    def flaky(db_, data, item_id=None, extra=None):
        calls['n'] += 1
        if calls['n'] == 1:
            raise RuntimeError('firestore hiccup')
        return real_create(db_, data, item_id=item_id, extra=extra)

    inv_create = inv.create_item
    inv.create_item = flaky
    try:
        with pytest.raises(RuntimeError):
            pas.confirm(db, action['id'], USER)
        assert db.store['pending_actions'][action['id']]['status'] == 'failed'
        pas.confirm(db, action['id'], USER)  # retry
    finally:
        inv.create_item = inv_create

    assert db.store['inventory'][flour_id]['current_stock'] == 35  # applied once, not twice
    assert len(db.store['inventory_movements']) == 2 and len(db.store['variable_expenses']) == 1


def test_edited_classification_is_what_gets_applied(db):
    action = ip.propose_receipt(db, _receipt([_existing(db, amount=28000), _expense(description='Bolsas', amount=3000)]), USER)
    edited = action['payload']
    edited['lines'][1] = _existing(db, 'Queso mozzarella', quantity=1, amount=3000, unit='kg', description='Bolsas')
    pas.confirm(db, action['id'], USER, edited_payload=edited)
    assert 'variable_expenses' not in db.store  # the line moved from expense to stock, never both
    assert db.store['inventory'][_item_id(db, 'Queso mozzarella')]['current_stock'] == 5


# ---------- proposal checks (warnings / errors for the model) ----------

def test_new_item_with_the_same_name_as_an_existing_one_is_rejected(db):
    with pytest.raises(ip.ProposalError) as err:
        ip.propose_receipt(db, _receipt([_new(name='harina 000')]), USER)
    assert 'ya existe' in str(err.value) and 'existing' in str(err.value)


def test_new_item_that_looks_like_an_existing_one_only_warns(db):
    action = ip.propose_receipt(db, _receipt([_new(name='Harina')]), USER)
    assert any("se parece a 'Harina 000'" in w for w in action['warnings'])


def test_unknown_item_id_is_an_error_for_the_model(db):
    with pytest.raises(ip.ProposalError):
        ip.propose_receipt(db, _receipt([_existing(db, item_id='nope')]), USER)


def test_warnings_for_unit_mismatch_price_jump_and_sum(db):
    action = ip.propose_receipt(db, _receipt([_existing(db, unit='saco', quantity=1, amount=28000)], total=99000), USER)
    joined = ' | '.join(action['warnings'])
    assert 'unidad (saco)' in joined
    assert 'difiere' in joined       # $28.000/kg against an average of $1.000/kg
    assert 'no cuadra' in joined


def test_default_stock_limits_are_flagged_for_new_items(db):
    action = ip.propose_receipt(db, _receipt([_new()]), USER)
    assert any('mínimo y máximo en 0' in w for w in action['warnings'])


def test_new_category_is_flagged(db):
    action = ip.propose_receipt(db, _receipt([_new(category='Congelados')]), USER)
    assert any("categoría 'Congelados' es nueva" in w for w in action['warnings'])


def test_context_carries_candidates_and_vocabulary_for_the_card(db):
    action = ip.propose_receipt(db, _receipt([_expense(description='Harina 000 saco', amount=28000)]), USER)
    ctx = action['context']
    assert 'Secos' in ctx['known_categories'] and 'kg' in ctx['known_units']
    assert ctx['candidates']['0'][0]['name'] == 'Harina 000'


def test_same_document_twice_warns_as_duplicate(db):
    first = ip.propose_receipt(db, _receipt([_existing(db)]), USER)
    second = ip.propose_receipt(db, _receipt([_existing(db)]), USER)
    assert any('duplicado' in w for w in second['warnings'])
    pas.confirm(db, first['id'], USER)
    third = ip.propose_receipt(db, _receipt([_existing(db)]), USER)
    assert any('duplicado' in w and 'confirmada' in w for w in third['warnings'])


def test_purchase_without_supplier_is_never_a_duplicate(db):
    ip.propose_inventory_purchase(db, {'item_id': _item_id(db, 'Harina 000'), 'quantity': 5, 'total_cost': 5000}, USER)
    again = ip.propose_inventory_purchase(db, {'item_id': _item_id(db, 'Harina 000'), 'quantity': 5, 'total_cost': 5000}, USER)
    assert not any('duplicado' in w for w in again['warnings'])


# ---------- single-purpose tools ----------

def test_propose_inventory_purchase_is_a_one_line_receipt(db):
    action = ip.propose_inventory_purchase(
        db, {'item_id': _item_id(db, 'Harina 000'), 'quantity': 25, 'total_cost': 28000, 'supplier': 'Lo Valledor'}, USER)
    pas.confirm(db, action['id'], USER)
    assert db.store['inventory'][_item_id(db, 'Harina 000')]['current_stock'] == 35


def test_propose_inventory_item_with_initial_purchase(db):
    action = ip.propose_inventory_item(db, {'name': 'Aceitunas', 'category': 'Conservas', 'unit': 'kg',
                                            'quantity': 5, 'total_cost': 15000, 'min_stock': 1, 'max_stock': 10}, USER)
    pas.confirm(db, action['id'], USER)
    olives = next(d for d in db.store['inventory'].values() if d['name'] == 'Aceitunas')
    assert olives['current_stock'] == 5 and olives['weighted_avg_cost'] == 3000
    assert (olives['min_stock'], olives['max_stock']) == (1, 10)


# ---------- update ----------

def test_update_changes_only_the_given_fields(db):
    item_id = _item_id(db, 'Harina 000')
    action = ip.propose_inventory_update(db, {'item_id': item_id, 'changes': {'supplier': 'Lo Valledor', 'min_stock': 4}}, USER)
    assert 'supplier' in action['summary'] and action['context']['before']['min_stock'] == 2
    assert db.store['inventory'][item_id]['supplier'] == ''  # not applied yet
    pas.confirm(db, action['id'], USER)
    stored = db.store['inventory'][item_id]
    assert stored['supplier'] == 'Lo Valledor' and stored['min_stock'] == 4 and stored['name'] == 'Harina 000'
    assert stored['current_stock'] == 10  # stock is never edited through an update


def test_update_rejects_empty_changes_and_stock_fields(db):
    item_id = _item_id(db, 'Harina 000')
    with pytest.raises(ValidationError):
        ip.propose_inventory_update(db, {'item_id': item_id, 'changes': {}}, USER)
    action = ip.propose_inventory_update(db, {'item_id': item_id, 'changes': {'name': 'Harina 0000', 'current_stock': 999}}, USER)
    assert 'current_stock' not in action['payload']['changes']


# ---------- adjustments ----------

def test_count_adjustment_sets_stock_with_history_at_average_cost(db):
    item_id = _item_id(db, 'Harina 000')
    action = ip.propose_stock_adjustment(db, {'item_id': item_id, 'mode': 'count', 'quantity': 7, 'reason': 'Conteo mensual'}, USER)
    assert '10 → 7' in action['summary'] and db.store['inventory'][item_id]['current_stock'] == 10
    pas.confirm(db, action['id'], USER)
    stored = db.store['inventory'][item_id]
    assert stored['current_stock'] == 7 and stored['weighted_avg_cost'] == 1000
    movement, = db.store['inventory_movements'].values()
    assert movement['quantity'] == -3 and movement['movement_type'] == 'adjustment' and movement['notes'] == 'Conteo mensual'


def test_count_adjustment_upwards_does_not_change_average_cost(db):
    item_id = _item_id(db, 'Harina 000')
    action = ip.propose_stock_adjustment(db, {'item_id': item_id, 'mode': 'count', 'quantity': 12}, USER)
    pas.confirm(db, action['id'], USER)
    stored = db.store['inventory'][item_id]
    assert stored['current_stock'] == 12 and stored['weighted_avg_cost'] == 1000


def test_count_equal_to_stock_is_a_noop(db):
    item_id = _item_id(db, 'Harina 000')
    action = ip.propose_stock_adjustment(db, {'item_id': item_id, 'mode': 'count', 'quantity': 10}, USER)
    pas.confirm(db, action['id'], USER)
    assert 'inventory_movements' not in db.store


def test_waste_removes_stock_and_cannot_exceed_it(db):
    item_id = _item_id(db, 'Queso mozzarella')
    action = ip.propose_stock_adjustment(db, {'item_id': item_id, 'mode': 'waste', 'quantity': 1.5, 'reason': 'Vencido'}, USER)
    pas.confirm(db, action['id'], USER)
    assert db.store['inventory'][item_id]['current_stock'] == 2.5
    assert next(iter(db.store['inventory_movements'].values()))['movement_type'] == 'waste'
    with pytest.raises(ip.ProposalError):
        ip.propose_stock_adjustment(db, {'item_id': item_id, 'mode': 'waste', 'quantity': 99}, USER)


def test_large_count_difference_warns(db):
    item_id = _item_id(db, 'Harina 000')
    action = ip.propose_stock_adjustment(db, {'item_id': item_id, 'mode': 'count', 'quantity': 1}, USER)
    assert any('50 %' in w for w in action['warnings'])


# ---------- through the chat tools ----------

def test_every_proposal_tool_is_declared_and_routed():
    from routes import ai_chat_routes
    declared = {t['name'] for t in ai_chat_routes.TOOLS}
    assert set(ai_chat_routes.PROPOSAL_TOOLS) <= declared
    assert {'search_inventory', 'propose_receipt', 'propose_inventory_item', 'propose_inventory_purchase',
            'propose_inventory_update', 'propose_stock_adjustment'} <= declared


def test_prompt_enforces_search_first_and_one_classification_per_line():
    from routes import ai_chat_routes
    prompt = ai_chat_routes.SYSTEM_PROMPT
    assert 'ANTES de proponer cualquier insumo nuevo' in prompt
    assert 'Una línea nunca es insumo y gasto a la vez' in prompt
    assert 'Nunca adivines un `item_id`' in prompt


def test_tool_returns_errors_to_the_model_and_a_card_to_the_admin(db, monkeypatch):
    from flask import Flask, g
    from routes import ai_chat_routes
    monkeypatch.setattr(ai_chat_routes, 'get_db', lambda: db)

    with Flask(__name__).test_request_context():
        g.current_user = USER
        bad = ai_chat_routes.execute_tool('propose_receipt', _receipt([_existing(db, item_id='nope')]))
        assert 'error' in bad and 'pending_action_id' not in bad

        invalid = ai_chat_routes.execute_tool('propose_receipt', _receipt([_new(quantity=5, amount=0)]))
        assert 'error' in invalid and invalid['details']

        ok = ai_chat_routes.execute_tool('propose_receipt', _receipt([_existing(db), _expense()]))
        assert ok['status'] == 'pending_confirmation' and 'NO está guardada' in ok['message']
        card, = g.ai_pending_actions
        assert card['type'] == 'inventory_receipt' and card['context']['items']

    assert 'inventory_movements' not in db.store and 'variable_expenses' not in db.store
