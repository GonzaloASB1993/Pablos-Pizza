"""WhatsApp channel for the AI assistant: the same agent, the same propose -> confirm rule.

Flow (see routes/whatsapp_routes.py for the HTTP side):
  Twilio webhook  -> verify signature + allowlist -> store the message in `whatsapp_inbox` -> reply 200 at once
  Firestore trigger on `whatsapp_inbox/{sid}` -> process_inbox() -> agent -> reply through the Twilio API

Why a trigger: Twilio gives a webhook 15 s, an agent turn with a photo can take much longer, and a
serverless function must not keep working after it has answered.

Safety rules:
  * only numbers on the allowlist can talk to it (AI_WHATSAPP_ALLOWED, default: admin + partner numbers);
  * the agent still only PROPOSES. Nothing is written until the person answers SI to that proposal;
  * "SI"/"NO" are commands only while a proposal is pending, otherwise they are plain text for the agent;
  * Twilio retries and trigger redeliveries are idempotent (per MessageSid).
"""
import base64
import io
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from services import pending_actions_service as pending
from services import whatsapp_burst as burst
from services import undo_service  # also registers the `undo` action type, so a SI can confirm it
from services.ai_chat_history import ALLOWED_IMAGE_TYPES
from utils import clock
from utils.text_matching import normalize_text

logger = logging.getLogger(__name__)

INBOX = 'whatsapp_inbox'
CONVERSATIONS = 'whatsapp_conversations'
QUOTA = 'whatsapp_quota'
CONTACTS = 'whatsapp_contacts'  # per number: last message (24 h window), alert preferences, last confirmations



def _memory_hours():
    try:
        hours = float(os.getenv('AI_WHATSAPP_MEMORY_HOURS') or 24)
    except ValueError:
        hours = 24
    return hours if hours > 0 else 24


RESET_AFTER = timedelta(hours=_memory_hours())   # a conversation older than this starts fresh (AI_WHATSAPP_MEMORY_HOURS)
MAX_HISTORY = 16                     # text messages kept per conversation
MAX_MESSAGE_CHARS = 600              # per stored message
MAX_HISTORY_CHARS = 6000             # whole stored history
MAX_MEDIA_BYTES = 8 * 1024 * 1024
MAX_IMAGES = 3
CHUNK = 1400                         # Twilio's limit is 1600 characters per message
DEFAULT_DAILY_LIMIT = 100

RECEIVED, PROCESSING, DONE, FAILED, IGNORED = 'received', 'processing', 'done', 'failed', 'ignored'
MERGED = 'merged'                    # part of a burst answered by another worker (not an error, not counted in the quota)


class MediaTooLarge(ValueError):
    """A media file is heavier than the limit it was downloaded with"""


_URL = re.compile(r'https?://\S+')


def safe_error(exc):
    """An error text that can be stored: Twilio media URLs carry the Account SID, so any URL is cut out"""
    return _URL.sub('<url>', str(exc))[:300]


# ---------- configuration / identity ----------

def enabled():
    return os.getenv('AI_WHATSAPP_ENABLED', 'false').strip().lower() == 'true'


def processing_mode():
    """'trigger' (default, robust) or 'inline' (answer inside the webhook request)"""
    return os.getenv('AI_WHATSAPP_MODE', 'trigger').strip().lower()


def normalize_phone(raw):
    """'whatsapp:+56 9 1234 5678' -> '+56912345678'"""
    digits = re.sub(r'\D', '', str(raw or ''))
    return f'+{digits}' if digits else ''


def allowed_numbers():
    raw = os.getenv('AI_WHATSAPP_ALLOWED') or ','.join(
        [os.getenv('ADMIN_WHATSAPP_NUMBER', ''), os.getenv('PARTNER_WHATSAPP_NUMBER', '')])
    return {normalize_phone(n) for n in raw.split(',') if normalize_phone(n)}


def is_allowed(phone):
    return normalize_phone(phone) in allowed_numbers()


def user_for(phone):
    """Identity recorded in audits and `created_by` for things done through WhatsApp"""
    return {'uid': f'whatsapp:{phone}', 'email': f'whatsapp:{phone}'}


def verify_signature(candidate_urls, params, signature, auth_token=None):
    """Twilio signs (URL + sorted POST params) with the account token. Accept if any candidate URL matches
    (Cloud Run URL vs the hosting rewrite change the host Twilio signed)."""
    from twilio.request_validator import RequestValidator
    token = auth_token if auth_token is not None else os.getenv('TWILIO_AUTH_TOKEN', '')
    if not token or not signature:
        return False
    validator = RequestValidator(token)
    return any(validator.validate(url, params, signature) for url in candidate_urls if url)


# ---------- inbox ----------

def _is_audio(item):
    return (item.get('content_type') or '').split(';')[0].strip().lower().startswith('audio/')


def store_inbound(db, form, now=None):
    """Persist an incoming message once per MessageSid, and join it to the phone's open burst (see whatsapp_burst).
    One transaction: a Twilio retry of the same MessageSid neither duplicates the inbox doc nor appends to the burst twice.
    Returns True if it was new."""
    sid = form.get('MessageSid') or form.get('SmsMessageSid')
    if not sid:
        return False
    now = now or datetime.utcnow()
    ref = db.collection(INBOX).document(sid)
    phone = normalize_phone(form.get('From'))
    count = int(form.get('NumMedia') or 0)
    media = [{'url': form.get(f'MediaUrl{i}'), 'content_type': form.get(f'MediaContentType{i}')}
             for i in range(min(count, 10)) if form.get(f'MediaUrl{i}')]
    document = {
        'sid': sid, 'from': phone, 'body': (form.get('Body') or '')[:4000],
        'media': media, 'profile_name': form.get('ProfileName'), 'status': RECEIVED, 'created_at': now,
        'forwarded': str(form.get('Forwarded') or '').lower() == 'true',   # a forwarded message is never a command
        'button_payload': form.get('ButtonPayload') or None,                # quick-reply button tapped (e.g. "Ver")
    }
    transaction = db.transaction()

    @pending._transactional
    def run(txn):
        if ref.get(transaction=txn).exists:
            return False
        # photos open a burst (an album follows); a voice note alone does not, it only joins one that is already open
        burst_id = burst.join(db, txn, phone, sid, now, any(not _is_audio(m) for m in media))
        txn.set(ref, {**document, 'burst_id': burst_id})
        return True

    return run(transaction)


def touch_contact(db, phone, now=None):
    """Remember when this number last wrote to us: WhatsApp only allows free-form messages for 24 h after that.
    Called by the webhook for EVERY message of an allowed number (instant greetings included). Never raises."""
    try:
        now = now or datetime.utcnow()
        db.collection(CONTACTS).document(phone).set({'last_user_message_at': now, 'updated_at': now}, merge=True)
    except Exception as exc:  # noqa: BLE001 - bookkeeping must never block a message
        logger.warning('touch_contact failed: %s', exc)


