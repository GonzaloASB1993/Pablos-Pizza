"""Fixes from the Opus review of Pablito (B0-B4 + C): races, quota, speech cap, voice commands, send failures."""
import io
import os
import sys
from datetime import datetime, timedelta

import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402,F401  (imported at collection time: it loads backend/.env, which must not happen mid-test)
from routes import whatsapp_routes as routes  # noqa: E402
from services import expense_proposals  # noqa: E402
from services import pending_actions_service as pas  # noqa: E402
from services import speech_service as speech  # noqa: E402
from services import whatsapp_agent as wa  # noqa: E402
from services import whatsapp_burst as burst  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402
from tests.test_whatsapp_burst import Clock  # noqa: E402

ADMIN = '+56911111111'
NOW = datetime(2026, 10, 12, 15, 0, 0)
ASK_WRITTEN = 'No te escuché bien, ¿me lo confirmas escrito? *SI* / *NO*'


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_ENABLED', 'true')
    monkeypatch.setenv('ADMIN_WHATSAPP_NUMBER', ADMIN)
    monkeypatch.setenv('PARTNER_WHATSAPP_NUMBER', '+56922222222')
    for name in ('AI_WHATSAPP_ALLOWED', 'AI_WHATSAPP_STT_DAILY_SECONDS', 'AI_WHATSAPP_VOICE_CONFIRM', 'AI_WHATSAPP_DAILY_LIMIT',
                 'AI_WHATSAPP_BURST_SECONDS', 'AI_WHATSAPP_TEXT_BURST_SECONDS'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))
    monkeypatch.setattr('utils.audit.log_audit', lambda *a, **k: None)


@pytest.fixture
def db():
    return FakeFirestore()


def _jpeg():
    out = io.BytesIO()
    Image.new('RGB', (40, 30), 'white').save(out, 'JPEG')
    return out.getvalue()


class Sent:
    def __init__(self):
        self.items = []

    def __call__(self, phone, body):
        self.items.append(body)


class Transcriber:
    def __init__(self, *results):
        self.results, self.calls = list(results), []

    def __call__(self, data, content_type):
        self.calls.append((data, content_type))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def say(text, confidence=0.95, seconds=5.0):
    return {'text': text, 'confidence': confidence, 'seconds': seconds}


class Agent:
    def __init__(self, db=None, propose=False):
        self.db, self.propose, self.seen = db, propose, []

    def __call__(self, messages, user):
        self.seen.append(messages)
        actions = []
        if self.propose:
            action = expense_proposals.propose_expense(
                self.db, {'supplier': 'Copec', 'date': '2026-10-10', 'total': 25000, 'folio': '1', 'category': 'otros'}, user)
            actions = [pas.serialize(action)]
        return {'response': 'Listo, revísala.' if actions else 'Tienes 3 reservas.', 'pending_actions': actions, 'choices': []}


def deps_for(agent, transcriber=None, sent=None, download=None, now=NOW):
    return wa.Deps(send=sent if sent is not None else Sent(), run_chat=agent,
                   download_media=download or (lambda url, max_bytes=None: b'OPUS-BYTES'),
                   now=lambda: now, transcribe=transcriber)


def message(db, sid='SM1', body='', n=0, content_type='audio/ogg', forwarded=False, now=None):
    form = {'MessageSid': sid, 'From': f'whatsapp:{ADMIN}', 'Body': body, 'NumMedia': str(n),
            'Forwarded': 'true' if forwarded else 'false'}
    for i in range(n):
        form[f'MediaUrl{i}'] = f'https://api.twilio.com/media/{sid}-{i}'
        form[f'MediaContentType{i}'] = content_type
    wa.store_inbound(db, form, now=now)
    return sid


def propose_first(db):
    wa.process_inbox(db, message(db, 'SM0', body='boleta de copec'), deps_for(Agent(db, propose=True)))


def expense_count(db):
    return len(db.store.get('variable_expenses', {}))


def _newer_proposal_after_a_waiting_command(db, sid, body):
    """The race: the person wrote `body` about P1; a turn that ran first cancelled P1 and created P2"""
    propose_first(db)
    old = next(iter(db.store['pending_actions']))
    message(db, sid, body=body, now=datetime.utcnow() - timedelta(seconds=30))
    pas.cancel(db, old)
    newer = expense_proposals.propose_expense(db, {'supplier': 'Lider', 'date': '2026-10-10', 'total': 9000, 'folio': '9',
                                                   'category': 'otros'}, wa.user_for(ADMIN))
    db.collection('whatsapp_conversations').document(ADMIN).set(
        {'history': [], 'pending': [{'id': newer['id'], 'n': 1}], 'choices': [], 'last_inbound_at': NOW})
    return newer


