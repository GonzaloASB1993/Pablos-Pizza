"""WhatsApp channel routes: the Twilio webhook (public, signature-checked) and the worker that runs the agent.

Webhook   POST /api/whatsapp/webhook   Twilio -> store the message -> answer 200 immediately.
Worker    process_inbox_message(app, sid)   called by the Firestore trigger in main.py (or inline, see
          AI_WHATSAPP_MODE) -> runs the assistant and answers through the Twilio API.

Twilio console: set the number's "When a message comes in" webhook to
  https://<function-url>/api/whatsapp/webhook   (POST)
and, if Twilio signs a different URL than the one this function sees, set WHATSAPP_WEBHOOK_URL to it.
"""
import logging
import os
import time
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape

import requests
from flask import Blueprint, Response, request

from database import get_db
from services import recent_activity, situation
from services import whatsapp_agent as wa

logger = logging.getLogger(__name__)

whatsapp_bp = Blueprint('whatsapp', __name__, url_prefix='/api/whatsapp')

EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


def _twiml(text=None):
    """Empty TwiML, or one that makes Twilio answer with `text` right away"""
    if not text:
        return Response(EMPTY_TWIML, status=200, mimetype='text/xml')
    body = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{xml_escape(text)}</Message></Response>'
    return Response(body, status=200, mimetype='text/xml')


def candidate_urls():
    """URLs Twilio may have signed: the configured one, and the one this request arrived at"""
    urls = [os.getenv('WHATSAPP_WEBHOOK_URL', '').strip()]
    host = request.headers.get('X-Forwarded-Host') or request.host
    urls.append(f"https://{host}{request.path}")
    if request.query_string:
        urls = [u + '?' + request.query_string.decode() if u else u for u in urls]
    return [u for u in urls if u]


@whatsapp_bp.route('/webhook', methods=['POST'])
def webhook():
    """Public endpoint: everything is rejected or ignored unless Twilio signed it AND the sender is allowed"""
    if not wa.enabled():
        return _twiml()  # off: answer 200 so Twilio does not retry, do nothing

    form = request.form.to_dict(flat=True)
    if not wa.verify_signature(candidate_urls(), form, request.headers.get('X-Twilio-Signature', '')):
        logger.warning('WhatsApp webhook: invalid Twilio signature')
        return Response('Forbidden', status=403)

    phone = wa.normalize_phone(form.get('From'))
    if not wa.is_allowed(phone):
        logger.warning('WhatsApp webhook: sender not allowed (%s)', phone[-4:] or '?')
        return _twiml()

    # every message of an allowed number, instant answers included. It is bookkeeping: it runs next to the rest and is
    # joined before the response (AI_WHATSAPP_WEBHOOK_PARALLEL=false: sequential, as before)
    touching = None
    if wa.webhook_parallel():
        touching = wa.start_background(wa.touch_contact, get_db(), phone)
    else:
        wa.touch_contact(get_db(), phone)
    try:
        return _handle_allowed(form, phone)
    finally:
        wa.join_background(touching, timeout=3)


def _handle_allowed(form, phone):
    # "Ver" (the digest's button, or the word) is answered here too, from the detail saved when the digest went out
    from services import proactive_service
    detail = proactive_service.view_reply(get_db(), phone, form.get('ButtonPayload'), form.get('Body'))
    if detail:
        return _twiml(detail)

    # Greetings and "ayuda" are answered right here: no queue, no cold start, no model
    if not int(form.get('NumMedia') or 0):
        instant = wa.quick_reply(form.get('Body'))
        if instant:
            return _twiml(instant)

    db = get_db()
    message_sid = form.get('MessageSid') or form.get('SmsMessageSid')
    # "escribiendo…" goes out while the message is being stored (it only needs Twilio's sid): joined before answering
    # so the runtime cannot freeze it. AI_WHATSAPP_TYPING_ASYNC=false: old order (store first, then ask, sequentially)
    typing = wa.start_background(wa.send_typing, message_sid) if wa.typing_async() else None
    is_new = wa.store_inbound(db, form)
    if typing is not None:
        wa.join_background(typing)
    elif is_new:
        wa.send_typing(message_sid)
    mode = wa.processing_mode()
    if is_new and (mode == 'inline' or (mode == 'inline_text' and not int(form.get('NumMedia') or 0))):
        # No Firestore trigger available: answer inside this request (Twilio will time out at 15 s, but
        # the reply still goes out through the REST API as long as the function keeps running)
        from main import app
        process_inbox_message(app, form.get('MessageSid') or form.get('SmsMessageSid'))
    return _twiml()