def _claim(db, ref):
    """received -> processing, atomically, so a redelivered trigger or a Twilio retry runs once"""
    transaction = db.transaction()

    @pending._transactional
    def run(txn):
        snapshot = ref.get(transaction=txn)
        if not snapshot.exists:
            return None
        data = snapshot.to_dict()
        if data.get('status') != RECEIVED:
            return None
        txn.update(ref, {'status': PROCESSING, 'started_at': datetime.utcnow()})
        return data

    return run(transaction)


def _quota_ref(db, phone, now=None):
    """Today's counters of a phone. The day is Chile's (the server runs in UTC), the same one for messages and seconds."""
    return db.collection(QUOTA).document(f"{phone}_{clock.today_cl(now):%Y%m%d}")


def _within_quota(db, phone, cost=1, now=None):
    """Charge `cost` messages (a burst of N counts N) against today's limit, atomically (server-side Increment).
    Refuses when the limit was already used up."""
    from google.cloud import firestore
    limit = int(os.getenv('AI_WHATSAPP_DAILY_LIMIT', DEFAULT_DAILY_LIMIT))
    ref = _quota_ref(db, phone, now)
    cost = max(1, int(cost or 1))
    transaction = db.transaction()

    @pending._transactional
    def run(txn):
        snapshot = ref.get(transaction=txn)
        used = (snapshot.to_dict() or {}).get('count', 0) if snapshot.exists else 0
        if (used or 0) >= limit:
            return False
        # merge: keeps stt_seconds
        txn.set(ref, {'phone': phone, 'count': firestore.Increment(cost), 'updated_at': now or datetime.utcnow()}, merge=True)
        return True

    return run(transaction)


# ---------- voice notes: daily cap of transcribed seconds ----------

AUDIO_TYPES = {'audio/ogg', 'audio/opus', 'audio/mpeg', 'audio/mp4', 'audio/aac', 'audio/amr'}
DEFAULT_STT_DAILY_SECONDS = 900
MIN_VOICE_COMMAND_CONFIDENCE = 0.85     # a spoken SI / NO confirms only at or above this (unknown also passes)
ECHO_BELOW_CONFIDENCE = 0.80            # below this we show what we understood, even for a plain question


def stt_daily_limit():
    return int(os.getenv('AI_WHATSAPP_STT_DAILY_SECONDS', DEFAULT_STT_DAILY_SECONDS))


def _stt_within_cap(db, phone, now=None):
    snapshot = _quota_ref(db, phone, now).get()
    used = (snapshot.to_dict() or {}).get('stt_seconds', 0) if snapshot.exists else 0
    return (used or 0) < stt_daily_limit()


def _stt_charge(db, phone, seconds, now=None):
    """Add the seconds to today's counter: one blind set(merge) with a server-side Increment (no read, so concurrent
    notes neither lose counts nor race between "exists?" and "write")"""
    from google.cloud import firestore
    value = round(float(seconds or 0), 1)
    _quota_ref(db, phone, now).set(
        {'phone': phone, 'stt_seconds': firestore.Increment(value), 'updated_at': now or datetime.utcnow()}, merge=True)


# ---------- conversation state ----------

def _load_conversation(db, phone, now):
    snapshot = db.collection(CONVERSATIONS).document(phone).get()
    conv = snapshot.to_dict() if snapshot.exists else {}
    last = conv.get('last_inbound_at')
    if last is not None and getattr(last, 'tzinfo', None) is not None:
        last = last.replace(tzinfo=None)
    if not conv or last is None or now - last > RESET_AFTER:
        return {'history': [], 'pending': [], 'choices': []}
    return {'history': trim_history(conv.get('history', [])), 'pending': conv.get('pending', []),
            'choices': conv.get('choices', [])}


def compact_message(text, markers=()):
    """Fit a message in MAX_MESSAGE_CHARS without losing the proposal summary ("📋 ...") nor the "✅ ..." lines.
    `markers` ("[Propuesta 1: ...]") are appended only when the full text did not fit."""
    text = text or ''
    if len(text) <= MAX_MESSAGE_CHARS:
        return text
    keep = [line[:200] for line in text.split('\n') if line.startswith(('📋', '✅'))]
    notes = [m[:120] for m in markers]
    reserved = sum(len(line) + 1 for line in keep + notes)
    budget = max(0, MAX_MESSAGE_CHARS - reserved - 40)  # room for the line breaks and the "…" lines
    out, used = [], 0
    for line in text.split('\n'):
        if line.startswith(('📋', '✅')):
            out.append(line[:200])
        elif used < budget and line.strip():
            piece = line[:budget - used]
            out.append(piece + ('…' if len(piece) < len(line) else ''))
            used += len(piece)
        elif line.strip() and out[-1:] != ['…']:
            out.append('…')
    result = '\n'.join(out + notes)
    if len(result) > MAX_MESSAGE_CHARS:  # many proposals: summaries first, then the markers, cut at the end
        result = '\n'.join(keep + notes)[:MAX_MESSAGE_CHARS]
    return result


def trim_history(history):
    """Bounded history: <= MAX_HISTORY messages, <= MAX_MESSAGE_CHARS each, <= MAX_HISTORY_CHARS in total.
    Oldest user/assistant pairs go first and it always starts with a `user` message."""
    items = [{'role': m['role'], 'content': compact_message(m['content'])} for m in history
             if isinstance(m.get('content'), str)]
    while items and (len(items) > MAX_HISTORY or sum(len(m['content']) for m in items) > MAX_HISTORY_CHARS
                     or items[0]['role'] != 'user'):
        del items[:1 if items[0]['role'] != 'user' else 2]
    return items


def _save_conversation(db, phone, conv, now):
    db.collection(CONVERSATIONS).document(phone).set({
        'history': trim_history(conv['history']), 'pending': conv['pending'], 'choices': conv['choices'],
        'last_inbound_at': now, 'updated_at': now,
    }, merge=True)  # merge: a field another feature adds to this document must survive the next turn


# ---------- text helpers ----------

YES_WORDS = {'si', 'sii', 'confirmo', 'confirmar', 'confirma', 'dale', 'ok', 'okey', 'listo', 'correcto'}
NO_WORDS = {'no', 'cancelar', 'cancela', 'cancelo', 'anular'}
_COMMAND = re.compile(r'^(?P<word>[a-z]+)(?:\s+(?P<which>\d+|todas|todo|todos))?$')


def parse_command(text):
    """('yes'|'no', which) for a bare SI / NO (optionally 'SI 2' / 'NO todas'); None for anything else"""
    cleaned = normalize_text(re.sub(r'[^\w\s]', ' ', text or '')).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    match = _COMMAND.match(cleaned)
    if not match:
        return None
    word, which = match.group('word'), match.group('which')
    kind = 'yes' if word in YES_WORDS else 'no' if word in NO_WORDS else None
    if not kind:
        return None
    return kind, ('all' if which in ('todas', 'todo', 'todos') else int(which) if which else None)


