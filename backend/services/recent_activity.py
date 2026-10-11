"""Recent activity of the assistant (last 48 h of proposals), injected as DATA into the system prompt.

It lets Pablito answer "¿guardaste lo de ayer?" after the 24 h conversation memory is gone, without the model having
to guess. It is never written to the conversation history and never reaches the user's message (so the ids it shows
cannot enable proposals about events: only what the person typed does).
"""
import logging
from datetime import datetime, timedelta

from utils import clock

logger = logging.getLogger(__name__)

WINDOW = timedelta(hours=48)
MAX_LINES = 8
STATUS_ES = {'pending': 'pendiente', 'processing': 'pendiente', 'confirmed': 'confirmada',
             'cancelled': 'cancelada', 'expired': 'vencida', 'failed': 'falló'}


def _naive_utc(value):
    if value is not None and getattr(value, 'tzinfo', None) is not None:
        return value.replace(tzinfo=None) - (value.utcoffset() or timedelta(0))
    return value


def _clean(text, limit=80):
    return ' '.join(str(text or '').split())[:limit].replace('<', '').replace('>', '')


def _day_label(local, local_now):
    days = (local_now.date() - local.date()).days
    if days == 0:
        return 'hoy'
    if days == 1:
        return 'ayer'
    return local.strftime('%d/%m')


def _status(action, now):
    status = action.get('status')
    expires = _naive_utc(action.get('expires_at'))
    if status == 'pending' and expires is not None and expires <= now:
        status = 'expired'
    return STATUS_ES.get(status, str(status or '?'))


def build(db, now):
    """Up to 8 lines, newest first: "ayer 18:40 · Compra Líder $23.450 · confirmada · id abc12345".
    `now` is naive UTC (like every datetime stored in Firestore). Returns '' when there is nothing to show."""
    now = _naive_utc(now) or datetime.utcnow()
    docs = db.collection('pending_actions').where('created_at', '>=', now - WINDOW).stream()  # one field: no composite index
    actions = [d.to_dict() for d in docs]
    actions = [a for a in actions if a and a.get('created_at') is not None]
    actions.sort(key=lambda a: _naive_utc(a['created_at']), reverse=True)
    local_now = clock.now_cl(now)
    lines = []
    for action in actions[:MAX_LINES]:
        local = clock.now_cl(_naive_utc(action['created_at']))
        lines.append(f"{_day_label(local, local_now)} {local:%H:%M} · {_clean(action.get('summary'))} · "
                     f"{_status(action, now)} · id {str(action.get('id') or '')[:8]}")
    return '\n'.join(lines)
