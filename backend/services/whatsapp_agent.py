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
from datetime import datetime, timedelta

from services import pending_actions_service as pending
from services.ai_chat_history import ALLOWED_IMAGE_TYPES
from utils.text_matching import normalize_text

logger = logging.getLogger(__name__)

INBOX = 'whatsapp_inbox'
CONVERSATIONS = 'whatsapp_conversations'
QUOTA = 'whatsapp_quota'

RESET_AFTER = timedelta(hours=6)     # a conversation older than this starts fresh
MAX_HISTORY = 16                     # text messages kept per conversation
MAX_MEDIA_BYTES = 8 * 1024 * 1024
MAX_IMAGES = 3
CHUNK = 1400                         # Twilio's limit is 1600 characters per message
DEFAULT_DAILY_LIMIT = 100

RECEIVED, PROCESSING, DONE, FAILED, IGNORED = 'received', 'processing', 'done', 'failed', 'ignored'


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

def store_inbound(db, form):
    """Persist an incoming message once per MessageSid. Returns True if it was new."""
    sid = form.get('MessageSid') or form.get('SmsMessageSid')
    if not sid:
        return False
    ref = db.collection(INBOX).document(sid)
    if ref.get().exists:
        return False
    count = int(form.get('NumMedia') or 0)
    media = [{'url': form.get(f'MediaUrl{i}'), 'content_type': form.get(f'MediaContentType{i}')}
             for i in range(min(count, 10)) if form.get(f'MediaUrl{i}')]
    ref.set({
        'sid': sid, 'from': normalize_phone(form.get('From')), 'body': (form.get('Body') or '')[:4000],
        'media': media, 'profile_name': form.get('ProfileName'), 'status': RECEIVED, 'created_at': datetime.utcnow(),
    })
    return True


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


def _within_quota(db, phone):
    limit = int(os.getenv('AI_WHATSAPP_DAILY_LIMIT', DEFAULT_DAILY_LIMIT))
    ref = db.collection(QUOTA).document(f"{phone}_{datetime.utcnow():%Y%m%d}")
    snapshot = ref.get()
    used = snapshot.to_dict().get('count', 0) if snapshot.exists else 0
    if used >= limit:
        return False
    ref.set({'phone': phone, 'count': used + 1, 'updated_at': datetime.utcnow()})
    return True


# ---------- conversation state ----------

def _load_conversation(db, phone, now):
    snapshot = db.collection(CONVERSATIONS).document(phone).get()
    conv = snapshot.to_dict() if snapshot.exists else {}
    last = conv.get('last_inbound_at')
    if last is not None and getattr(last, 'tzinfo', None) is not None:
        last = last.replace(tzinfo=None)
    if not conv or last is None or now - last > RESET_AFTER:
        return {'history': [], 'pending': [], 'choices': []}
    return {'history': conv.get('history', []), 'pending': conv.get('pending', []), 'choices': conv.get('choices', [])}


def _save_conversation(db, phone, conv, now):
    db.collection(CONVERSATIONS).document(phone).set({
        'history': conv['history'][-MAX_HISTORY:], 'pending': conv['pending'], 'choices': conv['choices'],
        'last_inbound_at': now, 'updated_at': now,
    })


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
    return '✅ Listo.'


# ---------- the worker ----------

class Deps:
    """What process_inbox needs from the outside world (replaced by fakes in tests)"""

    def __init__(self, send, run_chat, download_media, now=None, typing=None):
        self.send, self.run_chat, self.download_media = send, run_chat, download_media
        self.now = now or datetime.utcnow
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