def to_whatsapp(markdown):
    """Chat markdown -> what WhatsApp renders (*bold*, bullets, no tables / headings / code fences)"""
    text = markdown or ''
    text = re.sub(r'```.*?```', lambda m: m.group(0).strip('`').strip(), text, flags=re.S)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'\1 (\2)', text)
    text = re.sub(r'^#{1,6}\s*(.+?)\s*$', r'*\1*', text, flags=re.M)
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.M)
    lines = []
    for line in text.split('\n'):
        if re.match(r'^\s*\|?\s*:?-{2,}', line) and '|' in line:
            continue  # table separator
        if line.strip().startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            line = ' — '.join(c for c in cells if c)
        lines.append(line.rstrip())
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def chunks(text, size=CHUNK):
    """Split at paragraph / line boundaries so every message fits in Twilio's limit"""
    parts, current = [], ''
    for paragraph in text.split('\n\n'):
        candidate = f'{current}\n\n{paragraph}' if current else paragraph
        if len(candidate) <= size:
            current = candidate
            continue
        if current:
            parts.append(current)
        while len(paragraph) > size:
            cut = paragraph.rfind('\n', 0, size)
            cut = cut if cut > size // 2 else paragraph.rfind(' ', 0, size)
            cut = cut if cut > 0 else size
            parts.append(paragraph[:cut].rstrip())
            paragraph = paragraph[cut:].lstrip()
        current = paragraph
    if current:
        parts.append(current)
    return parts or ['']


def compress_image(data, max_side=1600, quality=80):
    """Twilio hands over the original photo: resize and re-encode it like the web chat does"""
    from PIL import Image, ImageOps
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert('RGB')
    image.thumbnail((max_side, max_side))
    out = io.BytesIO()
    image.save(out, 'JPEG', quality=quality)
    return out.getvalue()


# ---------- instant replies (no model, no cold start) ----------

GREETING = '¡Hola! Soy Pablito 🍕 ¿En qué te ayudo?'
HELP = ('Puedo ayudarte con:\n• Anotar gastos y compras: mándame la foto de la boleta\n'
        '• Insumos de un evento\n• Agendar reservas\n• Ver eventos, inventario y finanzas\n\n'
        'Escríbeme normal, como a una persona.')
GREETING_WORDS = {'hola', 'holi', 'holis', 'ola', 'wena', 'wenas', 'buenas', 'buen dia', 'buenos dias', 'buenas tardes',
                  'buenas noches', 'hey', 'hello', 'que tal', 'pablito', 'hola pablito', 'wena pablito', 'buenas pablito'}
HELP_WORDS = {'ayuda', 'menu', 'opciones', 'que puedes hacer', 'que haces', 'para que sirves'}


def quick_reply(text):
    """Answer greetings and 'ayuda' on the spot (the webhook replies with it: well under a second)"""
    cleaned = re.sub(r'\s+', ' ', normalize_text(re.sub(r'[^\w\s]', ' ', text or ''))).strip()
    if cleaned in GREETING_WORDS:
        return GREETING
    if cleaned in HELP_WORDS:
        return HELP
    return None


def send_typing(message_sid):
    """Show "escribiendo…" (and the blue ticks) while the answer is prepared. Twilio public beta: best effort."""
    if os.getenv('AI_WHATSAPP_TYPING', 'true').strip().lower() == 'false' or not message_sid:
        return False
    try:
        import requests
        response = requests.post(
            'https://messaging.twilio.com/v2/Indicators/Typing.json',
            data={'messageId': message_sid, 'channel': 'whatsapp'},
            auth=(os.getenv('TWILIO_ACCOUNT_SID', ''), os.getenv('TWILIO_AUTH_TOKEN', '')), timeout=1.5)
        if not response.ok:
            logger.warning('Typing indicator not accepted (HTTP %s)', response.status_code)
        return response.ok
    except Exception as exc:  # noqa: BLE001 - never let a cosmetic call break the message
        logger.warning('Typing indicator failed: %s', exc)
        return False


# ---------- describing proposals in plain text (short: it is read at a glance) ----------

def _clp(n):
    return '$' + f'{round(n or 0):,}'.replace(',', '.')


# On WhatsApp there is no card: the SI is given looking only at this message. So the rule fails SAFE: every warning is
# shown (most important first, at most 2, the rest counted) except the ones known to be harmless noise.
# Exact phrases on purpose: "la detección de duplicados es menos confiable" must not match "posible duplicado".
IMPORTANT_WARNINGS = ('posible duplicado', 'no cuadra', 'insuficiente', 'no hay stock', 'reemplaza', 'ese día ya hay',
                      'ya pasó', 'difiere', 'no coincide', 'volvió más', 'se parece a', 'fecha del documento',
                      'comuna lejana', 'mayor al 50')
HARMLESS_WARNINGS = ('crédito fiscal', 'mínimo y máximo en 0', 'al confirmar se avisa', 'el cliente no recibe nada',
                     'se vinculará', 'otros gastos del evento en $0', 'sin folio', 'se cobra el mínimo')
MAX_LINES = 4


def key_warnings(warnings, limit=2):
    ranked = []
    for position, warning in enumerate(warnings or []):
        low = warning.lower()
        if any(k in low for k in HARMLESS_WARNINGS):
            continue
        hits = [i for i, key in enumerate(IMPORTANT_WARNINGS) if key in low]
        ranked.append((min(hits) if hits else len(IMPORTANT_WARNINGS), position, warning))
    chosen = [w if len(w) <= 170 else w[:167] + '…' for _, _, w in sorted(ranked)[:limit]]
    if len(ranked) > limit:
        chosen.append(f'+{len(ranked) - limit} aviso(s) más: míralos en el panel')
    return chosen


def short_text(text, limit=220):
    """The agent's own words next to a proposal: keep the first thought only"""
    paragraphs = [p.strip() for p in (text or '').strip().split('\n\n') if p.strip()]
    if not paragraphs:
        return ''
    first = paragraphs[0]
    if len(first) > limit:
        cut = max(first.rfind('. ', 0, limit), first.rfind('? ', 0, limit), first.rfind('! ', 0, limit))
        first = first[:cut + 1] if cut > 40 else first[:limit - 1].rstrip() + '…'
    # a question that comes later ("¿es factura o boleta?") is information the person needs: keep it
    questions = [p for p in paragraphs[1:] if p.endswith('?') and len(p) <= limit]
    return '\n\n'.join([first] + questions[:1])


def _more(lines, label_count):
    return lines[:MAX_LINES] + ([f'… y {label_count - MAX_LINES} más (detalle en el panel)'] if label_count > MAX_LINES else [])


