"""Speech-to-text for WhatsApp voice notes (Google Speech-to-Text API v2, plain REST).

Why REST and not google-cloud-speech: that library pulls grpc (slower cold start, a new dependency). `google.auth` and
`AuthorizedSession` already ship with firebase-admin, and v2 has `autoDecodingConfig` (no exact sample rate needed).
Both are imported lazily inside `transcribe`: a cold start is a project priority and most messages are not audio.

The audio is NEVER stored or logged. Only the transcript leaves this module.
"""
import base64
import logging
import os
import struct
import time

logger = logging.getLogger(__name__)

DEFAULT_PROJECT = 'pablospizza-d84bf'
RECOGNIZE_URL = 'https://speech.googleapis.com/v2/projects/{project}/locations/global/recognizers/_:recognize'
MAX_SECONDS = 58            # the synchronous API accepts up to 60 s
MAX_BYTES = 2 * 1024 * 1024
FALLBACK_BYTES_PER_SECOND = 4000  # only to charge the daily cap when the duration cannot be read (~32 kbps)
AMR_BYTES_PER_SECOND = 1600       # AMR-NB is ~12 kbps: dividing by 4000 would charge a 58 s note as 23 s
MIN_CHARGE_SECONDS = 5.0          # what a note costs the cap even when the transcription fails (it still hit Google)
REQUEST_TIMEOUT = 25

BASE_PHRASES = ['pizzeros', 'pizza party', 'boleta', 'factura', 'merma', 'Líder', 'Jumbo', 'Lo Valledor']
MAX_ITEM_PHRASES = 100
PHRASE_CACHE_SECONDS = 600
_phrase_cache = {'at': 0.0, 'phrases': None}


class SpeechError(Exception):
    """The transcription could not be done (API error, bad audio)"""


class AudioTooLong(SpeechError):
    """Rejected before calling the API: the note is longer than 58 s or heavier than 2 MB"""

    def __init__(self, seconds=None, size=None):
        super().__init__(f'audio too long (seconds={seconds}, bytes={size})')
        self.seconds, self.size = seconds, size


def stt_model():
    return os.getenv('AI_WHATSAPP_STT_MODEL', 'long').strip() or 'long'


def ogg_opus_seconds(data):
    """Duration of an Ogg/Opus file: granule position of the LAST page minus the pre-skip of OpusHead, at 48 kHz.
    None when it is not a readable Ogg/Opus file."""
    if not data or data[:4] != b'OggS':
        return None
    head = data.find(b'OpusHead')
    if head < 0 or len(data) < head + 12:
        return None
    pre_skip = struct.unpack_from('<H', data, head + 10)[0]
    last = data.rfind(b'OggS')
    while last > 0 and (len(data) < last + 14 or data[last + 4] != 0):  # version byte must be 0
        last = data.rfind(b'OggS', 0, last)
    if last < 0 or len(data) < last + 14:
        return None
    granule = struct.unpack_from('<q', data, last + 6)[0]
    if granule <= 0:
        return None
    return max(0.0, (granule - pre_skip) / 48000.0)


def estimate_seconds(data, content_type=None):
    """Duration to charge the daily cap: the real one for Ogg/Opus, else the size over a typical bitrate"""
    real = ogg_opus_seconds(data)
    if real is not None:
        return real
    kind = (content_type or '').split(';')[0].strip().lower()
    rate = AMR_BYTES_PER_SECOND if kind == 'audio/amr' else FALLBACK_BYTES_PER_SECOND
    return round(len(data or b'') / rate, 1)


def phrase_list(db=None, now=None):
    """Words that help the recognizer with the business vocabulary (cached 10 minutes)"""
    now = time.time() if now is None else now
    if _phrase_cache['phrases'] is not None and now - _phrase_cache['at'] < PHRASE_CACHE_SECONDS:
        return list(_phrase_cache['phrases'])
    phrases = list(BASE_PHRASES)
    if db is not None:
        try:
            names = []
            for doc in db.collection('inventory').stream():
                name = str((doc.to_dict() or {}).get('name') or '').strip()
                if name and name not in names and name not in phrases:
                    names.append(name)
                if len(names) >= MAX_ITEM_PHRASES:
                    break
            phrases += names
        except Exception as exc:  # noqa: BLE001 - the vocabulary is a nicety, never a reason to fail
            logger.warning('Could not read inventory names for speech phrases: %s', exc)
    _phrase_cache.update({'at': now, 'phrases': phrases})
    return list(phrases)


def build_request(data, phrases=None):
    config = {
        'autoDecodingConfig': {},
        'languageCodes': ['es-CL'],
        'model': stt_model(),
        'features': {'enableAutomaticPunctuation': True},
    }
    if phrases:
        config['adaptation'] = {'phraseSets': [{'inlinePhraseSet': {
            'phrases': [{'value': p, 'boost': 10} for p in phrases]}}]}
    return {'config': config, 'content': base64.b64encode(data).decode()}


def _session():
    import google.auth
    from google.auth.transport.requests import AuthorizedSession
    credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    return AuthorizedSession(credentials)


def transcribe(data, content_type, phrases=None, session=None):
    """-> {'text', 'confidence' (None when unknown), 'seconds'}. Raises AudioTooLong before any network call."""
    size = len(data or b'')
    seconds = ogg_opus_seconds(data)
    if size > MAX_BYTES or (seconds is not None and seconds > MAX_SECONDS):
        raise AudioTooLong(seconds, size)
    if seconds is None:
        seconds = estimate_seconds(data, content_type)
    project = os.getenv('AI_WHATSAPP_STT_PROJECT', DEFAULT_PROJECT)
    try:
        session = session or _session()
        response = session.post(RECOGNIZE_URL.format(project=project), json=build_request(data, phrases),
                                timeout=REQUEST_TIMEOUT)
    except Exception as exc:  # noqa: BLE001
        raise SpeechError(f'speech request failed: {exc}') from exc
    if response.status_code != 200:
        # never echo the body: it can contain request details; the status is enough to diagnose
        raise SpeechError(f'speech API answered HTTP {response.status_code}')
    pieces, confidences = [], []
    for result in (response.json() or {}).get('results', []):
        alternatives = result.get('alternatives') or []
        if not alternatives:
            continue
        piece = (alternatives[0].get('transcript') or '').strip()
        if piece:
            pieces.append(piece)
            if alternatives[0].get('confidence'):
                confidences.append(float(alternatives[0]['confidence']))
    # 0 / missing means "unknown"; with several results the weakest one decides
    return {'text': ' '.join(pieces).strip(), 'confidence': min(confidences) if confidences else None,
            'seconds': seconds}