# ============ 1. a SI never confirms a proposal created after it was written ============

def test_a_si_written_before_a_proposal_existed_never_confirms_it(db):
    newer = _newer_proposal_after_a_waiting_command(db, 'SM-SI', 'SI')
    sent, agent = Sent(), Agent()
    assert wa.process_inbox(db, 'SM-SI', deps_for(agent, sent=sent)) == 'command'
    assert expense_count(db) == 0 and agent.seen == []
    assert db.store['pending_actions'][newer['id']]['status'] == 'pending'
    assert sent.items == ['Te llegó una propuesta nueva, revísala y responde SI.']


def test_a_no_does_not_cancel_a_proposal_created_after_it_either(db):
    newer = _newer_proposal_after_a_waiting_command(db, 'SM-NO', 'NO')
    wa.process_inbox(db, 'SM-NO', deps_for(Agent(), sent=Sent()))
    assert db.store['pending_actions'][newer['id']]['status'] == 'pending'


def test_a_burst_uses_its_oldest_message_as_the_time_of_the_command(db):
    messages = [{'from': ADMIN, 'sid': 'A', 'created_at': datetime(2026, 10, 12, 15, 0, 5)},
                {'from': ADMIN, 'sid': 'B', 'created_at': datetime(2026, 10, 12, 15, 0, 1)}]
    assert wa._gather(db, deps_for(Agent()), messages).created_at == datetime(2026, 10, 12, 15, 0, 1)


# ============ 2. lock ============

def test_the_lock_outlives_the_worker_timeout():
    assert burst.LOCK_TTL >= 300


def test_a_live_lock_is_never_stolen_even_after_the_max_wait(db):
    clock = Clock()
    db.store['whatsapp_locks'] = {ADMIN: {'owner_sid': 'SM-ALIVE', 'until': NOW + timedelta(seconds=burst.LOCK_TTL)}}
    deps = deps_for(Agent())
    deps.now, deps.sleep = clock.now, clock.sleep
    with pytest.raises(burst.LockBusy):
        burst.acquire_lock(db, ADMIN, 'SM-WAITER', deps)
    assert db.store['whatsapp_locks'][ADMIN]['owner_sid'] == 'SM-ALIVE'


def test_a_lock_expiring_at_this_very_second_is_free(db):
    db.store['whatsapp_locks'] = {ADMIN: {'owner_sid': 'SM-OLD', 'until': NOW}}
    assert burst._try_lock(db, ADMIN, 'SM-NEW', NOW) is True


# ============ 3. quota counts every message of a burst ============

def test_a_burst_of_ten_messages_consumes_ten(db):
    for i in range(10):
        message(db, f'SM{i}', n=1, content_type='image/jpeg', now=NOW + timedelta(seconds=0.2 * i))
    clock = Clock(NOW + timedelta(seconds=2))
    deps = deps_for(Agent(), download=lambda url, max_bytes=None: _jpeg())
    deps.now, deps.sleep = clock.now, clock.sleep
    assert wa.process_inbox(db, 'SM9', deps) == 'answered'
    assert next(iter(db.store['whatsapp_quota'].values()))['count'] == 10


def test_quota_adds_the_cost_of_each_check(db):
    assert wa._within_quota(db, ADMIN, cost=3, now=NOW) and wa._within_quota(db, ADMIN, cost=2, now=NOW)
    assert next(iter(db.store['whatsapp_quota'].values()))['count'] == 5


