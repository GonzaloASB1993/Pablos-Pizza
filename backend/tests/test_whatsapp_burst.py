"""B2 tests: bursts grouped at the webhook, one leader worker, merged state, per-phone lock (fake Firestore + fake clock)"""
import io
import os
import sys
from datetime import datetime, timedelta

import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402,F401  (imported at collection time: it loads backend/.env, which must not happen mid-test)
from services import pending_actions_service as pas  # noqa: E402
from services import whatsapp_agent as wa  # noqa: E402
from services import whatsapp_burst as burst  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402

ADMIN = '+56911111111'
T0 = datetime(2026, 10, 12, 15, 0, 0)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_ENABLED', 'true')
    monkeypatch.setenv('ADMIN_WHATSAPP_NUMBER', ADMIN)
    monkeypatch.setenv('PARTNER_WHATSAPP_NUMBER', '+56922222222')
    monkeypatch.delenv('AI_WHATSAPP_ALLOWED', raising=False)
    monkeypatch.delenv('AI_WHATSAPP_BURST_SECONDS', raising=False)
    monkeypatch.delenv('AI_WHATSAPP_TEXT_BURST_SECONDS', raising=False)
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))
    monkeypatch.setattr('utils.audit.log_audit', lambda *a, **k: None)


@pytest.fixture
def db():
    return FakeFirestore()


class Clock:
    """Fake time: sleeping advances it, and a test can hook what happens "while waiting" """

    def __init__(self, start=T0):
        self.t = start
        self.sleeps = []
        self.on_sleep = None

    def now(self):
        return self.t

    def advance(self, seconds):
        self.t += timedelta(seconds=seconds)

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.advance(seconds)
        if self.on_sleep:
            self.on_sleep()


class Agent:
    def __init__(self, reply='listo', fail=False):
        self.calls, self.reply, self.fail = [], reply, fail

    def __call__(self, messages, user):
        self.calls.append(messages)
        if self.fail:
            raise RuntimeError('model down')
        return {'response': self.reply, 'pending_actions': [], 'choices': [], 'usage': {}}


def _jpeg():
    out = io.BytesIO()
    Image.new('RGB', (40, 30), 'white').save(out, 'JPEG')
    return out.getvalue()


def _deps(clock, agent, sent):
    return wa.Deps(send=lambda phone, body: sent.append((phone, body)), run_chat=agent,
                   download_media=lambda url, max_bytes=None: _jpeg(), now=clock.now, sleep=clock.sleep)


def _store(db, clock, sid, body='', photos=0, sender=ADMIN):
    form = {'MessageSid': sid, 'From': f'whatsapp:{sender}', 'Body': body, 'NumMedia': str(photos)}
    for i in range(photos):
        form[f'MediaUrl{i}'] = f'https://m/{sid}/{i}'
        form[f'MediaContentType{i}'] = 'image/jpeg'
    return wa.store_inbound(db, form, now=clock.now())


def _status(db, sid):
    return db.store['whatsapp_inbox'][sid]['status']


def _images(messages):
    return [b for b in messages[-1]['content'] if b['type'] == 'image']


# ============ bursts ============

def test_an_album_of_three_photos_gets_one_leader_two_merged_and_one_answer(db):
    clock, agent, sent = Clock(), Agent('Tres boletas leídas'), []
    for sid in ('SM1', 'SM2', 'SM3'):
        assert _store(db, clock, sid, photos=1)
        clock.advance(0.5)
    deps = _deps(clock, agent, sent)

    # the first two triggers wake up first and find a newer message in the burst: they step aside
    assert wa.process_inbox(db, 'SM1', deps) == 'merged'
    assert wa.process_inbox(db, 'SM2', deps) == 'merged'
    assert agent.calls == [] and sent == []
    assert wa.process_inbox(db, 'SM3', deps) == 'answered'

    assert len(agent.calls) == 1 and len(_images(agent.calls[0])) == 3
    assert sent == [(ADMIN, 'Tres boletas leídas')]
    assert [_status(db, s) for s in ('SM1', 'SM2', 'SM3')] == ['merged', 'merged', 'done']
    assert db.store['whatsapp_bursts'][ADMIN]['state'] == 'done'
    assert sum(clock.sleeps) >= 2.5 - 1e-9                       # the leader waited for the burst to go quiet
    # merged workers charge nothing themselves; the leader charges the burst once: three messages, three units
    assert db.store['whatsapp_quota'][f"{ADMIN}_20261012"]['count'] == 3


