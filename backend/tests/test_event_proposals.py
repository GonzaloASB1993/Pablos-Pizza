"""Tests for AI proposals of event supplies (estimate) and consumption (real)"""
import os
import sys
from datetime import date, timedelta

import pytest
from flask import Flask, g
from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.clock import today_cl  # noqa: E402

from routes import ai_chat_routes as routes  # noqa: E402
from services import event_inventory_service as ev  # noqa: E402
from services import event_proposals as ep  # noqa: E402
from services import pending_actions_service as pas  # noqa: E402
from services.inventory_proposals import ProposalError  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402

USER = {'uid': 'u1', 'email': 'admin@example.com'}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))
    monkeypatch.setattr('utils.audit.log_audit', lambda *a, **k: None)


@pytest.fixture
def db():
    fake = FakeFirestore()
    when = (today_cl() + timedelta(days=5)).isoformat()
    fake.store['bookings'] = {
        'b1': {'client_name': 'Martina', 'status': 'confirmed', 'event_date': when, 'participants': 12, 'financials': {'income': 100000}},
        'done': {'client_name': 'Colegio', 'status': 'completed', 'event_date': when},
        'pend': {'client_name': 'Pedro', 'status': 'pending', 'event_date': when},
    }
    fake.store['inventory'] = {
        'flour': {'id': 'flour', 'name': 'Harina', 'unit': 'kg', 'current_stock': 50, 'min_stock': 2, 'cost_per_unit': 1000},
        'cheese': {'id': 'cheese', 'name': 'Queso', 'unit': 'kg', 'current_stock': 6, 'min_stock': 1, 'cost_per_unit': 6000,
                   'weighted_avg_cost': 5000},
    }
    return fake


def _supplies(**o):
    data = {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'estimated_quantity': 10}, {'item_id': 'cheese', 'estimated_quantity': 4}]}
    data.update(o)
    return data


def _consumption(**o):
    data = {'booking_id': 'b1', 'items': [{'item_id': 'flour', 'actual_quantity_consumed': 8}], 'total_other_expenses': 3000}
    data.update(o)
    return data


# ---------- validation ----------

@pytest.mark.parametrize('bad', [
    {'items': []},
    {'items': [{'item_id': 'flour', 'estimated_quantity': 0}]},
    {'items': [{'item_id': 'flour', 'estimated_quantity': 1}, {'item_id': 'flour', 'estimated_quantity': 2}]},
    {'booking_id': ''},
])
def test_invalid_supplies_payloads(bad):
    with pytest.raises(ValidationError):
        ep.SuppliesPayload.model_validate(_supplies(**bad))


@pytest.mark.parametrize('item', [
    {'item_id': 'flour'},                                                          # neither
    {'item_id': 'flour', 'quantity_returned': 1, 'actual_quantity_consumed': 2},   # both
    {'item_id': 'flour', 'actual_quantity_consumed': -1},
])
def test_consumption_item_needs_exactly_one_quantity(item):
    with pytest.raises(ValidationError):
        ep.ConsumptionPayload.model_validate(_consumption(items=[item]))


# ---------- supplies ----------

def test_supplies_proposal_costs_the_estimate_and_writes_nothing(db):
    action = ep.propose_event_supplies(db, _supplies(), USER)
    assert action['type'] == 'event_supplies' and action['status'] == 'pending'
    assert 'Martina' in action['summary'] and '$30.000' in action['summary']  # 10*1000 + 4*5000
    assert action['context']['rows'][1]['cost_per_unit'] == 5000
    assert 'event_supplies' not in db.store


def test_confirming_supplies_creates_the_estimate_without_moving_stock(db):
    action = ep.propose_event_supplies(db, _supplies(), USER)
    result = pas.confirm(db, action['id'], USER)['result']
    supplies, = db.store['event_supplies'].values()
    assert supplies['booking_id'] == 'b1' and supplies['estimated_total_cost'] == 30000
    assert result['estimated_total_cost'] == 30000 and db.store['inventory']['flour']['current_stock'] == 50
    assert db.store['bookings']['b1']['financials']['estimated_supply_cost'] == 30000.0


