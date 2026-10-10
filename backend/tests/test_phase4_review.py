"""Regression tests for the findings of the phase-4 (block A) review"""
import os
import sys
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes import ai_chat_routes  # noqa: E402
from services import booking_proposals as bp  # noqa: E402
from services import expense_proposals  # noqa: E402
from services import pending_actions_service as pas  # noqa: E402
from services import whatsapp_agent as wa  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402
from utils import clock  # noqa: E402

ADMIN = '+56911111111'
NOW = datetime(2026, 10, 12, 15, 0, 0)
USER = wa.user_for(ADMIN)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_ENABLED', 'true')
    monkeypatch.setenv('AI_WHATSAPP_ALLOWED', ADMIN)
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))
    monkeypatch.setattr('utils.audit.log_audit', lambda *a, **k: None)


# ---------- Chile's "today" (the server runs in UTC) ----------

def test_the_business_day_is_chiles_not_utcs():
    late_evening_utc = datetime(2026, 10, 12, 1, 30, tzinfo=timezone.utc)   # 22:30 on the 11th in Santiago (UTC-3)
    assert clock.today_cl(late_evening_utc) == date(2026, 10, 11)
    assert clock.now_cl(late_evening_utc).hour == 22
    assert clock.today_cl(datetime(2026, 10, 12, 4, 0, tzinfo=timezone.utc)) == date(2026, 10, 12)
    assert clock.today_cl(datetime(2026, 10, 12, 4, 0)) == date(2026, 10, 12)  # naive input is read as UTC


def test_winter_offset_is_applied_too():
    assert clock.now_cl(datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)).hour == 8  # UTC-4 in winter


def test_the_assistant_gets_chiles_date_in_its_prompt(monkeypatch):
    seen = []

    class Model:
        def create(self, **params):
            seen.append(params['system'][0]['text'])
            return SimpleNamespace(content=[SimpleNamespace(type='text', text='ok')], stop_reason='end_turn',
                                   usage=SimpleNamespace(input_tokens=1, output_tokens=1), model='m')

    monkeypatch.setattr(ai_chat_routes, 'anthropic_client', SimpleNamespace(messages=Model()))
    monkeypatch.setattr(ai_chat_routes, 'AI_CHAT_SERVER_FALLBACK', False)
    monkeypatch.setattr(clock, 'now_cl', lambda now_utc=None: datetime(2026, 10, 11, 22, 30))
    with Flask(__name__).test_request_context():
        ai_chat_routes.run_chat([{'role': 'user', 'content': 'hola'}], USER)
    assert 'HOY ES: Domingo, 2026-10-11' in seen[0]


def test_a_booking_for_tonights_date_is_not_rejected_as_past_after_20h_in_chile(monkeypatch):
    monkeypatch.setattr(bp, 'today_cl', lambda: date(2026, 10, 11))      # UTC would already say the 12th
    monkeypatch.setattr('services.booking_proposals.today_cl', lambda: date(2026, 10, 11))
    payload = {'client_name': 'Ana Pérez', 'services': ['pizzeros'], 'event_date': '2026-10-11', 'event_time': '23:00',
               'location': 'Av. Siempre Viva 1', 'pizzeros_participants': 12}
    action = bp.propose_booking(FakeFirestore(), payload, USER)
    assert action['status'] == 'pending'


# ---------- warnings fail SAFE on WhatsApp ----------

@pytest.mark.parametrize('warning', [
    'La fecha del documento es futura.',
    'La fecha del documento tiene más de un año.',
    "Línea 2 (Sal fina): se parece a 'Harina 000' que ya existe. Si es el mismo producto, cámbialo a insumo existente.",
    'La diferencia con el stock registrado es mayor al 50 %. Verifica el conteo y la unidad.',
    'Quilicura es comuna lejana: incluye un cargo de $20.000.',
    'Una advertencia nueva que alguien agregue mañana.',
])
def test_decision_changing_warnings_are_shown(warning):
    assert wa.key_warnings([warning]) == [warning]


def test_known_noise_is_hidden():
    noise = ['Factura: el IVA (19 %) es crédito fiscal.', 'Sin folio: la detección de duplicados es menos confiable.',
             'stock mínimo y máximo en 0 (no se pueden leer de la boleta).', 'Al confirmar se avisa por WhatsApp (administrador y socio).',
             'Otros gastos del evento en $0. Si hubo bencina…', 'Ya existe el cliente Ana: la reserva se vinculará a él.']
    assert wa.key_warnings(noise) == []