def test_a_photo_and_a_text_one_second_later_are_one_turn(db):
    clock, agent, sent = Clock(), Agent(), []
    _store(db, clock, 'SM1', photos=1)
    clock.advance(1)
    _store(db, clock, 'SM2', body='es la boleta de Líder')
    assert db.store['whatsapp_inbox']['SM2']['burst_id'] == 'SM1'
    deps = _deps(clock, agent, sent)

    assert wa.process_inbox(db, 'SM1', deps) == 'merged'
    assert wa.process_inbox(db, 'SM2', deps) == 'answered'
    assert len(agent.calls) == 1 and len(sent) == 1
    content = agent.calls[0][-1]['content']
    assert content[0] == {'type': 'text', 'text': 'es la boleta de Líder'} and len(_images(agent.calls[0])) == 1


def test_a_lone_text_waits_for_nothing(db):
    clock, agent, sent = Clock(), Agent(), []
    _store(db, clock, 'SM1', body='¿cómo va el inventario?')
    assert db.store['whatsapp_inbox']['SM1']['burst_id'] is None and 'whatsapp_bursts' not in db.store

    assert wa.process_inbox(db, 'SM1', _deps(clock, agent, sent)) == 'answered'
    assert clock.sleeps == []                                    # no burst, free lock: not a single sleep
    assert len(agent.calls) == 1


def test_a_twilio_retry_does_not_duplicate_the_inbox_doc_or_the_burst_append(db):
    clock = Clock()
    assert _store(db, clock, 'SM1', photos=1) is True
    clock.advance(0.5)
    assert _store(db, clock, 'SM2', photos=1) is True
    clock.advance(0.5)
    assert _store(db, clock, 'SM2', photos=1) is False           # same MessageSid again
    assert _store(db, clock, 'SM1', photos=1) is False
    assert sorted(db.store['whatsapp_inbox']) == ['SM1', 'SM2']
    assert db.store['whatsapp_bursts'][ADMIN]['sids'] == ['SM1', 'SM2']
    assert db.store['whatsapp_bursts'][ADMIN]['last_sid'] == 'SM2'


def test_a_late_leader_still_gives_a_single_answer(db):
    """Cold start: the worker of the LAST message wakes up first and the first message's worker long after"""
    clock, agent, sent = Clock(), Agent(), []
    for sid in ('SM1', 'SM2', 'SM3'):
        _store(db, clock, sid, photos=1)
        clock.advance(0.5)
    deps = _deps(clock, agent, sent)

    assert wa.process_inbox(db, 'SM3', deps) == 'answered'
    clock.advance(40)                                            # the first instance finally boots
    assert wa.process_inbox(db, 'SM1', deps) == 'merged'
    assert wa.process_inbox(db, 'SM2', deps) == 'merged'
    assert len(agent.calls) == 1 and len(sent) == 1 and len(_images(agent.calls[0])) == 3


def test_a_late_first_worker_does_not_run_after_a_newer_burst_replaced_it(db):
    clock, agent, sent = Clock(), Agent(), []
    _store(db, clock, 'SM1', photos=1)
    deps = _deps(clock, agent, sent)
    assert wa.process_inbox(db, 'SM1', deps) == 'answered'      # alone in its burst: it leads itself
    clock.advance(60)
    _store(db, clock, 'SM2', photos=1)                           # a new burst
    assert db.store['whatsapp_bursts'][ADMIN]['id'] == 'SM2'
    assert wa.process_inbox(db, 'SM1', deps) == 'skipped'        # SM1 was already claimed: nothing runs twice
    assert len(agent.calls) == 1


def test_a_burst_closes_after_ten_messages(db):
    clock = Clock()
    ids = []
    for i in range(11):
        _store(db, clock, f'SM{i}', photos=1)
        ids.append(db.store['whatsapp_inbox'][f'SM{i}']['burst_id'])
        clock.advance(0.2)
    assert ids[:10] == ['SM0'] * 10 and ids[10] == 'SM10'
    assert db.store['whatsapp_bursts'][ADMIN]['sids'] == ['SM10']


def test_a_burst_closes_after_fifteen_seconds_even_if_messages_keep_coming(db):
    clock = Clock()
    ids = []
    for i in range(8):                                           # one every 2.5 s: always inside the 3 s window
        _store(db, clock, f'SM{i}', photos=1)
        ids.append(db.store['whatsapp_inbox'][f'SM{i}']['burst_id'])
        clock.advance(2.5)
    # SM0 at 0 s ... SM6 at 15 s still joins; SM7 at 17.5 s starts a new burst
    assert ids == ['SM0'] * 7 + ['SM7']


