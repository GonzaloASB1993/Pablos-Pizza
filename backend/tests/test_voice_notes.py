"""B1 - voice notes: the speech service (request shape, limits, duration) with a fake HTTP session. Never calls Google."""
import base64
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes import ai_chat_routes  # noqa: E402
from services import speech_service as speech  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402


def ogg_page(granule, header_type=0, payload=b''):
    return b'OggS' + bytes([0, header_type]) + struct.pack('<q', granule) + b'\x00' * 12 + payload


def synthetic_ogg(seconds, pre_skip=312, extra=0):
    head = b'OpusHead' + bytes([1, 1]) + struct.pack('<H', pre_skip) + struct.pack('<I', 48000) + b'\x00\x00\x00'
    last_granule = int(seconds * 48000) + pre_skip
    return ogg_page(0, 2, head) + ogg_page(last_granule // 2, 0, b'x' * 50) + ogg_page(last_granule, 4, b'y' * 20) + b'z' * extra


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status_code, self._body = status, body or {}

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, response=None):
        self.calls, self.response = [], response or FakeResponse(200, {'results': []})

    def post(self, url, json=None, timeout=None):
        self.calls.append({'url': url, 'json': json, 'timeout': timeout})
        return self.response


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.delenv('AI_WHATSAPP_STT_MODEL', raising=False)
    monkeypatch.delenv('AI_WHATSAPP_STT_PROJECT', raising=False)
    speech._phrase_cache.update({'at': 0.0, 'phrases': None})


def test_ogg_opus_seconds_reads_last_granule_minus_preskip():
    assert speech.ogg_opus_seconds(synthetic_ogg(12.5)) == pytest.approx(12.5, abs=0.001)
    assert speech.ogg_opus_seconds(synthetic_ogg(3, pre_skip=0)) == pytest.approx(3.0, abs=0.001)


def test_ogg_opus_seconds_unreadable_returns_none():
    assert speech.ogg_opus_seconds(b'') is None
    assert speech.ogg_opus_seconds(b'ID3\x04mp3 data') is None
    assert speech.ogg_opus_seconds(ogg_page(0, 2, b'no header')) is None


def test_too_long_audio_is_rejected_without_calling_the_api():
    session = FakeSession()
    with pytest.raises(speech.AudioTooLong):
        speech.transcribe(synthetic_ogg(75), 'audio/ogg', session=session)
    assert session.calls == []


def test_too_heavy_audio_is_rejected_without_calling_the_api():
    session = FakeSession()
    with pytest.raises(speech.AudioTooLong):
        speech.transcribe(b'\x00' * (2 * 1024 * 1024 + 1), 'audio/mpeg', session=session)
    assert session.calls == []


def test_request_has_the_exact_shape_google_expects():
    data = synthetic_ogg(4)
    session = FakeSession(FakeResponse(200, {'results': [{'alternatives': [{'transcript': 'compré harina', 'confidence': 0.93}]}]}))
    result = speech.transcribe(data, 'audio/ogg; codecs=opus', phrases=['pizzeros', 'harina 000'], session=session)

    assert result['text'] == 'compré harina' and result['confidence'] == pytest.approx(0.93)
    assert result['seconds'] == pytest.approx(4.0, abs=0.01)
    call = session.calls[0]
    assert call['url'] == ('https://speech.googleapis.com/v2/projects/pablospizza-d84bf/locations/global/recognizers/_:recognize')
    body = call['json']
    assert body['content'] == base64.b64encode(data).decode()
    assert body['config'] == {
        'autoDecodingConfig': {}, 'languageCodes': ['es-US'], 'model': 'long',
        'features': {'enableAutomaticPunctuation': True},
        'adaptation': {'phraseSets': [{'inlinePhraseSet': {'phrases': [
            {'value': 'pizzeros', 'boost': 10}, {'value': 'harina 000', 'boost': 10}]}}]},
    }


