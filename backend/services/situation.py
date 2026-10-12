"""A small, fresh snapshot of the business ("situación actual") given to the WhatsApp agent as DATA on every turn.

Why: questions like "¿qué eventos tengo esta semana?", "¿qué falta comprar?" or "¿qué consultas hay pendientes?" used to need a
tool call and a second model round (~1.2 s each). With this snapshot the model can answer straight away; anything outside it
(other dates, other periods, details) still goes through the tools. It carries NO ids: an event can only be chosen by the person
(ask_choice / typed), exactly like before.

Read only, three single-filter queries (no composite index), never raises. On by default; AI_WHATSAPP_CONTEXT=false switches it off.
"""
import logging
import os
from datetime import datetime, timedelta

from services.booking_search import DAY_NAMES, service_label
from utils import clock

logger = logging.getLogger(__name__)

HORIZON_DAYS = 14
MAX_EVENTS = 15
MAX_STOCK = 12
MAX_CONTACTS = 5
_STATUS_ES = {'pending': 'por confirmar', 'confirmed': 'confirmada'}


def enabled():
    return os.getenv('AI_WHATSAPP_CONTEXT', 'true').strip().lower() != 'false'


def _clean(value, limit=60):
    return ' '.join(str(value or '').split())[:limit].replace('<', '').replace('>', '')


def _qty(value):
    return (f'{float(value or 0):.2f}'.rstrip('0').rstrip('.')).replace('.', ',')


def _events(db, today):
    start, end = today.isoformat(), (today + timedelta(days=HORIZON_DAYS)).isoformat()
    query = db.collection('bookings').where('event_date', '>=', start).where('event_date', '<=', end + '~').limit(60)
    rows = [(str(b.get('event_date')), b) for b in (s.to_dict() or {} for s in query.stream())
            if b.get('status') in _STATUS_ES]
    rows.sort(key=lambda row: row[0])
    lines = []
    for when, booking in rows[:MAX_EVENTS]:
        day = datetime.strptime(when[:10], '%Y-%m-%d').date() if len(when) >= 10 else None
        label = f'{DAY_NAMES[day.weekday()][:3].lower()} {day.day}/{day.month}' if day else when
        hour = (booking.get('event_time') or (when[11:16] if len(when) >= 16 else '')) or ''
        parts = [f'{label} {hour}'.strip(), _clean(booking.get('client_name')) or 'sin nombre',
                 service_label(booking.get('service_type')),
                 _clean(booking.get('location')),
                 f"{booking['participants']} pers." if booking.get('participants') else '',
                 _STATUS_ES[booking['status']]]
        lines.append('- ' + ' · '.join(p for p in parts if p))
    if len(rows) > MAX_EVENTS:
        lines.append(f'- (+{len(rows) - MAX_EVENTS} más después: usa las herramientas)')
    return lines


def _low_stock(db):
    items = [s.to_dict() or {} for s in db.collection('inventory').where('needs_restock', '==', True).limit(MAX_STOCK + 1).stream()]
    lines = [f"- {_clean(i.get('name'))}: {_qty(i.get('current_stock'))} {_clean(i.get('unit'), 12)} (mínimo {_qty(i.get('min_stock'))})"
             for i in items[:MAX_STOCK]]
    if len(items) > MAX_STOCK:
        lines.append('- (hay más: usa las herramientas)')
    return lines


def _contacts(db):
    docs = [s.to_dict() or {} for s in db.collection('contacts').where('status', '==', 'pending').limit(MAX_CONTACTS + 1).stream()]
    lines = [f"- {_clean(c.get('name'), 40)} · {_clean(c.get('subject'), 60)}" + (' · ' + str(c['priority']) if c.get('priority') in ('high', 'urgent') else '')
             for c in docs[:MAX_CONTACTS]]
    if len(docs) > MAX_CONTACTS:
        lines.append('- (hay más: usa las herramientas)')
    return lines


def build(db, now):
    """The snapshot text ('' when switched off, empty or on any failure). `now` is naive UTC."""
    if not enabled():
        return ''
    today = clock.today_cl(now)
    sections = []
    for title, builder, args in ((f'Eventos por confirmar o confirmados en los próximos {HORIZON_DAYS} días (por fecha)', _events, (db, today)),
                                 ('Insumos con stock bajo o en el mínimo', _low_stock, (db,)),
                                 ('Consultas de clientes sin responder', _contacts, (db,))):
        try:
            lines = builder(*args)
        except Exception as exc:  # noqa: BLE001 - the agent still has its tools
            logger.warning('situation: %s failed: %s', title, exc)
            return ''                      # a partial snapshot could look like "nothing there": better none at all
        sections.append(f'{title}:\n' + ('\n'.join(lines) if lines else '- ninguno'))
    return '\n\n'.join(sections)