def test_more_than_three_photos_are_read_up_to_three_and_the_answer_says_so(db):
    clock, agent, sent = Clock(), Agent('Listo'), []
    for sid in ('SM1', 'SM2', 'SM3', 'SM4'):
        _store(db, clock, sid, photos=1)
        clock.advance(0.3)
    assert wa.process_inbox(db, 'SM4', _deps(clock, agent, sent)) == 'answered'
    assert len(_images(agent.calls[0])) == 3
    assert sent[0][1].startswith('Leí las primeras 3 fotos.') and sent[0][1].endswith('Listo')


def test_three_photos_or_fewer_get_no_notice(db):
    clock, agent, sent = Clock(), Agent('Listo'), []
    _store(db, clock, 'SM1', photos=3)
    wa.process_inbox(db, 'SM1', _deps(clock, agent, sent))
    assert sent == [(ADMIN, 'Listo')]


def test_warmup_markers_never_join_a_burst(db):
    clock = Clock()
    _store(db, clock, 'SM1', photos=1)
    _store(db, clock, 'warmup-1760000000', photos=1)
    assert db.store['whatsapp_inbox']['warmup-1760000000']['burst_id'] is None
    assert db.store['whatsapp_bursts'][ADMIN]['sids'] == ['SM1']


def test_the_burst_window_comes_from_the_environment(db, monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_BURST_SECONDS', '1')
    clock, agent, sent = Clock(), Agent(), []
    _store(db, clock, 'SM1', photos=1)
    clock.advance(2)                                             # outside the 1 s window
    _store(db, clock, 'SM2', photos=1)
    assert db.store['whatsapp_inbox']['SM2']['burst_id'] == 'SM2'
    assert wa.process_inbox(db, 'SM2', _deps(clock, agent, sent)) == 'answered'
    assert sum(clock.sleeps) <= 1.0 + 1e-9


def test_a_text_can_optionally_wait_for_a_photo_that_follows(db, monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_TEXT_BURST_SECONDS', '2')
    clock, agent, sent = Clock(), Agent(), []
    _store(db, clock, 'SM1', body='esta es la compra de hoy')
    assert db.store['whatsapp_inbox']['SM1']['burst_id'] == 'SM1'
    clock.advance(1)
    _store(db, clock, 'SM2', photos=1)
    deps = _deps(clock, agent, sent)
    assert wa.process_inbox(db, 'SM1', deps) == 'merged'
    assert wa.process_inbox(db, 'SM2', deps) == 'answered'
    assert len(agent.calls) == 1 and len(_images(agent.calls[0])) == 1


def test_a_leader_takes_over_after_twenty_seconds_at_most(db):
    clock, agent, sent = Clock(), Agent(), []
    _store(db, clock, 'SM1', photos=1)
    clock.advance(0.1)

    # SM1 is the only message: simulate an absurdly long window to prove the cap
    db.store['whatsapp_bursts'][ADMIN]['window'] = 600
    assert wa.process_inbox(db, 'SM1', _deps(clock, agent, sent)) == 'answered'
    assert burst.LEADER_MAX_WAIT <= sum(clock.sleeps) < burst.LEADER_MAX_WAIT + 2


# ============ lock ============

def _hold_lock(db, owner, until):
    db.store.setdefault('whatsapp_locks', {})[ADMIN] = {'owner_sid': owner, 'until': until}


def test_the_second_turn_waits_for_the_lock_and_sees_the_first_turns_history(db):
    clock, agent, sent = Clock(), Agent(), []
    _hold_lock(db, 'SM-OTHER', T0 + timedelta(seconds=180))
    _store(db, clock, 'SM2', body='segundo mensaje')

    def first_turn_finishes():
        # the first turn saves its history and frees the lock while the second one is waiting
        if db.store['whatsapp_locks'][ADMIN]['owner_sid'] == 'SM-OTHER':
            wa._save_conversation(db, ADMIN, {'history': [{'role': 'user', 'content': 'primer mensaje'},
                                                           {'role': 'assistant', 'content': 'primera respuesta'}],
                                              'pending': [], 'choices': []}, clock.now())
            db.store['whatsapp_locks'][ADMIN]['owner_sid'] = None
    clock.on_sleep = first_turn_finishes

    assert wa.process_inbox(db, 'SM2', _deps(clock, agent, sent)) == 'answered'
    assert clock.sleeps == [1]                                   # it polled once
    history = [m['content'] if isinstance(m['content'], str) else m['content'][0]['text'] for m in agent.calls[0]]
    assert history == ['primer mensaje', 'primera respuesta', 'segundo mensaje']


def test_an_expired_lock_is_taken_over_without_waiting(db):
    clock, agent, sent = Clock(), Agent(), []
    _hold_lock(db, 'SM-DEAD', T0 - timedelta(seconds=1))
    _store(db, clock, 'SM1', body='hola, ¿qué tal el stock?')
    assert wa.process_inbox(db, 'SM1', _deps(clock, agent, sent)) == 'answered'
    assert clock.sleeps == [] and len(agent.calls) == 1


def test_a_lock_that_stays_valid_is_never_stolen_the_turn_gives_up_after_the_max_wait(db):
    clock, agent, sent = Clock(), Agent(), []
    _hold_lock(db, 'SM-STUCK', T0 + timedelta(hours=1))
    _store(db, clock, 'SM1', body='¿hay pizzas para el sábado?')
    assert wa.process_inbox(db, 'SM1', _deps(clock, agent, sent)) == 'failed'
    assert burst.LOCK_MAX_WAIT <= sum(clock.sleeps) < burst.LOCK_MAX_WAIT + 2
    assert agent.calls == [] and 'Escríbeme de nuevo' in sent[0][1]
    assert db.store['whatsapp_locks'][ADMIN]['owner_sid'] == 'SM-STUCK'   # the holder is alive: its lock is untouched


def test_the_lock_is_held_during_the_turn_and_released_after(db):
    clock, sent = Clock(), []
    _store(db, clock, 'SM1', body='hola, ¿cómo va todo?')
    seen = {}

    def agent(messages, user):
        seen['lock'] = dict(db.store['whatsapp_locks'][ADMIN])
        return {'response': 'bien', 'pending_actions': [], 'choices': []}

    assert wa.process_inbox(db, 'SM1', _deps(clock, agent, sent)) == 'answered'
    assert seen['lock']['owner_sid'] == 'SM1' and seen['lock']['until'] == T0 + timedelta(seconds=burst.LOCK_TTL)
    assert db.store['whatsapp_locks'][ADMIN]['owner_sid'] is None


def test_the_lock_is_released_when_the_agent_fails(db):
    clock, agent, sent = Clock(), Agent(fail=True), []
    _store(db, clock, 'SM1', body='hola, ¿cómo va todo?')
    assert wa.process_inbox(db, 'SM1', _deps(clock, agent, sent)) == 'failed'
    assert db.store['whatsapp_locks'][ADMIN]['owner_sid'] is None
    assert _status(db, 'SM1') == 'failed'
    assert 'No pude procesar' in sent[0][1]


def test_a_failing_burst_leader_closes_the_burst_and_the_lock(db):
    clock, agent, sent = Clock(), Agent(fail=True), []
    _store(db, clock, 'SM1', photos=1)
    clock.advance(0.5)
    _store(db, clock, 'SM2', photos=1)
    deps = _deps(clock, agent, sent)
    assert wa.process_inbox(db, 'SM1', deps) == 'merged'
    assert wa.process_inbox(db, 'SM2', deps) == 'failed'
    assert db.store['whatsapp_bursts'][ADMIN]['state'] == 'done'
    assert db.store['whatsapp_locks'][ADMIN]['owner_sid'] is None


def test_a_burst_with_a_photo_and_a_voice_note_is_one_turn_with_both(db):
    clock, agent, sent = Clock(), Agent('Anotado'), []
    _store(db, clock, 'SM1', photos=1)
    clock.advance(1)
    voice = {'MessageSid': 'SM2', 'From': f'whatsapp:{ADMIN}', 'Body': '', 'NumMedia': '1',
             'MediaUrl0': 'https://m/SM2/0', 'MediaContentType0': 'audio/ogg'}
    assert wa.store_inbound(db, voice, now=clock.now())
    assert db.store['whatsapp_inbox']['SM2']['burst_id'] == 'SM1'
    deps = _deps(clock, agent, sent)
    deps.transcribe = lambda data, content_type: {'text': 'es la compra de Líder', 'confidence': 0.95, 'seconds': 4}

    assert wa.process_inbox(db, 'SM1', deps) == 'merged'
    assert wa.process_inbox(db, 'SM2', deps) == 'answered'
    assert len(agent.calls) == 1 and len(sent) == 1
    content = agent.calls[0][-1]['content']
    assert len(_images(agent.calls[0])) == 1
    assert any('(nota de voz) es la compra de Líder' in b.get('text', '') for b in content)
    assert db.store['whatsapp_inbox']['SM2']['transcript'] == 'es la compra de Líder'


def test_a_lock_that_is_no_longer_ours_is_not_released(db):
    clock = Clock()
    _hold_lock(db, 'SM-NEW-OWNER', T0 + timedelta(seconds=100))
    burst.release_lock(db, ADMIN, 'SM-OLD', clock.now())
    assert db.store['whatsapp_locks'][ADMIN]['owner_sid'] == 'SM-NEW-OWNER'