# ---------- worker (production wiring of whatsapp_agent.process_inbox) ----------

def _send(phone, body):
    from services.whatsapp_service import TWILIO_WHATSAPP_FROM, twilio_client
    if twilio_client is None:
        raise RuntimeError('Twilio is not configured')
    twilio_client.messages.create(from_=TWILIO_WHATSAPP_FROM, to=f'whatsapp:{phone}', body=body)


def _download(url, max_bytes=None):
    """Twilio media needs basic auth (account SID + token); redirects to its CDN.
    `max_bytes` (default MAX_MEDIA_BYTES) caps what is read: a voice note is limited to what the STT accepts.
    Errors never carry the URL: it contains the Account SID and ends up in logs and in the inbox document."""
    limit = max_bytes or wa.MAX_MEDIA_BYTES
    try:
        response = requests.get(url, auth=(os.getenv('TWILIO_ACCOUNT_SID', ''), os.getenv('TWILIO_AUTH_TOKEN', '')),
                                timeout=20, stream=True)
        response.raise_for_status()
        data = response.raw.read(limit + 1, decode_content=True)
    except requests.RequestException as exc:
        raise RuntimeError(f'media download failed: {wa.safe_error(exc)}') from None
    if len(data) > limit:
        raise wa.MediaTooLarge('El archivo es demasiado grande')
    return data


def process_inbox_message(app, sid):
    """Run the assistant for one stored message inside a Flask context (it keeps per-request state in `g`)"""
    from routes import ai_chat_routes
    from services import keep_warm

    if keep_warm.is_warmup(sid):  # created by the scheduled keep-warm: load the SDK and go back to sleep
        keep_warm.prewarm()
        return 'warm'

    prefetched = {}

    def build_context():
        """Reference data for the agent: recent proposals (+ the situation snapshot when switched on). Never raises."""
        started = time.perf_counter()
        box, thread, activity = {}, None, ''
        try:  # the agent must still work without them
            db, now = get_db(), datetime.utcnow()
            if situation.enabled():   # its three small reads run next to the recent-activity one
                thread = wa.start_background(lambda: box.__setitem__('situation', situation.build(db, now)))
            activity = recent_activity.build(db, now)
        except Exception:  # noqa: BLE001
            logger.warning('Could not build the recent activity', exc_info=True)
            activity = ''
        wa.join_background(thread, timeout=5)
        return {'activity': activity, 'situation': box.get('situation') or '',
                'ms': round((time.perf_counter() - started) * 1000)}

    def prefetch():
        """Start reading that context while the worker does its own bookkeeping (quota, lock, conversation)"""
        if wa.prefetch_enabled() and 'thread' not in prefetched:
            prefetched['thread'] = wa.start_background(lambda: prefetched.__setitem__('data', build_context()))

    def run_chat(messages, user):
        wait_started = time.perf_counter()
        wa.join_background(prefetched.get('thread'), timeout=10)
        context = prefetched.get('data') or build_context()
        context_wait_ms = round((time.perf_counter() - wait_started) * 1000)
        with app.test_request_context():
            result = ai_chat_routes.run_chat(messages, user, channel='whatsapp', extra_system=context['activity'] or None,
                                             **({'situation': context['situation']} if context['situation'] else {}))
        result.setdefault('trace', {})['activity_ms'] = context_wait_ms     # time the turn waited for the context
        return result

    def transcribe(data, content_type):
        from services import speech_service  # lazy: only voice notes pay for it
        return speech_service.transcribe(data, content_type, phrases=speech_service.phrase_list(get_db()))

    deps = wa.Deps(send=_send, run_chat=run_chat, download_media=_download, typing=wa.send_typing, transcribe=transcribe,
                   prefetch=prefetch)
    status = wa.process_inbox(get_db(), sid, deps)
    logger.info('WhatsApp message %s: %s', sid, status)
    return status
