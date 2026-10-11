"""Tests for the daily digest: one message a day at most, only when something is new, never on a failed send"""
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta

import pytest
from flask import Flask
from twilio.request_validator import RequestValidator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402,F401  (imported at collection time: it loads backend/.env, which must not happen mid-test)
from routes import whatsapp_routes as routes  # noqa: E402
from services import alerts_service as alerts  # noqa: E402
from services import pending_actions_service as pas  # noqa: E402
from services import proactive_service as ps  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402

ADMIN, PARTNER = '+56911111111', '+56922222222'
NOW = datetime(2026, 10, 12, 13, 0, 0)      # 10:00 in Santiago
DAY_DOC = f'{ADMIN}_20261012'


class FakeDeps:
    def __init__(self, template_sid='HX123', fail=False):
        self.template_sid, self.fail, self.texts, self.templates = template_sid, fail, [], []

    def send_text(self, phone, body):
        if self.fail:
            raise RuntimeError('twilio down')
        self.texts.append((phone, body))
        return 'SMtext'

    def send_template(self, phone, content_sid, variables):
        if self.fail:
            raise RuntimeError('twilio down')
        self.templates.append((phone, content_sid, variables))
        return 'SMtemplate'

    @property
    def sent(self):
        return len(self.texts) + len(self.templates)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_ENABLED', 'true')
    monkeypatch.setenv('ADMIN_WHATSAPP_NUMBER', ADMIN)
    monkeypatch.setenv('PARTNER_WHATSAPP_NUMBER', PARTNER)
    monkeypatch.setenv('AI_WHATSAPP_PROACTIVE_TO', ADMIN)
    monkeypatch.delenv('AI_WHATSAPP_PROACTIVE_DRY_RUN', raising=False)
    monkeypatch.delenv('AI_WHATSAPP_ALLOWED', raising=False)
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))


@pytest.fixture
def db():
    return FakeFirestore()


def _low_stock(db, name='harina', stock=1):
    db.collection('inventory').document(name).set(
        {'name': name.capitalize(), 'current_stock': stock, 'min_stock': 5, 'unit': 'kg', 'needs_restock': True})


def _pending_booking(db, booking_id='b1', event_date='2026-10-30'):
    db.collection('bookings').document(booking_id).set(
        {'client_name': 'Ana Pérez', 'status': 'pending', 'event_date': event_date, 'created_at': NOW - timedelta(hours=30)})


def _spoke_recently(db, hours=2, phone=ADMIN):
    db.collection('whatsapp_contacts').document(phone).set({'last_user_message_at': NOW - timedelta(hours=hours)}, merge=True)


def _run(db, deps, now=NOW, dry_run=False):
    return ps.run_daily(db, deps, now=now, dry_run=dry_run)


# ============ switched off by default ============

def test_nothing_happens_until_recipients_are_enabled(db, monkeypatch):
    monkeypatch.delenv('AI_WHATSAPP_PROACTIVE_TO')
    _low_stock(db)
    deps = FakeDeps()
    assert _run(db, deps) == {'skipped': 'no_recipients'} and deps.sent == 0
    assert 'assistant_alerts' not in db.store and 'whatsapp_proactive' not in db.store


def test_dry_run_is_the_default(db, monkeypatch):
    monkeypatch.delenv('AI_WHATSAPP_PROACTIVE_DRY_RUN', raising=False)
    assert ps.dry_run_default() is True
    monkeypatch.setenv('AI_WHATSAPP_PROACTIVE_DRY_RUN', 'false')
    assert ps.dry_run_default() is False


