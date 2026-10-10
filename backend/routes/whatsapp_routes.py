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
from xml.sax.saxutils import escape as xml_escape

import requests
from flask import Blueprint, Response, request

from database import get_db
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

    # Greetings and "ayuda" are answered right here: no queue, no cold start, no model
    if not int(form.get('NumMedia') or 0):
        instant = wa.quick_reply(form.get('Body'))
        if instant:
            return _twiml(instant)

    db = get_db()
    is_new = wa.store_inbound(db, form)
    if is_new:
        wa.send_typing(form.get('MessageSid') or form.get('SmsMessageSid'))
    if is_new and wa.processing_mode() == 'inline':
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


def _download(url):
    """Twilio media needs basic auth (account SID + token); redirects to its CDN"""
    response = requests.get(url, auth=(os.getenv('TWILIO_ACCOUNT_SID', ''), os.getenv('TWILIO_AUTH_TOKEN', '')),
                            timeout=20, stream=True)
    response.raise_for_status()
    data = response.raw.read(wa.MAX_MEDIA_BYTES + 1, decode_content=True)
    if len(data) > wa.MAX_MEDIA_BYTES:
        raise ValueError('La imagen es demasiado grande')
    return data


def process_inbox_message(app, sid):
    """Run the assistant for one stored message inside a Flask context (it keeps per-request state in `g`)"""
    from routes import ai_chat_routes
    from services import keep_warm

    if keep_warm.is_warmup(sid):  # created by the scheduled keep-warm: load the SDK and go back to sleep
        keep_warm.prewarm()
        return 'warm'

    def run_chat(messages, user):
        with app.test_request_context():
            return ai_chat_routes.run_chat(messages, user, channel='whatsapp')

    deps = wa.Deps(send=_send, run_chat=run_chat, download_media=_download, typing=wa.send_typing)
    status = wa.process_inbox(get_db(), sid, deps)
    logger.info('WhatsApp message %s: %s', sid, status)
    return status