def describe_action(action, number=None):
    """What the web card shows, in a few WhatsApp lines"""
    prefix = '📋 ' if number is None else f'📋 *{number}*: '
    lines = [prefix + action['summary']]
    payload, ctx = action.get('payload', {}), action.get('context', {}) or {}
    detail = []
    if action['type'] == 'inventory_receipt':
        for line in payload.get('lines', []):
            kind = {'existing': '', 'new': ' (nuevo)', 'expense': ' (gasto)'}[line['classification']]
            qty = f" {line['quantity']:g} {line.get('unit') or ''}".rstrip() if line.get('quantity') else ''
            name = line.get('name') or ctx.get('items', {}).get(line.get('item_id'), {}).get('name') or line['description']
            detail.append(f"• {name}:{qty} {_clp(line['amount'])}{kind}")
        lines += _more(detail, len(detail))
    elif action['type'] in ('event_supplies', 'event_consumption'):
        for row in ctx.get('rows', []):
            qty = row.get('actual_quantity_consumed') if action['type'] == 'event_consumption' else None
            if qty is None:
                item = next((i for i in payload.get('items', []) if i['item_id'] == row['item_id']), {})
                qty = item.get('estimated_quantity')
            detail.append(f"• {row['item_name']}: {qty:g} {row['unit']}")
        lines += _more(detail, len(detail))
    lines += [f'⚠️ {w}' for w in key_warnings(action.get('warnings'))]
    return '\n'.join(lines)


def proposals_message(actions):
    parts = [describe_action(a, number=i if len(actions) > 1 else None) for i, a in enumerate(actions, start=1)]
    if len(actions) == 1:
        parts.append('¿La guardo? *SI* / *NO*')
    else:
        parts.append('¿Cuál guardo? *SI 1*, *SI 2*, *SI todas* o *NO*')
    return '\n\n'.join(parts)


def result_message(action):
    """One line after a SI"""
    result, payload, kind = action.get('result') or {}, action.get('payload') or {}, action['type']
    if kind == 'expense':
        return f"✅ Guardado: {payload.get('supplier', 'gasto')} {_clp(payload.get('total'))}."
    if kind == 'booking':
        return '✅ Reserva creada (pendiente). Confírmala en el panel: ahí se avisa al cliente.'
    if kind == 'event_consumption':
        return f"✅ Consumo guardado ({_clp(result.get('total_cost'))}). Stock descontado."
    if kind == 'event_supplies':
        return f"✅ Insumos del evento guardados ({_clp(result.get('estimated_total_cost'))})."
    if kind == 'inventory_receipt':
        return f"✅ Compra guardada: {result.get('inventory_lines', 0)} a inventario, {result.get('expense_lines', 0)} a gastos."
    if kind == 'undo':
        if result.get('already_undone'):
            return '↩️ Eso ya estaba deshecho.'
        return ' '.join([f"↩️ Listo, deshice *{result.get('label') or 'eso'}*."] + list(result.get('warnings') or []))
    return '✅ Listo.'


# ---------- the worker ----------

class Deps:
    """What process_inbox needs from the outside world (replaced by fakes in tests)"""

    def __init__(self, send, run_chat, download_media, now=None, typing=None, transcribe=None, sleep=None):
        self.send, self.run_chat, self.download_media = send, run_chat, download_media
        self.transcribe = transcribe  # optional: (bytes, content_type) -> {'text', 'confidence', 'seconds'}; None = no voice notes
        self.now = now or datetime.utcnow
        self.sleep = sleep or time.sleep  # burst leader / lock waits (a fake clock in tests)
        self.typing = typing  # optional: show "escribiendo…" (called again here: a cold start can eat the first 25 s)


def _reply(deps, phone, text):
    for part in chunks(text):
        deps.send(phone, part)


def _live_pending(db, conv):
    """[(number, action)] of this conversation's proposals that can still be confirmed"""
    live = []
    for entry in conv.get('pending', []):
        try:
            action = pending.get(db, entry['id'])
        except pending.PendingActionError:
            continue
        if action['status'] in (pending.PENDING, pending.FAILED):
            live.append((entry['n'], action))
    return live


def _safe_reply(deps, phone, text):
    """Answer a command whose effect is already decided/saved: if WhatsApp refuses the message the work is NOT undone,
    so the failure is only logged (the caller must not turn it into "no pude procesar tu mensaje")"""
    try:
        _reply(deps, phone, text)
    except Exception:  # noqa: BLE001
        logger.error('Sending the answer to a command failed (what it did stays done)', exc_info=True)


NEWER_PROPOSAL = 'Te llegó una propuesta nueva, revísala y responde SI.'


def _handle_command(db, deps, phone, user, conv, kind, which, created_at=None):
    """Handle a bare SI / NO. Returns the text it answered with, or None when it was not a command after all
    (no proposal is waiting): then the agent reads it as normal text.
    `created_at` is when the person WROTE the command: a proposal created after that moment was never seen by them
    (a turn that ran first, while this one waited for the lock, replaced the one they answered), so it is not touched."""
    live = _live_pending(db, conv)
    if not live:
        return None
    if which is None and len(live) > 1:
        text = ('Tengo varias propuestas pendientes. Responde *SI 1*, *SI 2*… o *SI todas* '
                '(o *NO 1*, *NO todas* para cancelar).')
        _safe_reply(deps, phone, text)
        return text
    chosen = live if which in (None, 'all') else [(n, a) for n, a in live if n == which]
    if not chosen:
        text = f'No encuentro la propuesta {which}. Pendientes: ' + ', '.join(str(n) for n, _ in live) + '.'
        _safe_reply(deps, phone, text)
        return text
    if created_at is not None and any(
            action.get('created_at') and pending._naive_utc(action['created_at']) > created_at for _, action in chosen):
        _safe_reply(deps, phone, NEWER_PROPOSAL)
        return NEWER_PROPOSAL

    replies, confirmed_now = [], []
    for number, action in chosen:
        label = f'Propuesta {number}: ' if len(live) > 1 else ''
        try:
            if kind == 'yes':
                done = pending.confirm(db, action['id'], user)
                replies.append(label + result_message(done))
                if done.get('type') != undo_service.UNDO_TYPE:   # an undo cannot be undone: it is never "the last thing"
                    confirmed_now.append({'id': action['id'], 'n': number, 'at': deps.now()})
            else:
                pending.cancel(db, action['id'])
                replies.append(f"{label}❌ Cancelada. No se guardó nada.")
        except pending.ActionExpired:
            replies.append(f'{label}⌛ Esa propuesta expiró. Pídemela de nuevo.')
        except pending.PendingActionError as exc:
            replies.append(f'{label}No pude hacerlo: {exc}')
        except Exception:  # noqa: BLE001
            logger.error('Confirming a proposal from WhatsApp failed', exc_info=True)
            replies.append(f'{label}⚠️ No se pudo guardar. Puedes responder SI para reintentar.')
    conv['pending'] = [{'id': a['id'], 'n': n} for n, a in _live_pending(db, conv)]  # only what can still be confirmed
    if confirmed_now:
        _remember_confirmed(db, phone, confirmed_now, deps.now())
    text = '\n'.join(replies)
    _safe_reply(deps, phone, text)
    return text


