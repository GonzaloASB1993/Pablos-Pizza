"""Instant answers (no model) for a few frequent, unambiguous read-only questions on WhatsApp.

Only a message that is EXACTLY one of these shapes is answered here ("qué hay de stock de queso", "tengo algo mañana?");
anything else (or any doubt: no match found, an unclear name, an error) returns None and the agent takes it, as before.
Read only: it never proposes nor changes anything. AI_WHATSAPP_FAST_QUERIES=false switches it off.
"""
import logging
import os
import re
from datetime import timedelta

from services import inventory_search
from services.booking_search import service_label
from utils import clock
from utils.text_matching import normalize_text

logger = logging.getLogger(__name__)

MAX_ITEMS = 4
MAX_NAME_WORDS = 3
NOT_AN_ITEM = {'hoy', 'manana', 'nuevo', 'novedad', 'novedades', 'eventos', 'evento', 'reservas', 'reserva', 'pendiente',
               'pendientes', 'todo', 'todos', 'inventario', 'gastos', 'ventas', 'plata', 'stock', 'bajo', 'minimo', 'esto',
               'eso', 'algo', 'tiempo', 'semana', 'mes', 'ayer'}

_NAME = r"(?P<name>[a-z0-9ñ]+(?: [a-z0-9ñ]+){0,%d})" % (MAX_NAME_WORDS - 1)
_STOCK = [re.compile(p) for p in (
    rf'^(?:que hay de |cuanto hay de |como esta el |como va el |ver )?stock (?:de |del )?{_NAME}$',
    rf'^(?:cuanto|cuanta|cuantos|cuantas) (?:hay|queda|quedan|tenemos|tengo|nos queda|nos quedan) (?:de |del )?{_NAME}$',
)]
_DAY = r'(?P<day>hoy|manana)'
_EVENTS = [re.compile(p) for p in (
    rf'^(?:que |cuales |cuantos )?eventos? (?:tengo|hay|tenemos|vienen|tienen)? ?(?:para |de |el )?{_DAY}$',
    rf'^(?:que |cuales )?eventos? {_DAY}$',
    rf'^tengo (?:algun )?(?:evento|algo|reserva) {_DAY}$',
    rf'^que (?:tengo|hay|tenemos) {_DAY}$',
)]
_STATUS_ES = {'pending': 'por confirmar', 'confirmed': 'confirmada', 'completed': 'completada'}
_DAYS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']


def enabled():
    return os.getenv('AI_WHATSAPP_FAST_QUERIES', 'true').strip().lower() != 'false'


def _clean(text):
    return re.sub(r'\s+', ' ', normalize_text(re.sub(r'[^\w\s]', ' ', text or ''))).strip()


def parse(text):
    """('stock', name) | ('events', 'hoy'|'manana') | None"""
    cleaned = _clean(text)
    for pattern in _EVENTS:
        match = pattern.match(cleaned)
        if match:
            return 'events', match.group('day')
    for pattern in _STOCK:
        match = pattern.match(cleaned)
        if match:
            words = match.group('name').split()
            if len(words) > MAX_NAME_WORDS or any(w in NOT_AN_ITEM for w in words):
                return None
            return 'stock', ' '.join(words)
    return None


def _tokens(text):
    return [t[:-1] if len(t) > 3 and t.endswith('s') else t for t in _clean(text).split()]


def _is_that_item(query, name):
    """Every word of the question is a whole word of the item name ("queso" is in "Queso mozzarella"; "sal" is not in
    "Salsa de tomate")"""
    wanted, have = _tokens(query), _tokens(name)
    return bool(wanted) and all(w in have for w in wanted)


def _qty(value):
    number = float(value or 0)
    return (f'{number:.2f}'.rstrip('0').rstrip('.')).replace('.', ',')


def answer_stock(db, name):
    scored = inventory_search.scored_items(db, name, threshold=0.6)
    hits = [(item_id, item) for _, item_id, item in scored if _is_that_item(name, item.get('name', ''))]
    if not hits:
        return None                       # unknown name / only look-alikes: the agent can ask or search better
    lines = []
    for _, item in hits[:MAX_ITEMS]:
        stock, minimum = item.get('current_stock') or 0, item.get('min_stock') or 0
        low = item.get('needs_restock') or (minimum and stock <= minimum)
        lines.append(f"• {item.get('name')}: {_qty(stock)} {item.get('unit') or 'un.'}"
                     + (f' (mínimo {_qty(minimum)}) ⚠️ bajo' if low else ''))
    extra = f'\n(+{len(hits) - MAX_ITEMS} más parecidos: pídeme "stock" con el nombre completo)' if len(hits) > MAX_ITEMS else ''
    return '📦 Stock:\n' + '\n'.join(lines) + extra


def answer_events(db, day, now):
    today = clock.today_cl(now)
    target = today if day == 'hoy' else today + timedelta(days=1)
    iso = target.isoformat()
    query = (db.collection('bookings').where('event_date', '>=', iso).where('event_date', '<=', iso + '~')
             .limit(25))
    rows = []
    for snapshot in query.stream():
        booking = snapshot.to_dict() or {}
        if booking.get('status') in ('pending', 'confirmed', 'completed'):
            rows.append(booking)
    rows.sort(key=lambda b: str(b.get('event_date')))
    label = f"{'Hoy' if day == 'hoy' else 'Mañana'} ({_DAYS[target.weekday()]} {target.day})"
    if not rows:
        return f'{label}: no tienes eventos 🙌'
    lines = []
    for booking in rows[:8]:
        when = str(booking.get('event_date') or '')
        time_part = (booking.get('event_time') or (when[11:16] if len(when) >= 16 else '')) or ''
        service = service_label(booking.get('service_type'))
        details = ' · '.join(p for p in (service, booking.get('location'),
                                         f"{booking['participants']} pers." if booking.get('participants') else '') if p)
        status = _STATUS_ES.get(booking.get('status'), '')
        lines.append(f"• {time_part + ' ' if time_part else ''}{booking.get('client_name') or 'Sin nombre'}"
                     + (f' — {details}' if details else '') + (f' ({status})' if status else ''))
    more = f'\n(+{len(rows) - 8} más: míralos en el panel)' if len(rows) > 8 else ''
    return f'📅 {label}:\n' + '\n'.join(lines) + more


def answer(db, text, now):
    """The instant answer for `text`, or None to let the agent handle it"""
    parsed = parse(text)
    if not parsed:
        return None
    try:
        kind, value = parsed
        return answer_stock(db, value) if kind == 'stock' else answer_events(db, value, now)
    except Exception as exc:  # noqa: BLE001 - any doubt goes to the agent
        logger.warning('quick query failed, using the agent: %s', exc)
        return None