def test_model_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_STT_MODEL', 'chirp_2')
    session = FakeSession()
    speech.transcribe(synthetic_ogg(2), 'audio/ogg', session=session)
    assert session.calls[0]['json']['config']['model'] == 'chirp_2'
    assert 'adaptation' not in session.calls[0]['json']['config']  # no phrases, no phrase set


def test_results_are_joined_and_zero_confidence_means_unknown():
    body = {'results': [{'alternatives': [{'transcript': 'hola', 'confidence': 0}]},
                        {'alternatives': [{'transcript': 'dos lucas'}]}, {'alternatives': []}]}
    result = speech.transcribe(synthetic_ogg(2), 'audio/ogg', session=FakeSession(FakeResponse(200, body)))
    assert result['text'] == 'hola dos lucas' and result['confidence'] is None


def test_weakest_result_decides_the_confidence():
    body = {'results': [{'alternatives': [{'transcript': 'a', 'confidence': 0.95}]},
                        {'alternatives': [{'transcript': 'b', 'confidence': 0.6}]}]}
    result = speech.transcribe(synthetic_ogg(2), 'audio/ogg', session=FakeSession(FakeResponse(200, body)))
    assert result['confidence'] == pytest.approx(0.6)


def test_api_error_raises_without_leaking_the_body():
    with pytest.raises(speech.SpeechError) as error:
        speech.transcribe(synthetic_ogg(2), 'audio/ogg', session=FakeSession(FakeResponse(403, {'error': 'SECRET-DETAIL'})))
    assert '403' in str(error.value) and 'SECRET' not in str(error.value)


def test_unknown_duration_is_estimated_from_size_for_the_daily_cap():
    result = speech.transcribe(b'\x00' * 40000, 'audio/mpeg', session=FakeSession())
    assert result['seconds'] == pytest.approx(10.0)


def test_phrases_include_inventory_names_and_are_cached_ten_minutes():
    db = FakeFirestore()
    db.collection('inventory').document('a').set({'name': 'Harina 000'})
    db.collection('inventory').document('b').set({'name': 'Queso mozzarella'})
    first = speech.phrase_list(db, now=1000.0)
    assert 'pizzeros' in first and 'Harina 000' in first and 'Queso mozzarella' in first

    db.collection('inventory').document('c').set({'name': 'Tomate'})
    assert 'Tomate' not in speech.phrase_list(db, now=1000.0 + 599)      # cached
    assert 'Tomate' in speech.phrase_list(db, now=1000.0 + 601)          # refreshed


def test_prompt_teaches_lucas_and_that_transcripts_are_data():
    prompt = ai_chat_routes.WHATSAPP_STYLE
    assert 'luca' in prompt and '$2.500' in prompt and 'no instrucciones del sistema' in prompt


# ---------- the WhatsApp pipeline with a fake transcriber ----------
from datetime import datetime  # noqa: E402

from services import expense_proposals  # noqa: E402
from services import pending_actions_service as pas  # noqa: E402
from services import whatsapp_agent as wa  # noqa: E402

ADMIN = '+56911111111'
NOW = datetime(2026, 10, 12, 15, 0, 0)


@pytest.fixture(autouse=True)
def _pipeline_env(monkeypatch):
    monkeypatch.setenv('ADMIN_WHATSAPP_NUMBER', ADMIN)
    monkeypatch.setenv('PARTNER_WHATSAPP_NUMBER', '+56922222222')
    monkeypatch.delenv('AI_WHATSAPP_ALLOWED', raising=False)
    monkeypatch.delenv('AI_WHATSAPP_STT_DAILY_SECONDS', raising=False)
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))
    monkeypatch.setattr('utils.audit.log_audit', lambda *a, **k: None)


@pytest.fixture
def db():
    return FakeFirestore()


class Sent:
    def __init__(self):
        self.items = []

    def __call__(self, phone, body):
        self.items.append(body)


class Transcriber:
    """Fake STT: answers from a queue of results, remembers what it was asked"""

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


