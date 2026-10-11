"""The daily WhatsApp digest: at most ONE proactive message per day, only when there is something new.

run_daily() (called by the scheduled function `whatsapp_daily_digest`, 10:00 Chile time):
  1. recipients = AI_WHATSAPP_PROACTIVE_TO, and only the admin number (owner's decision). Empty by default: nothing is
     ever sent until someone switches it on on purpose;
  2. alerts_service.evaluate() brings the alert state up to date; per recipient we keep only what that number has not
     heard about, is not muting and is out of cooldown. Nothing new -> nothing sent;
  3. the daily quota doc `whatsapp_proactive/{phone}_{YYYYMMDD}` is created in a transaction ("create if missing"):
     if it already exists the run stops, so two scheduler runs still mean ONE message;
  4. inside WhatsApp's 24 h window (the person wrote to us recently) it goes as free text, outside it as the approved
     template (TEMPLATE_PABLITO_DIGEST_SID) with a "Ver" button;
  5. only after Twilio accepted it: the daily doc becomes `sent`, `notified[phone]` is stored on every alert and the
     numbered `detail` is saved so "Ver" / "silencia N" can use it. A failed send marks nothing as notified.

AI_WHATSAPP_PROACTIVE_DRY_RUN (true by default) runs everything but the sending and writes `status: 'dry_run'`.
"""
import json
import logging
import os
import re
from datetime import datetime, timedelta

from services import alerts_service as alerts
from services import pending_actions_service as pending
from utils import clock

logger = logging.getLogger(__name__)

PROACTIVE = 'whatsapp_proactive'
CONTACTS = 'whatsapp_contacts'

WINDOW = timedelta(hours=23, minutes=50)   # WhatsApp allows free text for 24 h after the person's last message
DIGEST_VALIDITY = timedelta(hours=48)      # how long "Ver" / "silencia N" refer to a digest
SEND_FROM_HOUR, SEND_UNTIL_HOUR = 8, 21    # local hours (Chile): never at night
SUMMARY_MAX = 100                          # template variable {{2}}
DETAIL_MAX_LINES = 12


# ---------- configuration ----------

def dry_run_default():
    return os.getenv('AI_WHATSAPP_PROACTIVE_DRY_RUN', 'true').strip().lower() != 'false'


def _phone(raw):
    digits = re.sub(r'\D', '', str(raw or ''))
    return f'+{digits}' if digits else ''


def recipients():
    """Numbers that may receive the digest: AI_WHATSAPP_PROACTIVE_TO ∩ the admin number. Empty when not switched on."""
    admin = _phone(os.getenv('ADMIN_WHATSAPP_NUMBER'))
    wanted = [_phone(n) for n in os.getenv('AI_WHATSAPP_PROACTIVE_TO', '').split(',') if _phone(n)]
    ignored = [n for n in wanted if n != admin]
    if ignored:
        logger.warning('Proactive digest: %d number(s) ignored (only the admin number receives it)', len(ignored))
    return [n for n in dict.fromkeys(wanted) if admin and n == admin]


# ---------- the message ----------