def test_only_the_admin_number_ever_receives_the_digest(db, monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_PROACTIVE_TO', f'{PARTNER}, {ADMIN}')
    assert ps.recipients() == [ADMIN]
    monkeypatch.setenv('AI_WHATSAPP_PROACTIVE_TO', PARTNER)
    assert ps.recipients() == []


# ============ the happy path ============

def test_it_sends_free_text_inside_the_24_hour_window_and_records_everything(db):
    _low_stock(db)
    _pending_booking(db)
    _spoke_recently(db, hours=2)
    deps = FakeDeps()
    result = _run(db, deps)
    assert result['results'][ADMIN]['status'] == 'sent' and result['results'][ADMIN]['mode'] == 'text'
    assert deps.templates == [] and len(deps.texts) == 1
    phone, body = deps.texts[0]
    assert phone == ADMIN and len(body.split('\n')) <= 4 and 'ver' in body.lower() and 'silenciar' in body.lower()

    day = db.store['whatsapp_proactive'][DAY_DOC]
    assert day['status'] == 'sent' and day['sid'] == 'SMtext' and day['items'] and '1.' in day['detail']
    for alert in db.store['assistant_alerts'].values():
        assert alert['notified'][ADMIN] == NOW and alert['last_notified_at'] == NOW
    digest = db.store['whatsapp_contacts'][ADMIN]['last_digest']
    assert digest['detail'] == day['detail'] and digest['items'] == day['items']
    assert db.store['whatsapp_contacts'][ADMIN]['last_user_message_at'] == NOW - timedelta(hours=2)   # merge kept it


def test_it_uses_the_template_outside_the_window_with_clean_variables(db):
    _low_stock(db)
    _pending_booking(db)
    _spoke_recently(db, hours=30)
    deps = FakeDeps()
    assert _run(db, deps)['results'][ADMIN]['mode'] == 'template'
    assert deps.texts == []
    phone, content_sid, variables = deps.templates[0]
    assert content_sid == 'HX123' and variables['1'] == '2'
    assert '\n' not in variables['2'] and len(variables['2']) <= 100 and 'harina' in variables['2'].lower()


def test_a_number_that_never_wrote_gets_the_template(db):
    _low_stock(db)
    deps = FakeDeps()
    assert _run(db, deps)['results'][ADMIN]['mode'] == 'template'


def test_the_window_edge_is_23h50(db):
    _low_stock(db)
    _spoke_recently(db, hours=23.9)
    assert ps.in_window(db, ADMIN, NOW) is False
    _spoke_recently(db, hours=23.5)
    assert ps.in_window(db, ADMIN, NOW) is True


def test_without_an_approved_template_outside_the_window_nothing_is_sent_or_marked(db):
    _low_stock(db)
    deps = FakeDeps(template_sid='')
    assert _run(db, deps)['results'][ADMIN]['status'] == 'no_template'
    assert deps.sent == 0 and 'whatsapp_proactive' not in db.store
    assert db.store['assistant_alerts']['low_stock:harina']['notified'] == {}


def test_the_summary_is_one_short_line_even_with_many_alerts(db):
    for i in range(8):
        _low_stock(db, name=f'ingrediente_con_nombre_largo_{i}')
    for i in range(5):
        _pending_booking(db, f'b{i}', event_date='2026-10-14')
    active = alerts.evaluate(db, NOW)
    summary = ps.summarize(active)
    assert '\n' not in summary and 0 < len(summary) <= 100


def test_the_free_text_always_fits_four_lines(db):
    for i in range(6):
        _low_stock(db, name=f'item{i}')
    _pending_booking(db)
    text = ps.build_free_text(alerts.evaluate(db, NOW))
    assert len(text.split('\n')) <= 4


# ============ anti-spam ============

def test_running_twice_the_same_day_sends_one_message(db):
    _low_stock(db)
    deps = FakeDeps()
    _run(db, deps)
    second = _run(db, deps)
    assert deps.sent == 1 and second['results'][ADMIN]['status'] == 'nothing_new'


def test_the_daily_quota_holds_even_when_something_new_appears_in_between(db):
    _low_stock(db)
    deps = FakeDeps()
    _run(db, deps)
    _pending_booking(db)                                            # a new alert after the first run
    again = _run(db, deps, now=NOW + timedelta(minutes=30))
    assert again['results'][ADMIN]['status'] == 'already_sent' and deps.sent == 1


def test_an_alert_that_stays_the_same_is_never_announced_again(db):
    _low_stock(db)
    deps = FakeDeps()
    for day in range(5):
        _run(db, deps, now=NOW + timedelta(days=day))
    assert deps.sent == 1


def test_nothing_new_means_nothing_sent(db):
    deps = FakeDeps()
    assert _run(db, deps)['results'][ADMIN]['status'] == 'nothing_new'
    assert deps.sent == 0 and 'whatsapp_proactive' not in db.store


def test_a_resolved_and_returning_alert_is_announced_again_after_the_cooldown(db):
    _low_stock(db, stock=1)
    deps = FakeDeps()
    _run(db, deps)
    _low_stock(db, stock=50)
    db.store['inventory']['harina']['needs_restock'] = False
    _run(db, deps, now=NOW + timedelta(days=1))                     # resolved
    _low_stock(db, stock=1)
    _run(db, deps, now=NOW + timedelta(days=2))                     # back, but only 48 h after the last notice
    assert deps.sent == 1
    _run(db, deps, now=NOW + timedelta(days=4))                     # 96 h
    assert deps.sent == 2


def test_muted_alerts_are_not_sent(db):
    _low_stock(db)
    db.collection('whatsapp_contacts').document(ADMIN).set({'alert_prefs': {'muted_types': ['low_stock']}}, merge=True)
    deps = FakeDeps()
    assert _run(db, deps)['results'][ADMIN]['status'] == 'nothing_new' and deps.sent == 0


def test_the_digest_only_carries_what_is_new(db):
    _low_stock(db)
    deps = FakeDeps()
    _run(db, deps)
    _pending_booking(db)
    _run(db, deps, now=NOW + timedelta(days=1))
    assert deps.sent == 2
    assert deps.templates[1][2]['1'] == '1' and 'harina' not in deps.templates[1][2]['2'].lower()


def test_no_message_at_night(db):
    _low_stock(db)
    deps = FakeDeps()
    night = datetime(2026, 10, 13, 2, 0)                            # 23:00 in Santiago
    early = datetime(2026, 10, 12, 10, 0)                           # 07:00 in Santiago
    assert _run(db, deps, now=night) == {'skipped': 'quiet_hours'}
    assert _run(db, deps, now=early) == {'skipped': 'quiet_hours'}
    assert deps.sent == 0 and 'whatsapp_proactive' not in db.store


# ============ dry run and failures ============

def test_dry_run_neither_sends_nor_marks_anything_as_notified(db):
    _low_stock(db)
    deps = FakeDeps()
    result = _run(db, deps, dry_run=True)
    assert result['results'][ADMIN]['status'] == 'dry_run' and deps.sent == 0
    assert db.store['whatsapp_proactive'][DAY_DOC]['status'] == 'dry_run'
    assert db.store['assistant_alerts']['low_stock:harina']['notified'] == {}
    assert 'last_digest' not in db.store.get('whatsapp_contacts', {}).get(ADMIN, {})


def test_a_real_run_can_follow_a_dry_run_the_same_day(db):
    _low_stock(db)
    deps = FakeDeps()
    _run(db, deps, dry_run=True)
    assert _run(db, deps)['results'][ADMIN]['status'] == 'sent' and deps.sent == 1
    assert db.store['whatsapp_proactive'][DAY_DOC]['status'] == 'sent'


def test_dry_run_follows_the_environment_default(db):
    _low_stock(db)
    deps = FakeDeps()
    assert ps.run_daily(db, deps, now=NOW)['results'][ADMIN]['status'] == 'dry_run' and deps.sent == 0


def test_a_failed_send_marks_nothing_as_notified(db):
    _low_stock(db)
    result = _run(db, FakeDeps(fail=True))
    assert result['results'][ADMIN]['status'] == 'failed'
    assert db.store['assistant_alerts']['low_stock:harina']['notified'] == {}
    assert db.store['whatsapp_proactive'][DAY_DOC]['status'] == 'failed'
    assert 'last_digest' not in db.store.get('whatsapp_contacts', {}).get(ADMIN, {})


def test_after_a_failure_the_alert_is_still_announceable_the_next_day(db):
    _low_stock(db)
    _run(db, FakeDeps(fail=True))
    deps = FakeDeps()
    assert _run(db, deps, now=NOW + timedelta(days=1))['results'][ADMIN]['status'] == 'sent' and deps.sent == 1


def test_the_scheduled_entry_point_is_off_with_the_channel(db, monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_ENABLED', 'false')
    assert ps.run_scheduled(db, now=NOW) == {'skipped': 'channel off'}


# ============ "Ver" ============

def _digest(db, hours_ago=1, phone=ADMIN):
    db.collection('whatsapp_contacts').document(phone).set(
        {'last_digest': {'at': NOW - timedelta(hours=hours_ago), 'detail': '📋 *Avisos de hoy*\n1. 📦 Stock bajo: Harina',
                         'items': ['low_stock:harina'], 'labels': ['Harina']}}, merge=True)


def test_ver_answers_the_saved_detail_for_the_button_and_for_the_word(db):
    _digest(db)
    assert 'Stock bajo: Harina' in ps.view_reply(db, ADMIN, 'digest_ver', 'Ver', now=NOW)
    assert 'Stock bajo: Harina' in ps.view_reply(db, ADMIN, None, ' Ver! ', now=NOW)


def test_ver_with_no_recent_digest(db):
    assert ps.view_reply(db, ADMIN, None, 'ver', now=NOW) is None                 # plain text: the agent handles it
    assert 'Ya no tengo' in ps.view_reply(db, ADMIN, 'digest_ver', 'Ver', now=NOW)  # a tapped button always gets an answer
    _digest(db, hours_ago=49)
    assert ps.view_reply(db, ADMIN, None, 'ver', now=NOW) is None


def test_other_texts_are_not_ver(db):
    _digest(db)
    assert ps.view_reply(db, ADMIN, None, 'ver las ventas', now=NOW) is None
    assert ps.view_reply(db, ADMIN, None, '', now=NOW) is None


TOKEN = 'twilio-test-token'
URL = 'https://main-test.example.run.app/api/whatsapp/webhook'


@pytest.fixture
def hook(db, monkeypatch):
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', TOKEN)
    monkeypatch.setattr(routes, 'get_db', lambda: db)
    app = Flask(__name__)
    app.register_blueprint(routes.whatsapp_bp)
    client = app.test_client()

    def post(form):
        headers = {'X-Twilio-Signature': RequestValidator(TOKEN).compute_signature(URL, form)}
        return client.post('/api/whatsapp/webhook', data=form, headers=headers, base_url='https://main-test.example.run.app')
    return post


def test_the_webhook_answers_ver_by_twiml_without_the_model_and_opens_the_window(db, hook, monkeypatch):
    now = datetime.utcnow()
    db.collection('whatsapp_contacts').document(ADMIN).set(
        {'last_digest': {'at': now - timedelta(hours=1), 'detail': 'DETALLE & más', 'items': ['k'], 'labels': ['K']}})
    form = {'From': f'whatsapp:{ADMIN}', 'Body': 'Ver', 'ButtonPayload': 'digest_ver', 'MessageSid': 'SM900', 'NumMedia': '0'}
    response = hook(form)
    assert response.status_code == 200 and b'DETALLE &amp; m' in response.data
    assert 'whatsapp_inbox' not in db.store                                          # no queue, no model
    assert db.store['whatsapp_contacts'][ADMIN]['last_user_message_at'] >= now       # the reply opened the 24 h window


def test_the_webhook_lets_a_plain_ver_without_digest_reach_the_agent(db, hook):
    form = {'From': f'whatsapp:{ADMIN}', 'Body': 'ver', 'MessageSid': 'SM901', 'NumMedia': '0'}
    hook(form)
    assert db.store['whatsapp_inbox']['SM901']['body'] == 'ver'


# ============ preview endpoint ============

def test_preview_shows_the_digest_without_touching_any_state(db):
    _low_stock(db)
    _pending_booking(db)
    view = ps.preview(db, now=NOW)
    assert view['new_count'] == 2 and view['would_send'] and view['mode'] == 'template' and view['dry_run'] is True
    assert '\n' not in view['template_variables']['2'] and view['detail'].startswith('📋')
    assert 'assistant_alerts' not in db.store and 'whatsapp_proactive' not in db.store


def test_preview_endpoint_is_admin_only_and_read_only(db, monkeypatch):
    from routes import ai_chat_routes
    monkeypatch.setattr(ai_chat_routes, 'get_db', lambda: db)
    app = Flask(__name__)
    app.register_blueprint(ai_chat_routes.ai_chat_bp)
    client = app.test_client()
    assert client.get('/api/ai-chat/proactive/preview').status_code in (401, 403)     # no admin session
    assert 'assistant_alerts' not in db.store


# ============ the template script ============

def _script():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts', 'create_whatsapp_template.py')
    spec = importlib.util.spec_from_file_location('create_whatsapp_template', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload, ok=True, status_code=200):
        self._payload, self.ok, self.status_code, self.text = payload, ok, status_code, json.dumps(payload)

    def json(self):
        return self._payload


def test_the_template_script_dry_run_prints_the_request_and_calls_nothing():
    script, lines = _script(), []

    def forbidden(*a, **k):
        raise AssertionError('no network in a dry run')

    assert script.main(['--dry-run', '--approve'], post=forbidden, get=forbidden, env={}, out=lines.append) == 0
    output = '\n'.join(lines)
    assert 'pablito_resumen_diario' in output and 'digest_ver' in output and 'UTILITY' in output and 'nothing was sent' in output


def test_the_template_payload_matches_the_design():
    payload = _script().content_payload()
    assert payload['language'] == 'es' and payload['variables'] == {
        '1': '2', '2': 'stock bajo de harina y 1 reserva por confirmar'}
    quick = payload['types']['twilio/quick-reply']
    assert '{{1}}' in quick['body'] and '{{2}}' in quick['body'] and quick['actions'] == [{'title': 'Ver', 'id': 'digest_ver'}]


def test_the_template_script_creates_and_requests_approval_with_simulated_requests_and_hides_credentials():
    script, lines, calls = _script(), [], []

    def post(url, json=None, auth=None, timeout=None):
        calls.append((url, json, auth))
        return FakeResponse({'sid': 'HXabc'} if url.endswith('/Content') else {'status': 'received'})

    env = {'TWILIO_ACCOUNT_SID': 'ACsecretsid', 'TWILIO_AUTH_TOKEN': 'secrettoken'}
    assert script.main(['--approve'], post=post, get=None, env=env, out=lines.append) == 0
    assert [c[0] for c in calls] == ['https://content.twilio.com/v1/Content',
                                     'https://content.twilio.com/v1/Content/HXabc/ApprovalRequests/whatsapp']
    assert calls[1][1] == {'name': 'pablito_resumen_diario', 'category': 'UTILITY'} and calls[0][2] == ('ACsecretsid', 'secrettoken')
    output = '\n'.join(lines)
    assert 'HXabc' in output and 'secrettoken' not in output and 'ACsecretsid' not in output


def test_the_template_script_needs_credentials_and_reports_api_errors():
    script = _script()
    with pytest.raises(SystemExit):
        script.main([], post=lambda *a, **k: None, get=None, env={}, out=lambda *_: None)
    with pytest.raises(SystemExit) as error:
        script.main([], post=lambda *a, **k: FakeResponse({'message': 'bad'}, ok=False, status_code=400), get=None,
                    env={'TWILIO_ACCOUNT_SID': 'AC', 'TWILIO_AUTH_TOKEN': 't'}, out=lambda *_: None)
    assert '400' in str(error.value)


def test_the_template_script_can_check_the_approval_status():
    script, lines = _script(), []
    get = lambda url, auth=None, timeout=None: FakeResponse({'whatsapp': {'status': 'approved'}})  # noqa: E731
    assert script.main(['--status', 'HXabc'], post=None, get=get,
                       env={'TWILIO_ACCOUNT_SID': 'AC', 'TWILIO_AUTH_TOKEN': 't'}, out=lines.append) == 0
    assert 'approved' in '\n'.join(lines)


# ============ deployment manifest ============

def test_functions_yaml_entry_matches_what_the_sdk_generates():
    import yaml
    from firebase_functions.private import serving
    generated = yaml.safe_load(serving.functions_as_yaml(serving.get_functions()))['endpoints']['whatsapp_daily_digest']
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'functions.yaml')
    with open(path, encoding='utf-8') as handle:
        declared = yaml.safe_load(handle)['endpoints']['whatsapp_daily_digest']
    for key in ('platform', 'entryPoint', 'scheduleTrigger', 'timeoutSeconds'):
        assert declared[key] == generated[key], key
    assert declared['scheduleTrigger']['schedule'] == '0 10 * * *'
    assert declared['scheduleTrigger']['timeZone'] == 'America/Santiago'
    keep_warm = yaml.safe_load(open(path, encoding='utf-8'))['endpoints']['keep_warm']
    assert set(declared) == set(keep_warm)                                           # same shape as the existing entry