def test_supplies_for_a_booking_that_already_has_them_replace_them(db):
    first = ep.propose_event_supplies(db, _supplies(), USER)
    pas.confirm(db, first['id'], USER)
    second = ep.propose_event_supplies(db, _supplies(items=[{'item_id': 'flour', 'estimated_quantity': 5}]), USER)
    assert any('REEMPLAZA' in w for w in second['warnings'])
    pas.confirm(db, second['id'], USER)
    supplies, = db.store['event_supplies'].values()  # still one document
    assert [i['item_id'] for i in supplies['items']] == ['flour'] and supplies['estimated_total_cost'] == 5000


def test_supplies_confirm_twice_creates_one_document(db):
    action = ep.propose_event_supplies(db, _supplies(), USER)
    pas.confirm(db, action['id'], USER)
    pas.confirm(db, action['id'], USER)
    assert len(db.store['event_supplies']) == 1


def test_supplies_errors_for_the_model(db):
    with pytest.raises(ProposalError):
        ep.propose_event_supplies(db, _supplies(booking_id='nope'), USER)
    with pytest.raises(ProposalError) as err:
        ep.propose_event_supplies(db, _supplies(booking_id='done'), USER)
    assert 'completed' in str(err.value) and 'confirmadas' in str(err.value)
    with pytest.raises(ProposalError):
        ep.propose_event_supplies(db, _supplies(booking_id='pend'), USER)
    with pytest.raises(ProposalError):
        ep.propose_event_supplies(db, _supplies(items=[{'item_id': 'ghost', 'estimated_quantity': 1}]), USER)
    with pytest.raises(ProposalError) as err:
        ep.propose_event_supplies(db, _supplies(items=[{'item_id': 'cheese', 'estimated_quantity': 99}]), USER)
    assert 'Queso' in str(err.value) and 'disponible 6' in str(err.value)


# ---------- consumption ----------

def test_consumption_proposal_previews_without_touching_stock(db):
    action = ep.propose_event_consumption(db, _consumption(), USER)
    assert action['type'] == 'event_consumption'
    assert 'insumos $8.000 + otros $3.000 = $11.000' in action['summary']
    row, = action['context']['rows']
    assert row['stock_before'] == 50 and row['stock_after'] == 42 and row['total_cost'] == 8000
    assert db.store['inventory']['flour']['current_stock'] == 50 and 'event_consumption' not in db.store


def test_confirming_consumption_deducts_stock_and_updates_the_booking(db):
    action = ep.propose_event_consumption(db, _consumption(), USER)
    result = pas.confirm(db, action['id'], USER)['result']
    assert db.store['inventory']['flour']['current_stock'] == 42 and result['total_cost'] == 11000
    fin = db.store['bookings']['b1']['financials']
    assert fin['supply_cost'] == 8000 and fin['other_expenses'] == 3000 and fin['profit'] == 100000 - 11000
    movement, = db.store['inventory_movements'].values()
    assert movement['reference_type'] == 'event_consumption' and movement['quantity'] == -8


def test_consumption_from_what_came_back_uses_the_estimate(db):
    pas.confirm(db, ep.propose_event_supplies(db, _supplies(), USER)['id'], USER)
    action = ep.propose_event_consumption(
        db, _consumption(items=[{'item_id': 'flour', 'quantity_returned': 3}, {'item_id': 'cheese', 'quantity_returned': 1}]), USER)
    flour, cheese = action['context']['rows']
    assert flour['actual_quantity_consumed'] == 7 and cheese['actual_quantity_consumed'] == 3
    pas.confirm(db, action['id'], USER)
    assert db.store['inventory']['flour']['current_stock'] == 43 and db.store['inventory']['cheese']['current_stock'] == 3


def test_returning_more_than_taken_is_an_error_for_the_model(db):
    pas.confirm(db, ep.propose_event_supplies(db, _supplies(), USER)['id'], USER)
    with pytest.raises(ProposalError) as err:
        ep.propose_event_consumption(db, _consumption(items=[{'item_id': 'flour', 'quantity_returned': 11}]), USER)
    assert 'no puede ser mayor que lo llevado' in str(err.value)