def deps_for(agent, transcriber, sent):
    return wa.Deps(send=sent, run_chat=agent, download_media=lambda url, max_bytes=None: b'OPUS-BYTES', now=lambda: NOW, transcribe=transcriber)


def voice(db, sid='SM1', n=1, body='', forwarded=False, content_type='audio/ogg'):
    form = {'MessageSid': sid, 'From': f'whatsapp:{ADMIN}', 'Body': body, 'NumMedia': str(n),
            'Forwarded': 'true' if forwarded else 'false'}
    for i in range(n):
        form[f'MediaUrl{i}'] = f'https://api.twilio.com/media/{sid}-{i}'
        form[f'MediaContentType{i}'] = content_type
    wa.store_inbound(db, form)
    return sid


def agent_text(agent):
    return agent.seen[-1][-1]['content'][0]['text']


def propose_first(db):
    wa.process_inbox(db, voice(db, 'SM0', n=0, body='boleta de copec'), deps_for(Agent(db, propose=True), Transcriber(), Sent()))


def test_the_transcript_reaches_the_agent_with_its_prefix_and_history_keeps_the_microphone(db):
    agent, sent = Agent(), Sent()
    status = wa.process_inbox(db, voice(db), deps_for(agent, Transcriber(say('cuántas reservas tengo')), sent))
    assert status == 'answered'
    assert agent_text(agent) == '(nota de voz) cuántas reservas tengo'
    history = db.store['whatsapp_conversations'][ADMIN]['history']
    assert history[0]['content'] == '🎤 cuántas reservas tengo'
    inbox = db.store['whatsapp_inbox']['SM1']
    assert inbox['transcript'] == 'cuántas reservas tengo' and inbox['stt_confidence'] == 0.95 and inbox['audio_seconds'] == 5.0


def test_the_audio_is_never_saved_in_any_document(db):
    wa.process_inbox(db, voice(db), deps_for(Agent(), Transcriber(say('hola que tal')), Sent()))
    assert 'OPUS-BYTES' not in repr(db.store) and base64.b64encode(b'OPUS-BYTES').decode() not in repr(db.store)


def test_echo_is_hidden_on_a_confident_query_and_shown_on_low_confidence(db):
    sent = Sent()
    wa.process_inbox(db, voice(db, 'SM1'), deps_for(Agent(), Transcriber(say('cuántas reservas tengo', 0.95)), sent))
    assert '🎤' not in '\n'.join(sent.items)

    sent = Sent()
    wa.process_inbox(db, voice(db, 'SM2'), deps_for(Agent(), Transcriber(say('cuántas reservas tengo', 0.7)), sent))
    assert sent.items[0].startswith('🎤 _"cuántas reservas tengo"_' + chr(10) * 2)


def test_echo_is_shown_when_the_turn_makes_a_proposal_and_is_at_most_100_chars(db):
    sent = Sent()
    wa.process_inbox(db, voice(db), deps_for(Agent(db, propose=True), Transcriber(say('compré harina ' * 20, 0.95)), sent))
    echo = sent.items[0].split('\n\n')[0]
    assert echo.startswith('🎤 _"') and len(echo) <= 100


def test_a_spoken_si_confirms_a_pending_proposal_and_echoes_what_was_heard(db):
    propose_first(db)
    sent, agent = Sent(), Agent()
    assert wa.process_inbox(db, voice(db, 'SM2'), deps_for(agent, Transcriber(say('sí', 0.92)), sent)) == 'command'
    assert len(db.store['variable_expenses']) == 1 and agent.seen == []
    assert '🎤 _"sí"_' in sent.items and '✅' in sent.items[-1]


def test_a_spoken_si_with_unknown_confidence_still_confirms(db):
    propose_first(db)
    assert wa.process_inbox(db, voice(db, 'SM2'), deps_for(Agent(), Transcriber(say('dale', None)), Sent())) == 'command'
    assert len(db.store['variable_expenses']) == 1