def _remember_confirmed(db, phone, confirmed, now):
    """What this SI just saved: "deshacer" works on it. Replaces the previous batch ("lo último"). Never raises."""
    try:
        db.collection(CONTACTS).document(phone).set({'last_confirmed': confirmed, 'updated_at': now}, merge=True)
    except Exception as exc:  # noqa: BLE001 - bookkeeping must never turn a saved action into an error
        logger.warning('remembering last_confirmed failed: %s', exc)


# ---------- pipeline: claim -> gather -> commands -> agent ----------

@dataclass
class Inbound:
    """Everything the person sent in one go (one message today; a whole burst of photos/notes later)"""
    phone: str
    sids: list
    text: str = ''
    image_blocks: list = field(default_factory=list)
    transcripts: list = field(default_factory=list)    # voice notes, already transcribed
    unsupported: bool = False
    forwarded: bool = False
    button_payload: str = None
    notice: str = ''                                   # shown before the answer (e.g. "I only read the first 3 photos")
    stt_confidence: float = None       # weakest known confidence among the notes (None = unknown)
    audio_seconds: float = 0.0
    audio_empty: bool = False          # a note could not be understood (empty / failed transcription)
    audio_too_long: bool = False
    audio_capped: bool = False         # today's cap of transcribed seconds is used up
    created_at: datetime = None        # when the person wrote it (the oldest message of a burst); None = unknown

    @property
    def has_voice(self):
        return bool(self.transcripts)

    def agent_text(self, typed=None):
        """What the agent reads: the typed text plus every voice note, in order, labelled as such"""
        typed = self.text if typed is None else typed
        return '\n'.join([t for t in [typed] if t] + [f'(nota de voz) {t}' for t in self.transcripts])

    def history_text(self, typed=None):
        typed = self.text if typed is None else typed
        return '\n'.join([t for t in [typed] if t] + [f'🎤 {t}' for t in self.transcripts])


@dataclass
class Ctx:
    """What a command handler needs"""
    db: object
    deps: object
    phone: str
    user: dict
    conv: dict
    inbound: Inbound
    now: datetime


def _gather_voice(db, deps, inbound, item, content_type):
    """Download one voice note, transcribe it and keep ONLY the text: the audio is never stored nor logged"""
    from services import speech_service
    now = deps.now()
    if not _stt_within_cap(db, inbound.phone, now):
        inbound.audio_capped = True
        return
    try:
        data = deps.download_media(item['url'], max_bytes=speech_service.MAX_BYTES)
    except MediaTooLarge:
        inbound.audio_too_long = True
        return
    try:
        result = deps.transcribe(data, content_type)
    except speech_service.AudioTooLong:
        inbound.audio_too_long = True
        return
    except Exception as exc:  # noqa: BLE001 - say only what failed, never the audio
        logger.warning('Voice note could not be transcribed: %s', safe_error(exc))
        inbound.audio_empty = True
        # it did reach Google (and may have been billed): a failing API must not be a free, unlimited retry loop
        try:
            _stt_charge(db, inbound.phone, max(speech_service.estimate_seconds(data, content_type),
                                               speech_service.MIN_CHARGE_SECONDS), now)
        except Exception:  # noqa: BLE001 - bookkeeping
            logger.warning('Charging a failed transcription failed', exc_info=True)
        return
    finally:
        del data
    seconds = float(result.get('seconds') or 0)
    inbound.audio_seconds += seconds
    _stt_charge(db, inbound.phone, seconds, now)
    text = (result.get('text') or '').strip()
    if not text:
        inbound.audio_empty = True
        return
    inbound.transcripts.append(text)
    confidence = result.get('confidence')
    if confidence:
        inbound.stt_confidence = confidence if inbound.stt_confidence is None else min(inbound.stt_confidence, confidence)


def echo_line(text):
    """'Entendi': one short line with what was heard (at most 100 characters)"""
    text = ' '.join((text or '').split())
    room = 100 - len('🎤 _""_')
    if len(text) > room:
        text = text[:room - 1].rstrip() + '…'
    return f'🎤 _"{text}"_'


def _gather(db, deps, messages, timings=None):
    """Collect the text and the photos of one or several stored messages into a single Inbound"""
    started = time.perf_counter()
    inbound = Inbound(phone=messages[0]['from'], sids=[m.get('sid') for m in messages])
    texts = []
    for message in messages:
        body = (message.get('body') or '').strip()
        if body:
            texts.append(body)
        inbound.forwarded = inbound.forwarded or bool(message.get('forwarded'))
        inbound.button_payload = message.get('button_payload') or inbound.button_payload
        for item in message.get('media', [])[:MAX_IMAGES + 2]:
            content_type = (item.get('content_type') or '').split(';')[0].strip().lower()
            if content_type in ALLOWED_IMAGE_TYPES and len(inbound.image_blocks) < MAX_IMAGES:
                data = compress_image(deps.download_media(item['url']))
                inbound.image_blocks.append({'type': 'image', 'source': {
                    'type': 'base64', 'media_type': 'image/jpeg', 'data': base64.b64encode(data).decode()}})
            elif content_type in AUDIO_TYPES and deps.transcribe:
                _gather_voice(db, deps, inbound, item, content_type)
            else:
                inbound.unsupported = True
    inbound.text = '\n'.join(texts)
    stamps = [pending._naive_utc(m['created_at']) for m in messages if m.get('created_at')]
    inbound.created_at = min(stamps) if stamps else None
    if timings is not None:
        timings['media_ms'] = round((time.perf_counter() - started) * 1000)
    return inbound


# Deterministic commands (no model). Each feature adds one (matcher, handler):
#   matcher(ctx) -> anything truthy/non-None when the message is for this handler
#   handler(ctx, matched) -> the text it answered with, or None to let the next one / the agent take it
COMMAND_HANDLERS = []


VOICE_UNSURE = ('unsure',)             # a spoken SI / NO that is not trusted enough to act on
ASK_WRITTEN = 'No te escuché bien, ¿me lo confirmas escrito? *SI* / *NO*'


def voice_confirm_enabled():
    """AI_WHATSAPP_VOICE_CONFIRM=false: a spoken SI / NO never confirms or cancels (typed only)"""
    return os.getenv('AI_WHATSAPP_VOICE_CONFIRM', 'true').strip().lower() != 'false'


def _single_note(inbound):
    """The transcript when ONE voice note is the whole message, else None"""
    if inbound.text or len(inbound.transcripts) != 1:
        return None
    return inbound.transcripts[0]