def test_registering_again_warns_and_replaces_without_double_deducting(db):
    first = ep.propose_event_consumption(db, _consumption(), USER)
    pas.confirm(db, first['id'], USER)
    second = ep.propose_event_consumption(db, _consumption(items=[{'item_id': 'flour', 'actual_quantity_consumed': 5}]), USER)
    assert any('REEMPLAZA' in w for w in second['warnings'])
    assert second['context']['rows'][0]['stock_before'] == 50  # stock after giving the previous consumption back
    pas.confirm(db, second['id'], USER)
    assert db.store['inventory']['flour']['current_stock'] == 45
    assert len(db.store['event_consumption']) == 1 and len(db.store['inventory_movements']) == 1


def test_consumption_confirm_twice_deducts_once(db):
    action = ep.propose_event_consumption(db, _consumption(), USER)
    pas.confirm(db, action['id'], USER)
    pas.confirm(db, action['id'], USER)
    assert db.store['inventory']['flour']['current_stock'] == 42


def test_insufficient_stock_is_an_error_for_the_model_and_nothing_is_saved(db):
    with pytest.raises(ProposalError) as err:
        ep.propose_event_consumption(db, _consumption(items=[{'item_id': 'cheese', 'actual_quantity_consumed': 99}]), USER)
    assert 'Insufficient stock for Queso' in str(err.value)
    assert 'pending_actions' not in db.store


def test_warnings_for_variance_missing_estimate_and_zero_expenses(db):
    pas.confirm(db, ep.propose_event_supplies(db, _supplies(items=[{'item_id': 'flour', 'estimated_quantity': 10}]), USER)['id'], USER)
    action = ep.propose_event_consumption(db, _consumption(
        items=[{'item_id': 'flour', 'actual_quantity_consumed': 20}, {'item_id': 'cheese', 'actual_quantity_consumed': 1}],
        total_other_expenses=0), USER)
    joined = ' | '.join(action['warnings'])
    assert '100 % más de lo estimado' in joined
    assert 'Queso no estaba en la estimación' in joined
    assert 'Otros gastos del evento en $0' in joined


def test_returned_without_an_estimate_is_flagged(db):
    action = ep.propose_event_consumption(db, _consumption(items=[{'item_id': 'flour', 'quantity_returned': 2}]), USER)
    assert any('no hay cantidad estimada' in w for w in action['warnings'])
    assert action['context']['rows'][0]['actual_quantity_consumed'] == 0


def test_edited_payload_at_confirm_is_revalidated_and_used(db):
    action = ep.propose_event_consumption(db, _consumption(), USER)
    edited = {**action['payload'], 'items': [{'item_id': 'flour', 'actual_quantity_consumed': 2, 'quantity_returned': None}],
              'total_other_expenses': 500}
    pas.confirm(db, action['id'], USER, edited_payload=edited)
    assert db.store['inventory']['flour']['current_stock'] == 48
    with pytest.raises(pas.InvalidPayload):
        pas.confirm(db, ep.propose_event_consumption(db, _consumption(), USER)['id'], USER,
                    edited_payload={**action['payload'], 'items': []})


# ---------- the guard: the user must have chosen the event ----------

def _tool(db, monkeypatch, name, payload, user_text):
    monkeypatch.setattr(routes, 'get_db', lambda: db)
    with Flask(__name__).test_request_context():
        g.current_user = USER
        g.ai_user_text = user_text
        return routes.execute_tool(name, payload), list(getattr(g, 'ai_pending_actions', []))


def test_a_proposal_for_an_event_the_user_never_chose_is_refused(db, monkeypatch):
    result, cards = _tool(db, monkeypatch, 'propose_event_consumption', _consumption(), 'Sube los insumos de la fiesta')
    assert 'error' in result and 'ask_choice' in result['error'] and cards == []
    assert 'pending_actions' not in db.store


def test_a_proposal_for_the_event_the_user_tapped_goes_through(db, monkeypatch):
    result, cards = _tool(db, monkeypatch, 'propose_event_consumption', _consumption(),
                          'Sube los insumos\nMartina · en 5 días [id: b1]')
    assert result['status'] == 'pending_confirmation' and 'NO está guardada' in result['message']
    assert cards[0]['type'] == 'event_consumption'
    assert db.store['inventory']['flour']['current_stock'] == 50


def test_the_guard_does_not_apply_to_other_proposals(db, monkeypatch):
    result, _ = _tool(db, monkeypatch, 'propose_stock_adjustment',
                      {'item_id': 'flour', 'mode': 'count', 'quantity': 40}, 'sin id de evento')
    assert result['status'] == 'pending_confirmation'