def test_quota_refuses_once_the_limit_is_used(db, monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_DAILY_LIMIT', '4')
    assert wa._within_quota(db, ADMIN, cost=4, now=NOW)
    assert not wa._within_quota(db, ADMIN, cost=1, now=NOW)


# ============ 4. speech cap ============

def test_a_failing_transcription_still_costs_the_minimum(db):
    wa.process_inbox(db, message(db, n=1), deps_for(Agent(), Transcriber(speech.SpeechError('HTTP 500'))))
    assert next(iter(db.store['whatsapp_quota'].values()))['stt_seconds'] >= speech.MIN_CHARGE_SECONDS


class _Session:
    def post(self, url, json=None, timeout=None):
        class Response:
            status_code = 200

            def json(self):
                return {'results': []}
        return Response()


def test_amr_is_estimated_at_1600_bytes_per_second_and_mp3_at_4000():
    assert speech.estimate_seconds(b'\0' * 16000, 'audio/amr') == pytest.approx(10.0)
    assert speech.estimate_seconds(b'\0' * 40000, 'audio/mpeg') == pytest.approx(10.0)
    assert speech.estimate_seconds(b'\0' * 40000, 'audio/aac') == pytest.approx(10.0)
    result = speech.transcribe(b'\0' * 16000, 'audio/amr; rate=8000', session=_Session())
    assert result['seconds'] == pytest.approx(10.0)


def test_the_stt_charge_never_reads_the_document_first(db, monkeypatch):
    from tests import fakes

    def no_read(self, transaction=None):
        raise AssertionError('the charge must be a blind set(merge) + Increment')
    with monkeypatch.context() as patch:
        patch.setattr(fakes.FakeDocRef, 'get', no_read)
        wa._stt_charge(db, ADMIN, 7, now=NOW)
        wa._stt_charge(db, ADMIN, 3.5, now=NOW)
    assert next(iter(db.store['whatsapp_quota'].values()))['stt_seconds'] == 10.5


def test_audio_is_downloaded_with_the_two_megabyte_limit(db):
    seen = []
    deps = deps_for(Agent(), Transcriber(say('hola')), download=lambda url, max_bytes=None: seen.append(max_bytes) or b'x')
    wa.process_inbox(db, message(db, n=1), deps)
    assert seen == [speech.MAX_BYTES]


def test_an_audio_over_the_download_limit_gets_the_too_long_answer(db):
    def too_big(url, max_bytes=None):
        raise wa.MediaTooLarge('too big')
    sent = Sent()
    assert wa.process_inbox(db, message(db, n=1), deps_for(Agent(), Transcriber(), sent, download=too_big)) == 'audio_too_long'
    assert sent.items == ['Uf, muy largo 😅 ¿me lo mandas en audios de menos de 1 minuto?']


def test_the_daily_counters_follow_chiles_day_not_utc(db):
    late = datetime(2026, 10, 13, 1, 0, 0)          # 22:00 of Oct 12 in Santiago
    wa.process_inbox(db, message(db, n=1, now=late), deps_for(Agent(), Transcriber(say('hola')), now=late))
    assert list(db.store['whatsapp_quota']) == [f'{ADMIN}_20261012']


# ============ 5. a doubtful spoken SI / NO asks for it in writing ============

def test_a_low_confidence_si_asks_for_it_in_writing_without_calling_the_model(db):
    propose_first(db)
    agent, sent = Agent(), Sent()
    assert wa.process_inbox(db, message(db, 'SM2', n=1), deps_for(agent, Transcriber(say('sí', 0.5)), sent)) == 'command'
    assert sent.items == [ASK_WRITTEN] and agent.seen == [] and expense_count(db) == 0


def test_a_forwarded_voice_si_asks_for_it_in_writing(db):
    propose_first(db)
    agent, sent = Agent(), Sent()
    wa.process_inbox(db, message(db, 'SM2', n=1, forwarded=True), deps_for(agent, Transcriber(say('sí', 0.99)), sent))
    assert sent.items == [ASK_WRITTEN] and agent.seen == [] and expense_count(db) == 0


def test_a_doubtful_si_with_nothing_waiting_is_just_text_for_the_agent(db):
    agent = Agent()
    assert wa.process_inbox(db, message(db, n=1), deps_for(agent, Transcriber(say('sí', 0.5)))) == 'answered'
    assert agent.seen


def test_the_voice_confirmation_switch_turns_spoken_si_off(db, monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_VOICE_CONFIRM', 'false')
    propose_first(db)
    agent, sent = Agent(), Sent()
    wa.process_inbox(db, message(db, 'SM2', n=1), deps_for(agent, Transcriber(say('sí', None)), sent))
    assert sent.items == [ASK_WRITTEN] and expense_count(db) == 0
    wa.process_inbox(db, message(db, 'SM3', body='SI'), deps_for(agent, sent=sent))     # typed still works
    assert expense_count(db) == 1


def test_a_confident_or_unknown_confidence_spoken_si_still_confirms_by_default(db):
    propose_first(db)
    assert wa.process_inbox(db, message(db, 'SM2', n=1), deps_for(Agent(), Transcriber(say('dale', None)))) == 'command'
    assert expense_count(db) == 1


# ============ 10. "deshacer" by voice ============

def test_a_spoken_deshacer_is_a_command(db):
    agent, sent = Agent(), Sent()
    assert wa.process_inbox(db, message(db, n=1), deps_for(agent, Transcriber(say('deshacer', 0.95)), sent)) == 'command'
    assert agent.seen == [] and sent.items == [wa.NOTHING_TO_UNDO]


@pytest.mark.parametrize('kwargs,confidence', [({'forwarded': True}, 0.95), ({'body': 'hola'}, 0.95), ({}, 0.4)])
def test_a_spoken_deshacer_that_is_not_the_whole_clear_message_goes_to_the_agent(db, kwargs, confidence):
    agent = Agent()
    assert wa.process_inbox(db, message(db, n=1, **kwargs), deps_for(agent, Transcriber(say('deshacer', confidence)))) == 'answered'
    assert agent.seen


# ============ 11. a capped note next to a heard one is announced ============

def test_a_note_left_unheard_by_the_daily_cap_is_announced(db, monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_STT_DAILY_SECONDS', '10')
    sent, agent = Sent(), Agent()
    transcriber = Transcriber(say('primera nota', seconds=20), say('segunda'))
    wa.process_inbox(db, message(db, n=2), deps_for(agent, transcriber, sent))
    assert len(transcriber.calls) == 1
    assert sent.items[0].startswith('Una nota de voz no la pude escuchar (tope diario).')


# ============ 12. a failed SEND after a saved SI is not "no pude procesar" ============

def test_a_send_failure_after_a_confirmed_si_is_logged_not_apologized(db):
    propose_first(db)
    attempts = []

    def flaky(phone, body):
        attempts.append(body)
        raise RuntimeError('twilio down')
    assert wa.process_inbox(db, message(db, 'SM2', body='SI'), deps_for(Agent(), sent=flaky)) == 'command'
    assert expense_count(db) == 1 and db.store['whatsapp_inbox']['SM2']['status'] == 'done'
    assert not any('No pude procesar' in body for body in attempts)


# ============ 14. no Account SID in errors ============

SID_URL = 'https://api.twilio.com/2010-04-01/Accounts/ACtest-fake-account-sid/Messages/MM1/Media/ME1'


def test_a_failed_media_download_does_not_leak_the_account_sid(monkeypatch):
    import requests

    class Response:
        raw = None

        def raise_for_status(self):
            raise requests.HTTPError(f'404 Client Error: Not Found for url: {SID_URL}')
    monkeypatch.setattr(routes.requests, 'get', lambda *a, **k: Response())
    with pytest.raises(Exception) as error:
        routes._download(SID_URL)
    assert 'AC0123456789' not in str(error.value) and '404' in str(error.value)


def test_download_reads_at_most_the_given_limit(monkeypatch):
    reads = []

    class Raw:
        def read(self, n, decode_content=True):
            reads.append(n)
            return b'x' * 10

    class Response:
        raw = Raw()

        def raise_for_status(self):
            pass
    monkeypatch.setattr(routes.requests, 'get', lambda *a, **k: Response())
    assert routes._download(SID_URL, max_bytes=100) == b'x' * 10 and reads == [101]


def test_the_error_saved_in_the_inbox_has_no_account_sid(db):
    def boom(messages, user):
        raise RuntimeError(f'404 for url: {SID_URL}')
    wa.process_inbox(db, message(db, 'SM1', body='hola'), deps_for(boom))
    stored = db.store['whatsapp_inbox']['SM1']
    assert stored['status'] == 'failed' and 'AC0123456789' not in stored['error']


# ============ 15. a voice note alone does not open a burst ============

def test_a_lone_voice_note_opens_no_burst_but_joins_an_open_one(db):
    message(db, 'SM1', n=1, content_type='audio/ogg; codecs=opus', now=NOW)
    assert db.store['whatsapp_inbox']['SM1']['burst_id'] is None and 'whatsapp_bursts' not in db.store
    message(db, 'SM2', n=1, content_type='image/jpeg', now=NOW + timedelta(seconds=1))
    message(db, 'SM3', n=1, content_type='audio/ogg', now=NOW + timedelta(seconds=2))
    assert db.store['whatsapp_inbox']['SM3']['burst_id'] == 'SM2'