def _match_confirm(ctx):
    """A bare SI / NO (a photo with it is a new request, not an answer). Never from a forwarded text.
    By voice only when ONE note is the whole message, the transcript is exactly a SI / NO, it is not forwarded, the
    switch is on and the recognizer is sure enough (or does not say): a misheard word must not confirm anything.
    A spoken SI / NO that fails one of those is VOICE_UNSURE: with proposals waiting we ask for it in writing."""
    inbound = ctx.inbound
    if inbound.image_blocks:
        return None
    if inbound.has_voice:
        transcript = _single_note(inbound)
        command = parse_command(transcript) if transcript else None
        if command is None:
            return None
        sure = (not inbound.forwarded and voice_confirm_enabled()
                and (inbound.stt_confidence is None or inbound.stt_confidence >= MIN_VOICE_COMMAND_CONFIDENCE))
        return command if sure else VOICE_UNSURE
    if inbound.forwarded:
        return None
    return parse_command(inbound.text)


def _run_confirm(ctx, command):
    if command == VOICE_UNSURE:
        if not _live_pending(ctx.db, ctx.conv):
            return None            # nothing to confirm: it is just a word for the agent
        _safe_reply(ctx.deps, ctx.phone, ASK_WRITTEN)
        return ASK_WRITTEN
    if ctx.inbound.has_voice and ctx.conv.get('pending'):
        _safe_reply(ctx.deps, ctx.phone, echo_line(ctx.inbound.transcripts[0]))  # show what was heard before acting on it
    answered = _handle_command(ctx.db, ctx.deps, ctx.phone, ctx.user, ctx.conv, *command, created_at=ctx.inbound.created_at)
    if answered is None and ctx.conv.get('pending'):
        # the proposal was resolved elsewhere (web panel) or replaced: do not hand a bare "SI" to the model
        answered = 'Esa propuesta ya no está pendiente (se confirmó, canceló o venció). ¿Qué necesitas?'
        ctx.conv['pending'] = []
        _safe_reply(ctx.deps, ctx.phone, answered)
    return answered


COMMAND_HANDLERS.append((_match_confirm, _run_confirm))


# ---------- alert preferences (personal settings, applied straight away: they are not business data) ----------

_MUTE_TYPE = re.compile(r'^silencia(?:r)? (?P<what>stock|inventario|reservas?|eventos?|propuestas?)$')
_MUTE_NUMBER = re.compile(r'^silencia(?:r)? (?P<n>\d{1,2})$')
_MUTE_ALL = re.compile(r'^(?:silencia(?:r)? (?:todo|todos|todas)|pausa(?:r)? (?:los )?avisos)$')
_UNMUTE = re.compile(r'^(?:avisame de nuevo|(?:activa|reactiva)(?:r)? (?:los )?avisos)$')
_STATUS = re.compile(r'^avisos$')
_GROUP_ALIASES = {'stock': 'stock', 'inventario': 'stock', 'reserva': 'reservas', 'reservas': 'reservas',
                  'evento': 'eventos', 'eventos': 'eventos', 'propuesta': 'propuestas', 'propuestas': 'propuestas'}
_GROUP_NAMES = {'stock': 'stock bajo', 'reservas': 'reservas por confirmar', 'eventos': 'eventos de mañana',
                'propuestas': 'propuestas sin responder'}


def _match_alert_prefs(ctx):
    """('mute_type', group) | ('mute_n', n) | ('mute_all', None) | ('unmute', None) | ('status', None) | None.
    Never for forwarded messages or messages with photos."""
    if ctx.inbound.image_blocks or ctx.inbound.forwarded or ctx.inbound.has_voice:   # typed text only
        return None
    text = re.sub(r'\s+', ' ', normalize_text(re.sub(r'[^\w\s]', ' ', ctx.inbound.text or ''))).strip()
    for pattern, kind in ((_MUTE_TYPE, 'mute_type'), (_MUTE_NUMBER, 'mute_n')):
        match = pattern.match(text)
        if match:
            value = match.groupdict().get('what') or match.groupdict().get('n')
            return kind, _GROUP_ALIASES[value] if kind == 'mute_type' else int(value)
    if _MUTE_ALL.match(text):
        return 'mute_all', None
    if _UNMUTE.match(text):
        return 'unmute', None
    return ('status', None) if _STATUS.match(text) else None


def _save_prefs(db, phone, prefs, now):
    db.collection(CONTACTS).document(phone).set({'alert_prefs': prefs, 'updated_at': now}, merge=True)


def _prefs_summary(prefs):
    from services import alerts_service   # imported here: keeps the worker's cold start light
    if prefs.get('paused'):
        return '🔕 Avisos en pausa. Para volver: *avísame de nuevo*.'
    muted = [_GROUP_NAMES[g] for g, types in alerts_service.TYPE_GROUPS.items()
             if types[0] in (prefs.get('muted_types') or [])]
    extra = len(prefs.get('muted_keys') or {})
    if not muted and not extra:
        return '🔔 Avisos activos: te mando un resumen a las 10:00 solo si hay algo nuevo. Para callar algo: *silenciar stock*.'
    lines = ['🔔 Avisos activos, con esto silenciado:']
    lines += [f'• {name}' for name in muted]
    if extra:
        lines.append(f'• {extra} aviso(s) puntual(es)')
    lines.append('Para volver a todo: *avísame de nuevo*.')
    return '\n'.join(lines)


def _run_alert_prefs(ctx, matched):
    from services import alerts_service
    kind, value = matched
    db, phone = ctx.db, ctx.phone
    prefs = alerts_service.get_prefs(db, phone)
    if kind == 'mute_type':
        muted = list(prefs.get('muted_types') or [])
        muted += [t for t in alerts_service.TYPE_GROUPS[value] if t not in muted]
        prefs['muted_types'] = muted
        text = f'🔕 Listo, no te aviso más de {_GROUP_NAMES[value]}. Para volver: *avísame de nuevo*.'
    elif kind == 'mute_n':
        from services import proactive_service
        digest = proactive_service.last_digest(db, phone, ctx.now)
        items = (digest or {}).get('items') or []
        if not 1 <= value <= len(items):
            text = ('No encuentro ese número en el último resumen. Prueba con *ver* para repasarlo, '
                    'o con *silenciar stock* / *reservas* / *eventos* / *propuestas*.')
            _reply(ctx.deps, phone, text)
            return text
        keys = dict(prefs.get('muted_keys') or {})
        keys[items[value - 1]] = ctx.now.isoformat()
        prefs['muted_keys'] = keys
        label = ((digest.get('labels') or [])[value - 1:value] or ['ese aviso'])[0]
        text = f'🔕 Listo, no te aviso más de *{label}*.'
    elif kind == 'mute_all':
        prefs['paused'] = True
        text = '🔕 Avisos en pausa. Para volver: *avísame de nuevo*.'
    elif kind == 'unmute':
        prefs = alerts_service.default_prefs()
        text = '🔔 Listo, vuelvo a avisarte de todo (un resumen al día, solo si hay algo nuevo).'
    else:
        text = _prefs_summary(prefs)
        _reply(ctx.deps, phone, text)
        return text
    _save_prefs(db, phone, prefs, ctx.now)
    _reply(ctx.deps, phone, text)
    return text