def _handle_command(db, deps, phone, user, conv, kind, which):
    """Handle a bare SI / NO. Returns the text it answered with, or None when it was not a command after all
    (no proposal is waiting): then the agent reads it as normal text."""
    live = _live_pending(db, conv)
    if not live:
        return None
    if which is None and len(live) > 1:
        text = ('Tengo varias propuestas pendientes. Responde *SI 1*, *SI 2*… o *SI todas* '
                '(o *NO 1*, *NO todas* para cancelar).')
        _reply(deps, phone, text)
        return text
    chosen = live if which in (None, 'all') else [(n, a) for n, a in live if n == which]
    if not chosen:
        text = f'No encuentro la propuesta {which}. Pendientes: ' + ', '.join(str(n) for n, _ in live) + '.'
        _reply(deps, phone, text)
        return text

    replies = []
    for number, action in chosen:
        label = f'Propuesta {number}: ' if len(live) > 1 else ''
        try:
            if kind == 'yes':
                done = pending.confirm(db, action['id'], user)
                replies.append(label + result_message(done))
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
    text = '\n'.join(replies)
    _reply(deps, phone, text)
    return text


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
    if deps.typing:
        deps.typing(sid)

    phone = message['from']
    try:
        if not is_allowed(phone):
            ref.update({'status': IGNORED})
            return 'ignored'
        if not _within_quota(db, phone):
            _reply(deps, phone, 'Llegaste al límite de mensajes de hoy con el asistente. Mañana seguimos 🙂')
            ref.update({'status': DONE, 'finished_at': deps.now()})
            return 'quota'

        now = deps.now()
        user = user_for(phone)
        conv = _load_conversation(db, phone, now)
        text = (message.get('body') or '').strip()

        # photos / unsupported media
        image_blocks, unsupported = [], False
        media_started = time.perf_counter()
        for item in message.get('media', [])[:MAX_IMAGES + 2]:
            if (item.get('content_type') or '').split(';')[0] in ALLOWED_IMAGE_TYPES and len(image_blocks) < MAX_IMAGES:
                data = compress_image(deps.download_media(item['url']))
                image_blocks.append({'type': 'image', 'source': {
                    'type': 'base64', 'media_type': 'image/jpeg', 'data': base64.b64encode(data).decode()}})
            else:
                unsupported = True
        timings['media_ms'] = round((time.perf_counter() - media_started) * 1000)
        if unsupported and not image_blocks and not text:
            _reply(deps, phone, 'Por ahora solo puedo leer texto y fotos. Mándame el mensaje escrito o una foto 🙂')
            ref.update({'status': DONE, 'finished_at': now})
            return 'unsupported'

        # SI / NO answers to a pending proposal
        command = parse_command(text) if not image_blocks else None
        answered = _handle_command(db, deps, phone, user, conv, *command) if command else None
        if command and answered is None and conv.get('pending'):
            answered = 'Esa propuesta ya no está pendiente (se confirmó, canceló o venció). ¿Qué necesitas?'
            conv['pending'] = []
            _reply(deps, phone, answered)
        if answered is not None:
            conv['history'] += [{'role': 'user', 'content': text}, {'role': 'assistant', 'content': answered}]
            _save_conversation(db, phone, conv, now)
            ref.update({'status': DONE, 'finished_at': now})
            return 'command'

        # a number answering the buttons the agent showed
        agent_text = text
        if conv['choices'] and text.isdigit() and 1 <= int(text) <= len(conv['choices']):
            picked = conv['choices'][int(text) - 1]
            agent_text = f"{picked['label']} [id: {picked['id']}]"

        content = ([{'type': 'text', 'text': agent_text}] if agent_text else []) + image_blocks
        messages = conv['history'] + [{'role': 'user', 'content': content}]
        agent_started = time.perf_counter()
        result = deps.run_chat(messages, user)
        timings['agent_ms'] = round((time.perf_counter() - agent_started) * 1000)

        # keep text only in the history (photos would be re-paid every turn); the agent's reading stays in its text
        stored = agent_text + (' [imagen enviada]' if image_blocks else '')
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

        agent_text = to_whatsapp(result.get('response') or '')
        parts = [short_text(agent_text) if actions else agent_text]
        if conv['choices']:
            parts.append('\n'.join(f"{i}) {c['label']}" for i, c in enumerate(conv['choices'], start=1))
                         + '\nResponde con el número.')
        if actions:
            parts.append(proposals_message(actions))
        outgoing = '\n\n'.join(p for p in parts if p)
        # what the person saw (summary of the proposal included) is what the agent remembers
        conv['history'] += [{'role': 'user', 'content': stored.strip() or '[mensaje]'},
                            {'role': 'assistant', 'content': outgoing or '…'}]
        send_started = time.perf_counter()
        _reply(deps, phone, outgoing)
        timings['send_ms'] = round((time.perf_counter() - send_started) * 1000)
        timings['total_ms'] = round((time.perf_counter() - started) * 1000)

        _save_conversation(db, phone, conv, now)
        ref.update({'status': DONE, 'finished_at': now, 'usage': result.get('usage'), 'timings': timings})
        logger.info('WhatsApp timings %s: %s', sid, timings)
        return 'answered'
    except Exception as exc:  # noqa: BLE001
        logger.error('WhatsApp message %s failed: %s', sid, exc, exc_info=True)
        try:
            _reply(deps, phone, 'No pude procesar tu mensaje 😕 Intenta de nuevo en un momento.')
        except Exception:  # noqa: BLE001
            pass
        ref.update({'status': FAILED, 'error': str(exc)[:300]})
        return 'failed'
