"""Tests for the WhatsApp channel: security (signature, allowlist, switch), idempotency, SI/NO and the agent turn"""
import base64
import io
import os
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from flask import Flask
from PIL import Image
from twilio.request_validator import RequestValidator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402,F401  (imported at collection time: it loads backend/.env, which must not happen mid-test)
from routes import ai_chat_routes  # noqa: E402
from routes import whatsapp_routes as routes  # noqa: E402
from services import expense_proposals  # noqa: E402
from services import pending_actions_service as pas  # noqa: E402
from services import whatsapp_agent as wa  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402

ADMIN, PARTNER, STRANGER = '+56911111111', '+56922222222', '+56933333333'
TOKEN = 'twilio-test-token'
URL = 'https://main-test.example.run.app/api/whatsapp/webhook'
NOW = datetime(2026, 10, 12, 15, 0, 0)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_ENABLED', 'true')
    monkeypatch.setenv('ADMIN_WHATSAPP_NUMBER', ADMIN)
    monkeypatch.setenv('PARTNER_WHATSAPP_NUMBER', PARTNER)
    monkeypatch.delenv('AI_WHATSAPP_ALLOWED', raising=False)
    monkeypatch.delenv('AI_WHATSAPP_MODE', raising=False)
    monkeypatch.delenv('WHATSAPP_WEBHOOK_URL', raising=False)
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', TOKEN)
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))
    monkeypatch.setattr('utils.audit.log_audit', lambda *a, **k: None)


@pytest.fixture
def db():
    return FakeFirestore()


def _jpeg(size=(40, 30)):
    out = io.BytesIO()
    Image.new('RGB', size, 'white').save(out, 'JPEG')
    return out.getvalue()


# ============ identity ============

def test_phone_normalization_and_default_allowlist():
    assert wa.normalize_phone('whatsapp:+56 9 1111 1111') == ADMIN and wa.normalize_phone(None) == ''
    assert wa.allowed_numbers() == {ADMIN, PARTNER}
    assert wa.is_allowed(f'whatsapp:{ADMIN}') and not wa.is_allowed(STRANGER) and not wa.is_allowed('')