COMMAND_HANDLERS.append((_match_alert_prefs, _run_alert_prefs))


# ---------- "deshacer": undo what a SI just saved (propose -> confirm, exact or not at all) ----------

_UNDO = re.compile(r'^(?:deshacer|deshaz|deshace|revertir)(?:\s+(?:lo\s+ultimo|ultimo|eso|esto|lo))?'
                   r'(?:\s+(?P<which>\d+|todas|todo|todos))?$')
NOTHING_TO_UNDO = ('No tengo nada reciente que deshacer. Solo puedo deshacer lo que confirmaste por aquí '
                   'en las últimas 24 horas.')


def parse_undo(text):
    """(which,) for "deshacer" / "deshaz 2" / "revertir todas"; None for anything else"""
    cleaned = re.sub(r'\s+', ' ', normalize_text(re.sub(r'[^\w\s]', ' ', text or ''))).strip()
    match = _UNDO.match(cleaned)
    if not match:
        return None
    which = match.group('which')
    return ('all' if which in ('todas', 'todo', 'todos') else int(which) if which else None,)


def _match_undo(ctx):
    """A bare command; a photo or a forwarded message with those words is not an order. By voice only when ONE clear
    note is the whole message (it only PROPOSES the undo: the SI that follows is what does it)"""
    inbound = ctx.inbound
    if inbound.image_blocks or inbound.forwarded:
        return None
    if inbound.has_voice:
        transcript = _single_note(inbound)
        if not transcript or (inbound.stt_confidence is not None and inbound.stt_confidence < MIN_VOICE_COMMAND_CONFIDENCE):
            return None
        return parse_undo(transcript)
    return parse_undo(inbound.text)


def _undoable(ctx):
    """[(n, action)] of what the last SI saved and has not been undone yet"""
    snapshot = ctx.db.collection(CONTACTS).document(ctx.phone).get()
    entries = (snapshot.to_dict() or {}).get('last_confirmed') or [] if snapshot.exists else []
    found = []
    for entry in entries:
        try:
            action = pending.get(ctx.db, entry['id'])
        except pending.PendingActionError:
            continue
        if action.get('type') == undo_service.UNDO_TYPE or (action.get('undo') or {}).get('state') == 'done':
            continue
        found.append((entry.get('n') or 1, action))
    return sorted(found, key=lambda pair: pair[0])


def _run_undo(ctx, matched):
    (which,) = matched
    candidates = _undoable(ctx)
    if not candidates:
        text = NOTHING_TO_UNDO
        if _live_pending(ctx.db, ctx.conv):
            text += ' Si hablas de la propuesta que está esperando, responde *NO*.'
        _reply(ctx.deps, ctx.phone, text)
        return text
    listing = '\n'.join(f'*{n}*: {undo_service.label(a)}' for n, a in candidates)
    if which is None and len(candidates) > 1:
        text = f'Confirmaste varias cosas:\n{listing}\nDime *deshacer 1*, *deshacer 2*… o *deshacer todas*.'
        _reply(ctx.deps, ctx.phone, text)
        return text
    chosen = candidates if which in (None, 'all') else [pair for pair in candidates if pair[0] == which]
    if not chosen:
        text = f'No encuentro la {which}. Lo último que confirmaste:\n{listing}'
        _reply(ctx.deps, ctx.phone, text)
        return text

    proposals, refusals = [], []
    for number, action in chosen:
        try:   # the check runs now, so a "no se puede" is answered before asking for a SI
            proposals.append((number, undo_service.propose_undo(ctx.db, action['id'], ctx.user, source='whatsapp', now=ctx.now)))
        except undo_service.CannotUndo as exc:
            refusals.append((undo_service.label(action), str(exc)))

    if not proposals:
        text = refusals[0][1] if len(refusals) == 1 else '\n'.join(f'• {name}: {why}' for name, why in refusals)
        _reply(ctx.deps, ctx.phone, text)
        return text

    cancelled = False
    for _, old in _live_pending(ctx.db, ctx.conv):   # like any new proposal: a bare SI must never confirm a stale one
        try:
            pending.cancel(ctx.db, old['id'])
            cancelled = True
        except pending.PendingActionError:
            pass
    ctx.conv['pending'] = [{'id': p['id'], 'n': i} for i, (_, p) in enumerate(proposals, start=1)]

    if len(proposals) == 1:
        proposal = proposals[0][1]
        lines = [f"↩️ ¿Deshago *{proposal['context']['label']}*?"]
        lines += [f'• {effect}' for effect in proposal['context']['effects'][:2]]
        lines += [*(f'⚠️ {w}' for w in proposal.get('warnings', [])), '*SI* / *NO*']
    else:
        lines = ['↩️ ¿Cuáles deshago?'] + [f"*{i}*: {p['context']['label']}" for i, (_, p) in enumerate(proposals, start=1)]
        lines.append('*SI 1*, *SI 2*, *SI todas* o *NO*')
    lines += [f'No se puede: {name}. {why}' for name, why in refusals]
    if cancelled:
        lines.append('(Cancelé la propuesta que tenías pendiente.)')
    text = '\n'.join(lines)
    _reply(ctx.deps, ctx.phone, text)
    return text


COMMAND_HANDLERS.append((_match_undo, _run_undo))


def _dispatch_commands(ctx):
    for matcher, handler in COMMAND_HANDLERS:
        matched = matcher(ctx)
        if matched is not None:
            answered = handler(ctx, matched)
            if answered is not None:
                return answered
    return None


def _agent_turn(ctx, timings):
    """Run the assistant on the conversation + this message, show the result and remember what the person saw"""
    db, deps, phone, conv, inbound = ctx.db, ctx.deps, ctx.phone, ctx.conv, ctx.inbound

    # a number answering the buttons the agent showed
    agent_text = inbound.agent_text()
    typed_only = not inbound.has_voice
    if typed_only and conv['choices'] and agent_text.isdigit() and 1 <= int(agent_text) <= len(conv['choices']):
        picked = conv['choices'][int(agent_text) - 1]
        agent_text = f"{picked['label']} [id: {picked['id']}]"

    content = ([{'type': 'text', 'text': agent_text}] if agent_text else []) + inbound.image_blocks
    messages = conv['history'] + [{'role': 'user', 'content': content}]
    agent_started = time.perf_counter()
    result = deps.run_chat(messages, ctx.user)
    timings['agent_ms'] = round((time.perf_counter() - agent_started) * 1000)

    # keep text only in the history (photos would be re-paid every turn); the agent's reading stays in its text
    stored = (agent_text if typed_only else inbound.history_text()) + (' [imagen enviada]' if inbound.image_blocks else '')
    conv['choices'] = result.get('choices') or []

    # a new set of proposals replaces the old ones: "SI" must never confirm something stale
    actions = result.get('pending_actions') or []
    if actions:
        for number, old in _live_pending(db, conv):
            try:
                pending.cancel(db, old['id'])
            except pending.PendingActionError:
                pass
        conv['pending'] = [{'id': a['id'], 'n': i} for i, a in enumerate(actions, start=1)]

    agent_reply = to_whatsapp(result.get('response') or '')
    parts = [inbound.notice, short_text(agent_reply) if actions else agent_reply]
    if conv['choices']:
        parts.append('\n'.join(f"{i}) {c['label']}" for i, c in enumerate(conv['choices'], start=1))
                     + '\nResponde con el número.')
    if actions:
        parts.append(proposals_message(actions))
    if inbound.has_voice and (actions or (inbound.stt_confidence is not None and inbound.stt_confidence < ECHO_BELOW_CONFIDENCE)):
        parts.insert(0, echo_line(' '.join(inbound.transcripts)))
    outgoing = '\n\n'.join(p for p in parts if p)
    # what the person saw (summary of the proposal included) is what the agent remembers
    markers = [f"[Propuesta {i}: {a['summary']}]" for i, a in enumerate(actions, start=1)]
    conv['history'] += [{'role': 'user', 'content': compact_message(stored.strip() or '[mensaje]')},
                        {'role': 'assistant', 'content': compact_message(outgoing or '…', markers)}]
    send_started = time.perf_counter()
    _reply(deps, phone, outgoing)
    timings['send_ms'] = round((time.perf_counter() - send_started) * 1000)
    return result