def summarize(active):
    """One short phrase for the template ({{2}}): no line breaks, at most 100 characters"""
    by_type = {}
    for alert in active:
        by_type.setdefault(alert['type'], []).append(alert)
    parts = []
    urgent = by_type.get(alerts.BOOKING_URGENT, [])
    if urgent:
        parts.append(f"{len(urgent)} reserva{'s' if len(urgent) > 1 else ''} urgente{'s' if len(urgent) > 1 else ''} por confirmar")
    tomorrow = by_type.get(alerts.EVENT_TOMORROW, [])
    if tomorrow:
        parts.append(f"{len(tomorrow)} evento{'s' if len(tomorrow) > 1 else ''} mañana")
    waiting = by_type.get(alerts.BOOKING_PENDING, [])
    if waiting:
        parts.append(f"{len(waiting)} reserva{'s' if len(waiting) > 1 else ''} por confirmar")
    proposals = by_type.get(alerts.PROPOSAL_PENDING, [])
    if proposals:
        parts.append(f"{len(proposals)} propuesta{'s' if len(proposals) > 1 else ''} sin responder")
    stock = by_type.get(alerts.LOW_STOCK, [])
    if stock:
        names = [a['label'] for a in stock]
        parts.append('stock bajo de ' + (names[0] if len(names) == 1 else f'{names[0]} y {names[1]}' if len(names) == 2
                                         else f'{names[0]} y {len(names) - 1} más'))
    text = ', '.join(parts[:-1]) + ' y ' + parts[-1] if len(parts) > 1 else (parts[0] if parts else '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text if len(text) <= SUMMARY_MAX else text[:SUMMARY_MAX - 1].rstrip() + '…'


def _line(alert):
    data = alert.get('data') or {}
    label = alert['label']
    kind = alert['type']
    if kind == alerts.BOOKING_URGENT:
        return f"🔴 Reserva sin confirmar, el evento es pronto: {label}"
    if kind == alerts.BOOKING_PENDING:
        return f"🟡 Reserva por confirmar: {label}"
    if kind == alerts.EVENT_TOMORROW:
        return f"📅 Mañana hay evento: {label}"
    if kind == alerts.PROPOSAL_PENDING:
        return f"📋 Propuesta sin responder: {label}"
    unit = f" {data['unit']}" if data.get('unit') else ''
    stock = data.get('current_stock')
    now_has = f" (quedan {stock:g}{unit})" if isinstance(stock, (int, float)) else ''
    return f"📦 Stock bajo: {label}{now_has}"


def build_detail(active):
    """(numbered detail text, keys of the numbered lines, their labels)"""
    shown = active[:DETAIL_MAX_LINES]
    lines = ['📋 *Avisos de hoy*'] + [f'{i}. {_line(a)}' for i, a in enumerate(shown, start=1)]
    if len(active) > len(shown):
        lines.append(f'… y {len(active) - len(shown)} más (míralos en el panel)')
    lines.append('Para no recibir más de uno: *silenciar 2*, *silenciar stock*, *silenciar reservas*.')
    return '\n'.join(lines), [a['key'] for a in shown], [a['label'] for a in shown]


def build_free_text(active):
    """At most 4 lines (inside the 24 h window: no template needed)"""
    count = len(active)
    return '\n'.join([
        f"Buenos días 🍕 Tienes {count} aviso{'s' if count > 1 else ''} nuevo{'s' if count > 1 else ''}:",
        summarize(active),
        'Responde *ver* para el detalle.',
        'Si no quieres más de algo: *silenciar stock* o *silenciar 2*.',
    ])


def template_variables(active):
    return {'1': str(len(active)), '2': summarize(active)}


def in_window(db, phone, now):
    snap = db.collection(CONTACTS).document(phone).get()
    last = alerts._naive_utc((snap.to_dict() or {}).get('last_user_message_at')) if snap.exists else None
    return last is not None and timedelta(0) <= now - last < WINDOW


# ---------- sending ----------

class TwilioDeps:
    """Production senders. Tests pass their own object with the same two methods."""

    def __init__(self, template_sid=None):
        self.template_sid = template_sid if template_sid is not None else os.getenv('TEMPLATE_PABLITO_DIGEST_SID', '')

    @staticmethod
    def _client():
        from services.whatsapp_service import TWILIO_WHATSAPP_FROM, twilio_client
        if twilio_client is None:
            raise RuntimeError('Twilio is not configured')
        return twilio_client, TWILIO_WHATSAPP_FROM

    def send_text(self, phone, body):
        client, sender = self._client()
        return client.messages.create(from_=sender, to=f'whatsapp:{phone}', body=body).sid

    def send_template(self, phone, content_sid, variables):
        client, sender = self._client()
        return client.messages.create(from_=sender, to=f'whatsapp:{phone}', content_sid=content_sid,
                                      content_variables=json.dumps(variables, ensure_ascii=False)).sid


def _claim_day(db, ref, now, dry_run):
    """Create today's quota doc if missing (a dry run may be overwritten by a real run). False = already used today."""
    transaction = db.transaction()
    status = 'dry_run' if dry_run else 'sending'

    @pending._transactional
    def run(txn):
        snapshot = ref.get(transaction=txn)
        if snapshot.exists and snapshot.to_dict().get('status') != 'dry_run':
            return False
        txn.set(ref, {'status': status, 'started_at': now})
        return True

    return run(transaction)


def run_daily(db, deps, now=None, dry_run=None):
    """Returns what it did (for logs and tests). `now` is naive UTC."""
    now = now or datetime.utcnow()
    dry_run = dry_run_default() if dry_run is None else dry_run
    to = recipients()
    if not to:
        return {'skipped': 'no_recipients'}
    local = clock.now_cl(now)
    if not SEND_FROM_HOUR <= local.hour < SEND_UNTIL_HOUR:
        return {'skipped': 'quiet_hours'}

    active = alerts.evaluate(db, now)
    results = {}
    for phone in to:
        results[phone] = _digest_for(db, deps, phone, active, now, local, dry_run)
    return {'results': results}


def _digest_for(db, deps, phone, active, now, local, dry_run):
    prefs = alerts.get_prefs(db, phone)
    news = alerts.announceable(active, phone, prefs, now)
    if not news:
        return {'status': 'nothing_new'}

    use_text = in_window(db, phone, now)
    template_sid = getattr(deps, 'template_sid', '') or ''
    if not use_text and not template_sid and not dry_run:
        logger.warning('Proactive digest: outside the 24 h window and TEMPLATE_PABLITO_DIGEST_SID is not set')
        return {'status': 'no_template'}

    detail, items, labels = build_detail(news)
    body = build_free_text(news) if use_text else None
    variables = template_variables(news)
    ref = db.collection(PROACTIVE).document(f"{phone}_{local:%Y%m%d}")
    if not _claim_day(db, ref, now, dry_run):
        return {'status': 'already_sent'}

    record = {'phone': phone, 'count': len(news), 'mode': 'text' if use_text else 'template', 'detail': detail,
              'items': items, 'keys': [a['key'] for a in news], 'text': body, 'variables': variables}
    if dry_run:
        ref.set({**record, 'status': 'dry_run', 'started_at': now})
        return {'status': 'dry_run', 'mode': record['mode'], 'count': len(news)}

    try:
        sid = deps.send_text(phone, body) if use_text else deps.send_template(phone, template_sid, variables)
    except Exception as exc:  # noqa: BLE001 - nothing is marked as notified; today's quota stays used (no blind retry)
        logger.error('Proactive digest to ...%s failed: %s', phone[-4:], exc, exc_info=True)
        ref.set({**record, 'status': 'failed', 'error': str(exc)[:200], 'started_at': now})
        return {'status': 'failed', 'error': str(exc)[:200]}

    try:
        batch = db.batch()
        batch.set(ref, {**record, 'status': 'sent', 'sent_at': now, 'sid': sid})
        alerts.mark_notified(db, batch, news, phone, now)
        batch.set(db.collection(CONTACTS).document(phone), {
            'last_digest': {'at': now, 'detail': detail, 'items': items, 'labels': labels}, 'updated_at': now}, merge=True)
        batch.commit()
    except Exception as exc:  # noqa: BLE001 - the message went out; the daily doc stays 'sending' so nothing goes twice today
        logger.error('Proactive digest sent but bookkeeping failed: %s', exc, exc_info=True)
        return {'status': 'sent_unrecorded', 'mode': record['mode'], 'sid': sid}
    return {'status': 'sent', 'mode': record['mode'], 'count': len(news), 'sid': sid}


def run_scheduled(db, now=None):
    """What the scheduled function calls: production senders, dry run unless switched off. Off with the channel."""
    from services import whatsapp_agent as wa
    if not wa.enabled():
        return {'skipped': 'channel off'}
    return run_daily(db, TwilioDeps(), now=now)


# ---------- "Ver" and the admin preview ----------

def last_digest(db, phone, now):
    """The digest sent to this number in the last 48 h, or None"""
    snap = db.collection(CONTACTS).document(phone).get()
    digest = (snap.to_dict() or {}).get('last_digest') if snap.exists else None
    at = alerts._naive_utc((digest or {}).get('at'))
    if not digest or at is None or now - at > DIGEST_VALIDITY:
        return None
    return digest


def view_reply(db, phone, button_payload, text, now=None):
    """Answer the "Ver" button (or the word "ver") with the saved detail. None = this message is not for us."""
    from utils.text_matching import normalize_text
    tapped = (button_payload or '') == 'digest_ver'
    typed = re.sub(r'[^\w\s]', '', normalize_text(text)).strip() == 'ver'
    if not (tapped or typed):
        return None
    digest = last_digest(db, phone, now or datetime.utcnow())
    if digest:
        return digest['detail']
    return 'Ya no tengo ese resumen guardado 🙂 Escríbeme lo que necesites.' if tapped else None


def preview(db, now=None, phone=None):
    """What the digest would say right now, WITHOUT changing any state (admin endpoint)"""
    now = now or datetime.utcnow()
    phone = phone or _phone(os.getenv('ADMIN_WHATSAPP_NUMBER'))
    active = alerts.evaluate(db, now, persist=False)
    news = alerts.announceable(active, phone, alerts.get_prefs(db, phone), now) if phone else []
    detail, items, _ = build_detail(news) if news else ('', [], [])
    return {
        'recipients_enabled': recipients(), 'dry_run': dry_run_default(), 'phone': phone,
        'active_total': len(active), 'new_count': len(news),
        'mode': ('text' if in_window(db, phone, now) else 'template') if phone else None,
        'summary': summarize(news) if news else '', 'text': build_free_text(news) if news else '',
        'template_variables': template_variables(news) if news else {}, 'detail': detail, 'items': items,
        'would_send': bool(news),
    }