def test_allowlist_can_be_overridden_and_empty_means_nobody(monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_ALLOWED', f'{STRANGER}, whatsapp:+56944444444')
    assert wa.allowed_numbers() == {STRANGER, '+56944444444'} and not wa.is_allowed(ADMIN)
    monkeypatch.setenv('ADMIN_WHATSAPP_NUMBER', '')
    monkeypatch.setenv('PARTNER_WHATSAPP_NUMBER', '')
    monkeypatch.delenv('AI_WHATSAPP_ALLOWED')
    assert wa.allowed_numbers() == set() and not wa.is_allowed(ADMIN)


# ============ signature ============

def _sign(params, url=URL, token=TOKEN):
    return RequestValidator(token).compute_signature(url, params)


def test_signature_accepts_twilio_and_rejects_everything_else():
    params = {'From': f'whatsapp:{ADMIN}', 'Body': 'hola', 'MessageSid': 'SM1'}
    good = _sign(params)
    assert wa.verify_signature([URL], params, good)
    assert not wa.verify_signature([URL], {**params, 'Body': 'otra cosa'}, good)      # tampered body
    assert not wa.verify_signature([URL], params, _sign(params, token='other'))        # wrong account token
    assert not wa.verify_signature(['https://evil.example/api/whatsapp/webhook'], params, good)
    assert not wa.verify_signature([URL], params, '') and not wa.verify_signature([URL], params, None)
    assert wa.verify_signature(['https://other-host/x', URL], params, good)            # any candidate URL may match


def test_signature_needs_a_configured_token(monkeypatch):
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', '')
    assert not wa.verify_signature([URL], {'a': 'b'}, 'anything')


# ============ webhook ============

@pytest.fixture
def hook(db, monkeypatch):
    monkeypatch.setattr(routes, 'get_db', lambda: db)
    app = Flask(__name__)
    app.register_blueprint(routes.whatsapp_bp)
    client = app.test_client()

    def post(form, signed=True, url=URL):
        headers = {'X-Twilio-Signature': _sign(form, url)} if signed else {}
        return client.post('/api/whatsapp/webhook', data=form, headers=headers, base_url='https://main-test.example.run.app')
    return post


def _form(sender=ADMIN, body='registra un gasto de bencina', sid='SM100', **extra):
    return {'From': f'whatsapp:{sender}', 'To': 'whatsapp:+12017620171', 'Body': body, 'MessageSid': sid, 'NumMedia': '0', **extra}


def test_webhook_stores_a_signed_message_from_an_allowed_number(hook, db):
    res = hook(_form())
    assert res.status_code == 200 and res.mimetype == 'text/xml' and b'<Response>' in res.data
    stored = db.store['whatsapp_inbox']['SM100']
    assert stored['from'] == ADMIN and stored['body'] == 'registra un gasto de bencina' and stored['status'] == 'received'


def test_webhook_is_idempotent_per_message_sid(hook, db):
    hook(_form())
    hook(_form(body='cambiado'))
    assert len(db.store['whatsapp_inbox']) == 1 and db.store['whatsapp_inbox']['SM100']['body'] == 'registra un gasto de bencina'


def test_webhook_rejects_unsigned_and_badly_signed_requests(hook, db):
    assert hook(_form(), signed=False).status_code == 403
    assert hook(_form(), url='https://evil.example/api/whatsapp/webhook').status_code == 403
    assert 'whatsapp_inbox' not in db.store


def test_webhook_ignores_unknown_numbers_without_storing_anything(hook, db):
    res = hook(_form(sender=STRANGER))
    assert res.status_code == 200 and 'whatsapp_inbox' not in db.store


def test_webhook_does_nothing_when_the_channel_is_switched_off(hook, db, monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_ENABLED', 'false')
    assert hook(_form(), signed=False).status_code == 200  # no information leaks, nothing happens
    assert 'whatsapp_inbox' not in db.store


def test_webhook_keeps_media_references(hook, db):
    hook(_form(sid='SM200', NumMedia='1', MediaUrl0='https://api.twilio.com/m/1', MediaContentType0='image/jpeg'))
    assert db.store['whatsapp_inbox']['SM200']['media'] == [{'url': 'https://api.twilio.com/m/1', 'content_type': 'image/jpeg'}]


def test_inline_mode_processes_inside_the_webhook(hook, db, monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_MODE', 'inline')
    seen = []
    monkeypatch.setattr(routes, 'process_inbox_message', lambda app, sid: seen.append(sid))
    hook(_form())
    hook(_form())  # duplicate delivery: processed once
    assert seen == ['SM100']


def test_trigger_mode_never_processes_inside_the_webhook(hook, db, monkeypatch):
    seen = []
    monkeypatch.setattr(routes, 'process_inbox_message', lambda app, sid: seen.append(sid))
    hook(_form())
    assert seen == []


# ============ text helpers ============

@pytest.mark.parametrize('text,expected', [
    ('SI', ('yes', None)), ('Sí', ('yes', None)), ('sí!', ('yes', None)), ('Dale', ('yes', None)), ('ok', ('yes', None)),
    ('NO', ('no', None)), ('cancelar', ('no', None)), ('Si 2', ('yes', 2)), ('no 1', ('no', 1)),
    ('SI todas', ('yes', 'all')), ('no todo', ('no', 'all')),
    ('sí, pero cámbialo a 6 kg', None), ('hola', None), ('no sé', None), ('', None), ('si 2 y 3', None),
])
def test_commands_are_only_bare_si_and_no(text, expected):
    assert wa.parse_command(text) == expected


def test_markdown_becomes_whatsapp_text():
    out = wa.to_whatsapp('## Inventario\n\n**Harina**: 3 kg\n- ⚠️ Queso bajo\n\n| Item | Stock |\n|---|---|\n| Harina | 3 kg |\n\n[web](https://x.cl)')
    assert out.startswith('*Inventario*') and '*Harina*: 3 kg' in out and '• ⚠️ Queso bajo' in out
    assert 'Item — Stock' in out and 'Harina — 3 kg' in out and '---' not in out and '|' not in out
    assert 'web (https://x.cl)' in out


def test_long_messages_are_split_without_losing_text():
    text = '\n\n'.join(f'Párrafo {i}: ' + 'x' * 300 for i in range(12)) + '\n\n' + 'y' * 3000
    parts = wa.chunks(text, size=1400)
    assert all(len(p) <= 1400 for p in parts) and len(parts) > 2
    assert ''.join(parts).replace('\n', '').replace(' ', '') == text.replace('\n', '').replace(' ', '')
    assert wa.chunks('hola') == ['hola'] and wa.chunks('') == ['']


# ============ the worker ============

class Sent(list):
    def __call__(self, phone, body):
        self.append((phone, body))

    @property
    def bodies(self):
        return [b for _, b in self]


def _deps(run_chat, sent=None, download=None, now=NOW):
    return wa.Deps(send=sent if sent is not None else Sent(), run_chat=run_chat,
                   download_media=download or (lambda url: _jpeg()), now=lambda: now)


def _answer(text='Hola, soy el asistente.', **extra):
    return lambda messages, user: {'response': text, 'pending_actions': [], 'choices': [], 'usage': {'input_tokens': 1}, **extra}


def _inbox(db, sid='SM1', sender=ADMIN, body='hola', media=None):
    wa.store_inbound(db, {'MessageSid': sid, 'From': f'whatsapp:{sender}', 'Body': body, 'NumMedia': str(len(media or [])),
                          **{k: v for i, m in enumerate(media or []) for k, v in
                             ((f'MediaUrl{i}', m[0]), (f'MediaContentType{i}', m[1]))}})
    return sid


def test_a_text_turn_calls_the_agent_and_answers_by_whatsapp(db):
    calls, sent = [], Sent()
    deps = _deps(lambda m, u: calls.append((m, u)) or {'response': '**Todo bien**', 'pending_actions': [], 'choices': []}, sent)
    assert wa.process_inbox(db, _inbox(db, body='¿cómo va el inventario?'), deps) == 'answered'
    messages, user = calls[0]
    assert messages == [{'role': 'user', 'content': [{'type': 'text', 'text': '¿cómo va el inventario?'}]}]
    assert user == {'uid': f'whatsapp:{ADMIN}', 'email': f'whatsapp:{ADMIN}'}
    assert sent == [(ADMIN, '*Todo bien*')]
    assert db.store['whatsapp_inbox']['SM1']['status'] == 'done'


def test_the_conversation_keeps_text_history_between_messages(db):
    seen = []
    deps = _deps(lambda m, u: seen.append(m) or {'response': 'ok', 'pending_actions': [], 'choices': []})
    wa.process_inbox(db, _inbox(db, 'SM1', body='primero'), deps)
    wa.process_inbox(db, _inbox(db, 'SM2', body='segundo'), deps)
    history = [m['content'] if isinstance(m['content'], str) else m['content'][0]['text'] for m in seen[1]]
    assert history == ['primero', 'ok', 'segundo']


def test_an_old_conversation_starts_fresh(db):
    seen = []
    run = lambda m, u: seen.append(m) or {'response': 'ok', 'pending_actions': [], 'choices': []}  # noqa: E731
    wa.process_inbox(db, _inbox(db, 'SM1', body='ayer'), _deps(run, now=NOW))
    wa.process_inbox(db, _inbox(db, 'SM2', body='hoy'), _deps(run, now=NOW + timedelta(hours=25)))
    assert len(seen[1]) == 1


def test_photos_are_downloaded_compressed_and_never_kept_in_the_history(db):
    seen, downloaded = [], []
    big = io.BytesIO()
    Image.new('RGB', (3000, 2000), 'white').save(big, 'JPEG')
    deps = _deps(lambda m, u: seen.append(m) or {'response': 'Leí la boleta', 'pending_actions': [], 'choices': []},
                 download=lambda url: downloaded.append(url) or big.getvalue())
    sid = _inbox(db, body='registra esta boleta', media=[('https://api.twilio.com/m/1', 'image/jpeg')])
    wa.process_inbox(db, sid, deps)

    assert downloaded == ['https://api.twilio.com/m/1']
    content = seen[0][-1]['content']
    assert content[0] == {'type': 'text', 'text': 'registra esta boleta'} and content[1]['type'] == 'image'
    sent_image = Image.open(io.BytesIO(base64.b64decode(content[1]['source']['data'])))
    assert max(sent_image.size) == 1600 and content[1]['source']['media_type'] == 'image/jpeg'
    history = db.store['whatsapp_conversations'][ADMIN]['history']
    assert history[0]['content'] == 'registra esta boleta [imagen enviada]' and 'base64' not in str(history)


def test_unsupported_media_gets_a_friendly_answer_and_no_agent_call(db):
    called, sent = [], Sent()
    deps = _deps(lambda m, u: called.append(1), sent)
    sid = _inbox(db, body='', media=[('https://api.twilio.com/m/9', 'audio/ogg')])
    assert wa.process_inbox(db, sid, deps) == 'unsupported'
    assert called == [] and 'texto y fotos' in sent.bodies[0]


def test_the_same_message_is_processed_once_even_if_delivered_twice(db):
    runs, sent = [], Sent()
    deps = _deps(lambda m, u: runs.append(1) or {'response': 'ok', 'pending_actions': [], 'choices': []}, sent)
    sid = _inbox(db)
    assert wa.process_inbox(db, sid, deps) == 'answered'
    assert wa.process_inbox(db, sid, deps) == 'skipped'
    assert len(runs) == 1 and len(sent) == 1


def test_the_worker_double_checks_the_allowlist(db):
    runs = []
    sid = _inbox(db, sender=STRANGER)  # stored by some other path
    assert wa.process_inbox(db, sid, _deps(lambda m, u: runs.append(1))) == 'ignored'
    assert runs == [] and db.store['whatsapp_inbox'][sid]['status'] == 'ignored'


def test_daily_limit(db, monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_DAILY_LIMIT', '2')
    sent = Sent()
    deps = _deps(_answer(), sent)
    results = [wa.process_inbox(db, _inbox(db, f'SM{i}'), deps) for i in range(3)]
    assert results == ['answered', 'answered', 'quota'] and 'límite de mensajes' in sent.bodies[-1]


def test_an_agent_failure_apologizes_and_marks_the_message_failed(db):
    def boom(messages, user):
        raise RuntimeError('anthropic down')

    sent = Sent()
    assert wa.process_inbox(db, _inbox(db), _deps(boom, sent)) == 'failed'
    assert 'No pude procesar' in sent.bodies[0]
    assert db.store['whatsapp_inbox']['SM1']['status'] == 'failed' and 'anthropic down' in db.store['whatsapp_inbox']['SM1']['error']


# ============ choices (buttons) ============

def test_choices_are_numbered_and_a_number_picks_one(db):
    choices = [{'id': 'bk1', 'label': 'Martina · sáb 17'}, {'id': 'bk2', 'label': 'Colegio · lun 19'}]
    seen, sent = [], Sent()

    def run(messages, user):
        seen.append(messages)
        return {'response': '¿A qué evento?', 'pending_actions': [], 'choices': choices if len(seen) == 1 else []}

    deps = _deps(run, sent)
    wa.process_inbox(db, _inbox(db, 'SM1', body='insumos del evento'), deps)
    assert '1) Martina · sáb 17' in sent.bodies[0] and '2) Colegio · lun 19' in sent.bodies[0] and 'Responde con el número' in sent.bodies[0]

    wa.process_inbox(db, _inbox(db, 'SM2', body='2'), deps)
    assert seen[1][-1]['content'][0]['text'] == 'Colegio · lun 19 [id: bk2]'  # same shape the web buttons send


def test_a_number_is_plain_text_when_no_question_is_open(db):
    seen = []
    wa.process_inbox(db, _inbox(db, body='2'), _deps(lambda m, u: seen.append(m) or {'response': 'ok', 'pending_actions': [], 'choices': []}))
    assert seen[0][-1]['content'][0]['text'] == '2'


# ============ proposals: SI / NO ============

def _proposal(db, supplier='Copec', total=25000, folio='123'):
    return expense_proposals.propose_expense(db, {'supplier': supplier, 'date': '2026-10-10', 'total': total, 'folio': folio,
                                                  'category': 'otros'}, wa.user_for(ADMIN))


def _proposing(db, *suppliers):
    def run(messages, user):
        actions = [pas.serialize(_proposal(db, s, 1000 * (i + 1), str(i))) for i, s in enumerate(suppliers)]
        return {'response': 'Te dejé la propuesta.', 'pending_actions': actions, 'choices': []}
    return run


def test_a_proposal_is_described_and_waits_for_si(db):
    sent = Sent()
    wa.process_inbox(db, _inbox(db, body='boleta de copec'), _deps(_proposing(db, 'Copec'), sent))
    text = '\n'.join(sent.bodies)
    assert 'Copec' in text and '¿La guardo? *SI* / *NO*' in text
    assert 'variable_expenses' not in db.store  # nothing written yet


def test_si_confirms_the_single_pending_proposal_exactly_once(db):
    sent = Sent()
    wa.process_inbox(db, _inbox(db, 'SM1', body='boleta'), _deps(_proposing(db, 'Copec'), sent))
    runs = []
    deps = _deps(lambda m, u: runs.append(1) or {'response': 'otra cosa', 'pending_actions': [], 'choices': []}, sent)

    assert wa.process_inbox(db, _inbox(db, 'SM2', body='SI'), deps) == 'command'
    assert len(db.store['variable_expenses']) == 1 and '✅' in sent.bodies[-1] and runs == []
    expense, = db.store['variable_expenses'].values()
    assert expense['source'] == 'ai_agent' and expense['created_by'] == f'whatsapp:{ADMIN}'

    # a second SI has nothing to confirm: it is just text for the agent now
    assert wa.process_inbox(db, _inbox(db, 'SM3', body='SI'), deps) == 'answered'
    assert len(db.store['variable_expenses']) == 1 and runs == [1]


def test_no_cancels_without_writing(db):
    sent = Sent()
    wa.process_inbox(db, _inbox(db, 'SM1', body='boleta'), _deps(_proposing(db, 'Copec'), sent))
    wa.process_inbox(db, _inbox(db, 'SM2', body='NO'), _deps(_answer(), sent))
    assert 'variable_expenses' not in db.store and 'Cancelada' in sent.bodies[-1]
    assert next(iter(db.store['pending_actions'].values()))['status'] == 'cancelled'


def test_with_several_proposals_si_alone_asks_which_one(db):
    sent = Sent()
    wa.process_inbox(db, _inbox(db, 'SM1', body='dos boletas'), _deps(_proposing(db, 'Copec', 'Jumbo'), sent))
    assert '*1*:' in '\n'.join(sent.bodies) and '*2*:' in '\n'.join(sent.bodies) and '¿Cuál guardo?' in '\n'.join(sent.bodies)

    wa.process_inbox(db, _inbox(db, 'SM2', body='SI'), _deps(_answer(), sent))
    assert 'varias propuestas' in sent.bodies[-1] and 'variable_expenses' not in db.store

    wa.process_inbox(db, _inbox(db, 'SM3', body='SI 2'), _deps(_answer(), sent))
    expense, = db.store['variable_expenses'].values()
    assert 'Jumbo' in expense['description']

    wa.process_inbox(db, _inbox(db, 'SM4', body='SI 1'), _deps(_answer(), sent))
    assert len(db.store['variable_expenses']) == 2


def test_si_todas_and_no_todas(db):
    sent = Sent()
    wa.process_inbox(db, _inbox(db, 'SM1', body='dos'), _deps(_proposing(db, 'Copec', 'Jumbo'), sent))
    wa.process_inbox(db, _inbox(db, 'SM2', body='SI todas'), _deps(_answer(), sent))
    assert len(db.store['variable_expenses']) == 2

    sent2 = Sent()
    wa.process_inbox(db, _inbox(db, 'SM3', body='otras dos'), _deps(_proposing(db, 'Lider', 'Unimarc'), sent2))
    wa.process_inbox(db, _inbox(db, 'SM4', body='NO todas'), _deps(_answer(), sent2))
    assert len(db.store['variable_expenses']) == 2  # unchanged


def test_unknown_proposal_number(db):
    sent = Sent()
    wa.process_inbox(db, _inbox(db, 'SM1', body='dos'), _deps(_proposing(db, 'Copec', 'Jumbo'), sent))
    wa.process_inbox(db, _inbox(db, 'SM2', body='SI 7'), _deps(_answer(), sent))
    assert 'No encuentro la propuesta 7' in sent.bodies[-1] and 'variable_expenses' not in db.store


def test_new_proposals_replace_the_old_ones_so_si_never_confirms_something_stale(db):
    sent = Sent()
    wa.process_inbox(db, _inbox(db, 'SM1', body='boleta'), _deps(_proposing(db, 'Copec'), sent))
    old_id = next(iter(db.store['pending_actions']))
    wa.process_inbox(db, _inbox(db, 'SM2', body='mejor es otra'), _deps(_proposing(db, 'Jumbo'), sent))
    assert db.store['pending_actions'][old_id]['status'] == 'cancelled'

    wa.process_inbox(db, _inbox(db, 'SM3', body='SI'), _deps(_answer(), sent))
    expense, = db.store['variable_expenses'].values()
    assert 'Jumbo' in expense['description']


def test_an_expired_proposal_is_never_confirmed(db):
    sent = Sent()
    wa.process_inbox(db, _inbox(db, 'SM1', body='boleta'), _deps(_proposing(db, 'Copec'), sent))
    for action in db.store['pending_actions'].values():
        action['expires_at'] = datetime.utcnow() - timedelta(minutes=1)
    wa.process_inbox(db, _inbox(db, 'SM2', body='SI'), _deps(_answer(), sent))
    # an expired proposal is no longer live: "SI" goes to the agent instead of confirming anything
    assert 'variable_expenses' not in db.store


def test_a_photo_with_si_is_a_new_request_not_a_confirmation(db):
    runs = []
    wa.process_inbox(db, _inbox(db, 'SM1', body='boleta'), _deps(_proposing(db, 'Copec')))
    deps = _deps(lambda m, u: runs.append(m) or {'response': 'ok', 'pending_actions': [], 'choices': []})
    wa.process_inbox(db, _inbox(db, 'SM2', body='SI', media=[('https://api.twilio.com/m/1', 'image/jpeg')]), deps)
    assert len(runs) == 1 and 'variable_expenses' not in db.store


def test_a_failed_confirmation_can_be_retried_with_si(db, monkeypatch):
    sent = Sent()
    wa.process_inbox(db, _inbox(db, 'SM1', body='boleta'), _deps(_proposing(db, 'Copec'), sent))
    real = expense_proposals.expenses.create_variable
    state = {'n': 0}

    def flaky(*args, **kwargs):
        state['n'] += 1
        if state['n'] == 1:
            raise RuntimeError('firestore down')
        return real(*args, **kwargs)

    monkeypatch.setattr(expense_proposals.expenses, 'create_variable', flaky)
    wa.process_inbox(db, _inbox(db, 'SM2', body='SI'), _deps(_answer(), sent))
    assert 'No se pudo guardar' in sent.bodies[-1] and 'variable_expenses' not in db.store
    wa.process_inbox(db, _inbox(db, 'SM3', body='SI'), _deps(_answer(), sent))
    assert len(db.store['variable_expenses']) == 1


# ============ integration: the real run_chat behind a fake Claude ============

class ProposingModel:
    def __init__(self):
        self.calls = []

    def create(self, **params):
        self.calls.append(params)
        usage = SimpleNamespace(input_tokens=1, output_tokens=1)
        if len(self.calls) == 1:
            block = SimpleNamespace(type='tool_use', id='t1', name='propose_expense', input={
                'supplier': 'Copec', 'date': '2026-10-10', 'total': 25000, 'category': 'otros', 'folio': '555'})
            return SimpleNamespace(content=[block], stop_reason='tool_use', usage=usage, model='m')
        text = SimpleNamespace(type='text', text='Te dejé la propuesta para que la confirmes.')
        return SimpleNamespace(content=[text], stop_reason='end_turn', usage=usage, model='m')


def test_end_to_end_through_the_real_assistant_core(db, monkeypatch):
    app = Flask(__name__)
    model = ProposingModel()
    monkeypatch.setattr(routes, 'get_db', lambda: db)
    monkeypatch.setattr(ai_chat_routes, 'get_db', lambda: db)
    monkeypatch.setattr(ai_chat_routes, 'anthropic_client', SimpleNamespace(messages=model))
    monkeypatch.setattr(ai_chat_routes, 'AI_CHAT_SERVER_FALLBACK', False)
    sent = Sent()
    monkeypatch.setattr(routes, '_send', sent)

    wa.store_inbound(db, {'MessageSid': 'SM900', 'From': f'whatsapp:{ADMIN}', 'Body': 'registra la boleta de Copec por 25 mil', 'NumMedia': '0'})
    assert routes.process_inbox_message(app, 'SM900') == 'answered'
    assert 'variable_expenses' not in db.store                       # the agent only proposed
    assert '¿La guardo?' in '\n'.join(b for _, b in sent) and 'Copec' in '\n'.join(b for _, b in sent)

    wa.store_inbound(db, {'MessageSid': 'SM901', 'From': f'whatsapp:{ADMIN}', 'Body': 'SI', 'NumMedia': '0'})
    assert routes.process_inbox_message(app, 'SM901') == 'command'
    expense, = db.store['variable_expenses'].values()
    assert expense['amount'] == 25000.0 and expense['folio'] == '555' and expense['source'] == 'ai_agent'
    assert len(model.calls) == 2  # the SI never reached the model


# ============ block A: speed and brevity ============

@pytest.mark.parametrize('text', ['hola', 'Hola!', 'HOLA 👋', 'wena', 'buenas tardes', 'Hola Pablito', 'holi', '  buenos días  '])
def test_greetings_get_an_instant_answer(text):
    assert wa.quick_reply(text) == wa.GREETING and 'Pablito' in wa.GREETING


@pytest.mark.parametrize('text', ['ayuda', 'Menú', '¿qué puedes hacer?'])
def test_help_gets_an_instant_answer(text):
    assert wa.quick_reply(text) == wa.HELP


@pytest.mark.parametrize('text', ['hola, registra una boleta', 'SI', '', 'cuántos eventos tengo', 'hola pablito cómo va el inventario'])
def test_everything_else_goes_to_the_agent(text):
    assert wa.quick_reply(text) is None


def test_webhook_answers_a_greeting_by_itself_without_waking_the_worker(hook, db):
    res = hook(_form(body='hola'))
    assert res.status_code == 200 and res.mimetype == 'text/xml' and 'Soy Pablito' in res.get_data(as_text=True)
    assert 'whatsapp_inbox' not in db.store  # nothing queued: no cold start, no model call


def test_a_greeting_with_a_photo_is_not_a_greeting(hook, db):
    hook(_form(body='hola', sid='SM300', NumMedia='1', MediaUrl0='https://api.twilio.com/m/1', MediaContentType0='image/jpeg'))
    assert 'SM300' in db.store['whatsapp_inbox']


def test_greeting_xml_is_escaped(hook, monkeypatch):
    monkeypatch.setattr(wa, 'GREETING', 'Hola <b>&</b>')
    assert 'Hola &lt;b&gt;&amp;&lt;/b&gt;' in hook(_form(body='hola')).get_data(as_text=True)


def test_webhook_asks_for_the_typing_indicator_for_real_messages_only(hook, monkeypatch):
    asked = []
    monkeypatch.setattr(wa, 'send_typing', lambda sid: asked.append(sid) or True)
    hook(_form(body='hola', sid='SM400'))                       # greeting: instant, no indicator needed
    hook(_form(body='cuánto gasté este mes', sid='SM401'))
    assert asked == ['SM401']


def test_typing_indicator_never_breaks_the_message(monkeypatch):
    import requests
    monkeypatch.setattr(requests, 'post', lambda *a, **k: (_ for _ in ()).throw(requests.Timeout()))
    assert wa.send_typing('SM1') is False
    monkeypatch.setenv('AI_WHATSAPP_TYPING', 'false')
    assert wa.send_typing('SM1') is False


def test_typing_indicator_request_shape(monkeypatch):
    import requests
    captured = {}
    monkeypatch.setattr(requests, 'post', lambda url, **kw: captured.update(url=url, **kw) or SimpleNamespace(ok=True, status_code=200))
    assert wa.send_typing('SM77') is True
    assert captured['url'].endswith('/Indicators/Typing.json') and captured['data'] == {'messageId': 'SM77', 'channel': 'whatsapp'}


def test_the_worker_asks_for_typing_again_when_it_starts(db):
    asked = []
    deps = wa.Deps(send=Sent(), run_chat=_answer(), download_media=lambda u: b'', now=lambda: NOW, typing=asked.append)
    wa.process_inbox(db, _inbox(db, 'SM500'), deps)
    assert asked == ['SM500']


def test_stage_timings_are_stored_for_diagnosis(db):
    wa.process_inbox(db, _inbox(db, 'SM600'), _deps(_answer()))
    timings = db.store['whatsapp_inbox']['SM600']['timings']
    assert {'queue_ms', 'media_ms', 'agent_ms', 'send_ms', 'total_ms'} <= set(timings) and timings['total_ms'] >= 0


def test_a_proposal_message_is_short_and_keeps_only_the_warnings_that_matter(db):
    action = pas.serialize(expense_proposals.propose_expense(db, {'supplier': 'Copec', 'date': '2026-10-10', 'total': 25000,
                                                                  'category': 'otros'}, wa.user_for(ADMIN)))
    action['warnings'] = ['Sin folio: la detección de duplicados es menos confiable.', 'Factura: el IVA (19 %) es crédito fiscal.',
                          'Posible duplicado: ya hay una propuesta confirmada con el mismo proveedor.',
                          'El total ($25.000) no cuadra con la suma de las líneas ($23.000). Revisa la boleta.']
    text = wa.proposals_message([action])
    assert text.count('⚠️') == 2 and 'Posible duplicado' in text and 'no cuadra' in text
    assert 'Sin folio' not in text and 'IVA' not in text and text.endswith('¿La guardo? *SI* / *NO*')
    assert len(text.split('\n')) <= 6


def test_long_proposals_are_cut_to_four_lines(db):
    action = {'type': 'inventory_receipt', 'summary': 'Compra: …', 'warnings': [], 'context': {},
              'payload': {'lines': [{'classification': 'new', 'name': f'Insumo {i}', 'quantity': 1, 'unit': 'kg',
                                     'amount': 1000, 'description': 'x'} for i in range(7)]}}
    text = wa.describe_action(action)
    assert text.count('• Insumo') == 4 and '… y 3 más' in text


def test_the_agents_chatter_next_to_a_proposal_is_trimmed(db):
    wordy = 'Te dejé la propuesta para que la confirmes. ' + 'Esto es mucho texto que el sistema ya muestra. ' * 10 + '\n\nOtro párrafo.'
    sent = Sent()
    run = lambda m, u: {'response': wordy, 'choices': [], 'pending_actions': [pas.serialize(_proposal(db))]}  # noqa: E731
    wa.process_inbox(db, _inbox(db), _deps(run, sent))
    assert 'Otro párrafo' not in sent.bodies[0] and len(sent.bodies[0]) < 500


def test_confirmation_messages_are_one_line():
    for kind, result in [('expense', {}), ('booking', {}), ('event_consumption', {'total_cost': 8000}),
                         ('event_supplies', {'estimated_total_cost': 5000}), ('inventory_receipt', {'inventory_lines': 2, 'expense_lines': 1}),
                         ('stock_adjustment', {})]:
        text = wa.result_message({'type': kind, 'payload': {'supplier': 'Copec', 'total': 25000}, 'result': result})
        assert text.startswith('✅') and '\n' not in text and len(text) < 100


def test_the_whatsapp_style_rules_reach_the_model_only_on_that_channel(db, monkeypatch):
    from flask import Flask
    seen = []

    class Model:
        def create(self, **params):
            seen.append(params['system'][0]['text'])
            return SimpleNamespace(content=[SimpleNamespace(type='text', text='ok')], stop_reason='end_turn',
                                   usage=SimpleNamespace(input_tokens=1, output_tokens=1), model='m')

    monkeypatch.setattr(ai_chat_routes, 'anthropic_client', SimpleNamespace(messages=Model()))
    monkeypatch.setattr(ai_chat_routes, 'AI_CHAT_SERVER_FALLBACK', False)
    with Flask(__name__).test_request_context():
        ai_chat_routes.run_chat([{'role': 'user', 'content': 'hola'}], wa.user_for(ADMIN))
    with Flask(__name__).test_request_context():
        ai_chat_routes.run_chat([{'role': 'user', 'content': 'hola'}], wa.user_for(ADMIN), channel='whatsapp')
    assert 'CANAL: WHATSAPP' not in seen[0] and 'CANAL: WHATSAPP' in seen[1] and 'Máximo 3 o 4 líneas' in seen[1]
    assert seen[0].startswith('\nEres Pablito') or 'Eres Pablito' in seen[0]


def test_the_system_prompt_and_tools_are_cached():
    seen = {}

    class Model:
        def create(self, **params):
            seen.update(params)
            return SimpleNamespace(content=[], stop_reason='end_turn', usage=SimpleNamespace(input_tokens=1, output_tokens=1), model='m')

    ai_chat_routes.anthropic_client = SimpleNamespace(messages=Model())
    ai_chat_routes.AI_CHAT_SERVER_FALLBACK = False
    try:
        ai_chat_routes.create_ai_message('system text', [{'role': 'user', 'content': 'x'}])
    finally:
        ai_chat_routes.anthropic_client = None
        ai_chat_routes.AI_CHAT_SERVER_FALLBACK = True
    assert seen['system'] == [{'type': 'text', 'text': 'system text', 'cache_control': {'type': 'ephemeral'}}]
    assert seen['tools'][-1]['cache_control'] == {'type': 'ephemeral'} and 'cache_control' not in seen['tools'][0]
    assert 'cache_control' not in ai_chat_routes.TOOLS[-1]  # the module-level list is never mutated


# ============ the history must show what really happened (otherwise the model doubts itself) ============

def test_history_keeps_the_proposal_the_person_saw_and_the_si_exchange(db):
    seen = []

    def run(messages, user):
        seen.append(messages)
        if len(seen) == 1:
            return {'response': 'Listo, revísala.', 'choices': [], 'pending_actions': [pas.serialize(_proposal(db, 'Copec'))]}
        return {'response': 'ok', 'choices': [], 'pending_actions': []}

    deps = _deps(run)
    wa.process_inbox(db, _inbox(db, 'SM1', body='registra la boleta'), deps)
    wa.process_inbox(db, _inbox(db, 'SM2', body='SI'), deps)           # confirmed by the code, not by the agent
    wa.process_inbox(db, _inbox(db, 'SM3', body='y cuánto llevo gastado'), deps)

    texts = [m['content'] if isinstance(m['content'], str) else m['content'][0]['text'] for m in seen[1]]
    assert texts[0] == 'registra la boleta'
    assert 'Copec' in texts[1] and '¿La guardo?' in texts[1]            # the agent can answer "cámbialo" with the details
    assert texts[2] == 'SI' and texts[3].startswith('✅ Guardado')       # and knows it was saved
    assert texts[4] == 'y cuánto llevo gastado'


def test_the_prompt_tells_the_agent_not_to_doubt_earlier_answers():
    prompt = ai_chat_routes.WHATSAPP_STYLE
    assert 'no te "corrijas"' in prompt and 'SÍ ocurrieron' in prompt and 'nada de resúmenes' in prompt


# ============ B0: the pipeline others build on ============

def test_the_webhook_remembers_when_an_allowed_number_last_wrote_even_for_instant_answers(hook, db):
    hook(_form(body='hola', sid='SM700'))                          # instant greeting, nothing queued
    assert 'whatsapp_inbox' not in db.store
    assert db.store['whatsapp_contacts'][ADMIN]['last_user_message_at'] is not None
    first = db.store['whatsapp_contacts'][ADMIN]['last_user_message_at']

    hook(_form(body='registra un gasto', sid='SM701'))
    assert db.store['whatsapp_contacts'][ADMIN]['last_user_message_at'] >= first


def test_strangers_and_unsigned_requests_leave_no_contact_record(hook, db):
    hook(_form(sender=STRANGER))
    hook(_form(), signed=False)
    assert 'whatsapp_contacts' not in db.store


def test_touch_contact_merges_and_never_raises():
    db = FakeFirestore()
    db.store['whatsapp_contacts'] = {ADMIN: {'alert_prefs': {'paused': True}}}
    wa.touch_contact(db, ADMIN, NOW)
    assert db.store['whatsapp_contacts'][ADMIN] == {'alert_prefs': {'paused': True}, 'last_user_message_at': NOW, 'updated_at': NOW}

    class Broken:
        def collection(self, name):
            raise RuntimeError('firestore down')

    wa.touch_contact(Broken(), ADMIN, NOW)  # must not raise


def test_forwarded_and_button_payload_are_stored_for_later_features(db):
    wa.store_inbound(db, {'MessageSid': 'SM710', 'From': f'whatsapp:{ADMIN}', 'Body': 'Ver', 'NumMedia': '0',
                          'Forwarded': 'true', 'ButtonPayload': 'digest_ver'})
    stored = db.store['whatsapp_inbox']['SM710']
    assert stored['forwarded'] is True and stored['button_payload'] == 'digest_ver'
    wa.store_inbound(db, {'MessageSid': 'SM711', 'From': f'whatsapp:{ADMIN}', 'Body': 'hola', 'NumMedia': '0'})
    assert db.store['whatsapp_inbox']['SM711']['forwarded'] is False and db.store['whatsapp_inbox']['SM711']['button_payload'] is None


def test_saving_the_conversation_keeps_fields_other_features_added(db):
    db.store['whatsapp_conversations'] = {ADMIN: {'history': [], 'pending': [], 'choices': [], 'last_inbound_at': NOW, 'summary': 'kept'}}
    wa.process_inbox(db, _inbox(db, 'SM720', body='hola de nuevo'), _deps(_answer()))
    assert db.store['whatsapp_conversations'][ADMIN]['summary'] == 'kept'
    assert db.store['whatsapp_conversations'][ADMIN]['history'][0]['content'] == 'hola de nuevo'


def _stored(db, sid, body='', media=(), forwarded=False, button=None):
    wa.store_inbound(db, {'MessageSid': sid, 'From': f'whatsapp:{ADMIN}', 'Body': body, 'NumMedia': str(len(media)),
                          'Forwarded': 'true' if forwarded else 'false', **({'ButtonPayload': button} if button else {}),
                          **{k: v for i, m in enumerate(media) for k, v in ((f'MediaUrl{i}', m[0]), (f'MediaContentType{i}', m[1]))}})
    return db.store['whatsapp_inbox'][sid]


def test_gather_joins_a_whole_burst_into_one_inbound(db):
    jpeg = ('https://api.twilio.com/m', 'image/jpeg')
    burst = [_stored(db, 'A', 'registra estas', [jpeg]), _stored(db, 'B', '', [jpeg]), _stored(db, 'C', 'son de ayer', [jpeg, jpeg], forwarded=True,
                                                                                               button='x')]
    deps = _deps(_answer())
    inbound = wa._gather(db, deps, burst)
    assert inbound.phone == ADMIN and inbound.sids == ['A', 'B', 'C']
    assert inbound.text == 'registra estas\nson de ayer'
    assert len(inbound.image_blocks) == wa.MAX_IMAGES and inbound.unsupported is True   # the 4th photo is left out and flagged
    assert inbound.forwarded is True and inbound.button_payload == 'x'


def test_gather_flags_unsupported_media_without_downloading_it(db):
    downloaded = []
    deps = wa.Deps(send=Sent(), run_chat=_answer(), download_media=lambda u: downloaded.append(u) or b'', now=lambda: NOW)
    inbound = wa._gather(db, deps, [_stored(db, 'D', '', [('https://api.twilio.com/m', 'application/pdf')])])
    assert inbound.unsupported and not inbound.image_blocks and downloaded == []


def test_a_new_command_handler_is_one_line_and_skips_the_model(db, monkeypatch):
    seen = []
    monkeypatch.setattr(wa, 'COMMAND_HANDLERS', list(wa.COMMAND_HANDLERS))
    wa.COMMAND_HANDLERS.insert(0, (lambda ctx: ctx.inbound.text.lower() == 'ping' or None,
                                   lambda ctx, matched: (seen.append(ctx.phone), 'pong')[1]))
    sent, ran = Sent(), []
    deps = _deps(lambda m, u: ran.append(1) or {'response': 'x', 'pending_actions': [], 'choices': []}, sent)
    assert wa.process_inbox(db, _inbox(db, 'SM730', body='ping'), deps) == 'command'
    assert seen == [ADMIN] and ran == [] and db.store['whatsapp_conversations'][ADMIN]['history'][-1] == {'role': 'assistant', 'content': 'pong'}
    assert wa.process_inbox(db, _inbox(db, 'SM731', body='otra cosa'), deps) == 'answered' and ran == [1]


def test_a_handler_that_declines_lets_the_next_one_and_the_agent_run(db, monkeypatch):
    monkeypatch.setattr(wa, 'COMMAND_HANDLERS', [(lambda ctx: True, lambda ctx, matched: None)] + list(wa.COMMAND_HANDLERS))
    ran = []
    deps = _deps(lambda m, u: ran.append(1) or {'response': 'ok', 'pending_actions': [], 'choices': []})
    assert wa.process_inbox(db, _inbox(db, 'SM740', body='hola'), deps) == 'answered' and ran == [1]