def _stored_message(db, sid):
    snapshot = db.collection(INBOX).document(sid).get()
    return snapshot.to_dict() if snapshot.exists else None


def _count_images(messages):
    """Photos the person sent in this go (what _gather reads, before its cap of MAX_IMAGES)"""
    return sum(1 for message in messages for item in message.get('media', [])[:MAX_IMAGES + 2]
               if (item.get('content_type') or '').split(';')[0] in ALLOWED_IMAGE_TYPES)


def process_inbox(db, sid, deps):
    """Handle one stored message. Returns a short status string (useful in logs and tests)."""
    ref = db.collection(INBOX).document(sid)
    message = _claim(db, ref)
    if message is None:
        return 'skipped'

    started = time.perf_counter()
    timings = {}
    created = message.get('created_at')
    if created is not None:
        created = created.replace(tzinfo=None) if getattr(created, 'tzinfo', None) else created
        timings['queue_ms'] = max(0, round((datetime.utcnow() - created).total_seconds() * 1000))

    phone = message['from']
    burst_id = message.get('burst_id')
    led = locked = False
    try:
        messages = [message]
        if burst_id:
            # part of a burst: only the worker of its LAST message answers, once, for all of them
            sids = burst.lead(db, phone, burst_id, sid, deps)
            if sids is None:
                ref.update({'status': MERGED, 'finished_at': deps.now()})
                return 'merged'
            led = True
            messages = [message if s == sid else _stored_message(db, s) for s in sids]
            messages = [m for m in messages if m]
        if deps.typing:
            deps.typing(sid)

        if not is_allowed(phone):
            ref.update({'status': IGNORED})
            return 'ignored'
        if not _within_quota(db, phone, cost=len(messages), now=deps.now()):   # a burst of N messages counts N
            _reply(deps, phone, 'Llegaste al límite de mensajes de hoy con el asistente. Mañana seguimos 🙂')
            ref.update({'status': DONE, 'finished_at': deps.now()})
            return 'quota'

        # one agent turn at a time per phone: the next one must see the history this one saves
        burst.acquire_lock(db, phone, sid, deps)
        locked = True

        now = deps.now()
        user = user_for(phone)
        inbound = _gather(db, deps, messages, timings)
        if _count_images(messages) > MAX_IMAGES:
            inbound.notice = f'Leí las primeras {MAX_IMAGES} fotos.'
        if inbound.audio_capped and inbound.transcripts:      # one note heard, another not: say so
            inbound.notice = '\n'.join(p for p in (inbound.notice, 'Una nota de voz no la pude escuchar (tope diario).') if p)
        if inbound.audio_seconds or inbound.transcripts:
            ref.update({'transcript': '\n'.join(inbound.transcripts), 'stt_confidence': inbound.stt_confidence,
                        'audio_seconds': round(inbound.audio_seconds, 1)})  # the text only; the audio is never saved
        nothing_else = not inbound.text and not inbound.image_blocks and not inbound.transcripts
        voice_problem = None
        if nothing_else and inbound.audio_too_long:
            voice_problem = ('audio_too_long', 'Uf, muy largo 😅 ¿me lo mandas en audios de menos de 1 minuto?')
        elif nothing_else and inbound.audio_capped:
            voice_problem = ('audio_capped', 'Hoy ya escuché varios audios y llegué al tope 😅 Escríbeme el mensaje y seguimos.')
        elif nothing_else and inbound.audio_empty:
            voice_problem = ('audio_empty', 'No te caché el audio 😅 ¿me lo repites o me lo escribes?')
        if voice_problem:
            _reply(deps, phone, voice_problem[1])
            ref.update({'status': DONE, 'finished_at': now})
            return voice_problem[0]
        if inbound.unsupported and not inbound.image_blocks and not inbound.text and not inbound.transcripts:
            _reply(deps, phone, 'Por ahora solo puedo leer texto y fotos. Mándame el mensaje escrito o una foto 🙂')
            ref.update({'status': DONE, 'finished_at': now})
            return 'unsupported'

        conv = _load_conversation(db, phone, now)
        ctx = Ctx(db=db, deps=deps, phone=phone, user=user, conv=conv, inbound=inbound, now=now)

        answered = _dispatch_commands(ctx)
        if answered is not None:
            conv['history'] += [{'role': 'user', 'content': compact_message(inbound.history_text())},
                                {'role': 'assistant', 'content': compact_message(answered)}]
            _save_conversation(db, phone, conv, now)
            ref.update({'status': DONE, 'finished_at': now})
            return 'command'

        result = _agent_turn(ctx, timings)
        timings['total_ms'] = round((time.perf_counter() - started) * 1000)
        _save_conversation(db, phone, conv, now)
        ref.update({'status': DONE, 'finished_at': now, 'usage': result.get('usage'), 'timings': timings})
        logger.info('WhatsApp timings %s: %s', sid, timings)
        return 'answered'
    except Exception as exc:  # noqa: BLE001
        logger.error('WhatsApp message %s failed: %s', sid, exc, exc_info=True)
        try:
            _reply(deps, phone, 'Sigo con tu mensaje anterior 😅 Escríbeme de nuevo en un minuto.'
                   if isinstance(exc, burst.LockBusy) else 'No pude procesar tu mensaje 😕 Intenta de nuevo en un momento.')
        except Exception:  # noqa: BLE001
            pass
        ref.update({'status': FAILED, 'error': safe_error(exc)})
        return 'failed'
    finally:
        if locked:
            burst.release_lock(db, phone, sid, deps.now())
        if led:
            burst.finish(db, phone, burst_id)