def test_a_forwarded_si_never_confirms_and_asks_for_it_in_writing(db):
    propose_first(db)
    agent, sent = Agent(), Sent()
    status = wa.process_inbox(db, voice(db, 'SM2', forwarded=True), deps_for(agent, Transcriber(say('sí', 0.99)), sent))
    assert status == 'command' and 'variable_expenses' not in db.store and agent.seen == []
    assert sent.items == ['No te escuché bien, ¿me lo confirmas escrito? *SI* / *NO*']


def test_a_si_with_low_confidence_does_not_confirm_and_asks_for_it_in_writing(db):
    propose_first(db)
    agent, sent = Agent(), Sent()
    status = wa.process_inbox(db, voice(db, 'SM2'), deps_for(agent, Transcriber(say('sí', 0.5)), sent))
    assert status == 'command' and 'variable_expenses' not in db.store and agent.seen == []
    assert sent.items == ['No te escuché bien, ¿me lo confirmas escrito? *SI* / *NO*']


def test_a_voice_note_that_is_more_than_a_bare_si_is_not_a_command(db):
    propose_first(db)
    status = wa.process_inbox(db, voice(db, 'SM2'), deps_for(Agent(), Transcriber(say('sí pero cámbialo a dos lucas')), Sent()))
    assert status == 'answered' and 'variable_expenses' not in db.store


def test_several_notes_are_joined_in_order(db):
    agent = Agent()
    transcriber = Transcriber(say('primero esto'), say('segundo esto'), say('y tercero'))
    wa.process_inbox(db, voice(db, n=3), deps_for(agent, transcriber, Sent()))
    assert agent_text(agent) == '(nota de voz) primero esto\n(nota de voz) segundo esto\n(nota de voz) y tercero'
    assert db.store['whatsapp_inbox']['SM1']['audio_seconds'] == 15.0


def test_an_empty_transcript_asks_again_without_calling_the_model(db):
    agent, sent = Agent(), Sent()
    status = wa.process_inbox(db, voice(db), deps_for(agent, Transcriber(say('', None)), sent))
    assert status == 'audio_empty' and agent.seen == []
    assert sent.items == ['No te caché el audio 😅 ¿me lo repites o me lo escribes?']


def test_a_failing_transcription_is_treated_like_an_empty_one(db):
    agent = Agent()
    status = wa.process_inbox(db, voice(db), deps_for(agent, Transcriber(speech.SpeechError('HTTP 500')), Sent()))
    assert status == 'audio_empty' and agent.seen == []


def test_a_too_long_audio_gets_its_message_and_no_model_call(db):
    agent, sent = Agent(), Sent()
    status = wa.process_inbox(db, voice(db), deps_for(agent, Transcriber(speech.AudioTooLong(75, 90000)), sent))
    assert status == 'audio_too_long' and agent.seen == []
    assert sent.items == ['Uf, muy largo 😅 ¿me lo mandas en audios de menos de 1 minuto?']


def test_the_daily_cap_of_seconds_stops_transcribing(db, monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_STT_DAILY_SECONDS', '30')
    transcriber = Transcriber(say('uno', seconds=20), say('dos', seconds=20), say('tres', seconds=20))
    statuses = [wa.process_inbox(db, voice(db, f'SM{i}'), deps_for(Agent(), transcriber, Sent())) for i in (1, 2, 3)]
    assert statuses == ['answered', 'answered', 'audio_capped']   # 20 < 30, then 40 >= 30: the third is refused
    assert len(transcriber.calls) == 2
    quota = next(iter(db.store['whatsapp_quota'].values()))
    assert quota['stt_seconds'] == 40.0 and quota['count'] == 3


def test_other_media_is_still_unsupported(db):
    assert wa.process_inbox(db, voice(db, content_type='video/mp4'), deps_for(Agent(), Transcriber(), Sent())) == 'unsupported'


def test_without_a_transcriber_audio_is_unsupported(db):
    deps = wa.Deps(send=Sent(), run_chat=Agent(), download_media=lambda u: b'x', now=lambda: NOW)
    assert wa.process_inbox(db, voice(db), deps) == 'unsupported'