def test_only_two_warnings_are_shown_and_the_rest_are_counted():
    shown = wa.key_warnings(['Posible duplicado: x.', 'El total no cuadra con la suma.', 'La fecha del documento es futura.',
                             'Una advertencia nueva.'])
    assert shown[0].startswith('Posible duplicado') and 'no cuadra' in shown[1] and shown[2] == '+2 aviso(s) más: míralos en el panel'


# ---------- a SI for a proposal that is no longer alive ----------

def test_si_after_the_proposal_was_resolved_elsewhere_never_reaches_the_model():
    db, sent, calls = FakeFirestore(), [], []
    proposal = expense_proposals.propose_expense(db, {'supplier': 'Copec', 'date': '2026-10-10', 'total': 25000}, USER)

    def run(messages, user):
        calls.append(1)
        return {'response': 'Listo.', 'choices': [], 'pending_actions': [pas.serialize(proposal)]}

    deps = wa.Deps(send=lambda p, b: sent.append(b), run_chat=run, download_media=lambda u: b'', now=lambda: NOW)
    wa.store_inbound(db, {'MessageSid': 'SM1', 'From': f'whatsapp:{ADMIN}', 'Body': 'registra la boleta', 'NumMedia': '0'})
    wa.process_inbox(db, 'SM1', deps)
    pas.cancel(db, proposal['id'])                                    # cancelled from the web panel meanwhile

    wa.store_inbound(db, {'MessageSid': 'SM2', 'From': f'whatsapp:{ADMIN}', 'Body': 'SI', 'NumMedia': '0'})
    assert wa.process_inbox(db, 'SM2', deps) == 'command'
    assert calls == [1] and 'ya no está pendiente' in sent[-1]
    assert 'variable_expenses' not in db.store
    history = db.store['whatsapp_conversations'][ADMIN]['history']
    assert history[-2:] == [{'role': 'user', 'content': 'SI'}, {'role': 'assistant', 'content': sent[-1]}]

    # and once the stale proposals are forgotten, a SI is plain text for the agent again
    wa.store_inbound(db, {'MessageSid': 'SM3', 'From': f'whatsapp:{ADMIN}', 'Body': 'SI', 'NumMedia': '0'})
    assert wa.process_inbox(db, 'SM3', deps) == 'answered' and calls == [1, 1]


# ---------- trimming the agent's words next to a proposal ----------

def test_a_later_question_is_kept_when_the_agent_text_is_trimmed():
    text = 'Dejé la propuesta. ' + 'Relleno que sobra. ' * 20 + '\n\nOtro párrafo que sobra.\n\n¿Es factura o boleta?'
    out = wa.short_text(text)
    assert out.startswith('Dejé la propuesta.') and out.endswith('¿Es factura o boleta?') and 'Otro párrafo' not in out
    assert wa.short_text('') == '' and wa.short_text('Listo.') == 'Listo.'


def test_long_proposals_point_to_the_panel_for_the_rest():
    action = {'type': 'inventory_receipt', 'summary': 'Compra', 'warnings': [], 'context': {},
              'payload': {'lines': [{'classification': 'new', 'name': f'I{i}', 'quantity': 1, 'unit': 'kg', 'amount': 1, 'description': 'x'}
                                    for i in range(9)]}}
    assert '… y 5 más (detalle en el panel)' in wa.describe_action(action)


# ---------- usage reflects the cache ----------

def test_cached_tokens_are_reported():
    class Model:
        def create(self, **params):
            usage = SimpleNamespace(input_tokens=77, output_tokens=50, cache_read_input_tokens=10201, cache_creation_input_tokens=0)
            return SimpleNamespace(content=[SimpleNamespace(type='text', text='ok')], stop_reason='end_turn', usage=usage, model='m')

    ai_chat_routes.anthropic_client = SimpleNamespace(messages=Model())
    ai_chat_routes.AI_CHAT_SERVER_FALLBACK = False
    try:
        with Flask(__name__).test_request_context():
            usage = ai_chat_routes.run_chat([{'role': 'user', 'content': 'hola'}], USER)['usage']
    finally:
        ai_chat_routes.anthropic_client = None
        ai_chat_routes.AI_CHAT_SERVER_FALLBACK = True
    assert usage == {'input_tokens': 77, 'output_tokens': 50, 'cache_read_tokens': 10201, 'cache_write_tokens': 0}
