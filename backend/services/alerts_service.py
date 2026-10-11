"""Proactive alerts WITHOUT spam: a small state machine per condition.

Every condition the business cares about (low stock, a booking waiting for an answer, an event tomorrow, a proposal
nobody answered) is one document in `assistant_alerts/{type}:{entity_id}`:

    {type, entity_id, label, state: 'active'|'resolved', episode, first_seen_at, last_seen_at, resolved_at,
     notified: {phone: ts}, last_notified: {phone: ts}, last_notified_at, data}

Rules that keep the assistant quiet:
  * a NEW condition becomes `active` (episode 1) and is announced ONCE (`notified[phone]`);
  * a condition that stays the same only refreshes `last_seen_at`: it is never announced again;
  * when it disappears it becomes `resolved`; if it comes back later it is a new episode (`episode + 1`, `notified = {}`);
  * hysteresis: low stock is only resolved once the stock is clearly above the minimum (> min * 1.2), so a level that
    hovers around the minimum does not flip-flop;
  * cooldown: no key is announced again before 72 h after its last announcement, whatever the episode;
  * the person can mute a type / a key / everything (`whatsapp_contacts/{phone}.alert_prefs`).

`evaluate()` only maintains this state; deciding who hears about what, and when, is proactive_service's job.
Business "today" comes from utils/clock.py (Cloud Run runs in UTC). Nothing here ever writes business data.
"""
import logging
from datetime import datetime, timedelta, timezone

from services.booking_search import DAY_NAMES, event_day
from utils import clock

logger = logging.getLogger(__name__)

ALERTS = 'assistant_alerts'
CONTACTS = 'whatsapp_contacts'

LOW_STOCK, BOOKING_PENDING, BOOKING_URGENT = 'low_stock', 'booking_pending', 'booking_pending_urgent'
EVENT_TOMORROW, PROPOSAL_PENDING = 'event_tomorrow', 'proposal_pending'

COOLDOWN = timedelta(hours=72)        # a key is never announced again sooner than this
STOCK_HYSTERESIS = 1.2                # low stock resolves only above min_stock * 1.2
BOOKING_WAIT = timedelta(hours=24)    # a pending booking is worth a reminder after a day without an answer
URGENT_DAYS = 3                       # ... and one urgent reminder when the event is this close
PROPOSAL_WAIT = timedelta(hours=3)

# what the person types -> the alert types it covers
TYPE_GROUPS = {
    'stock': (LOW_STOCK,),
    'reservas': (BOOKING_PENDING, BOOKING_URGENT),
    'eventos': (EVENT_TOMORROW,),
    'propuestas': (PROPOSAL_PENDING,),
}
# most important first: the order of the digest and of its numbered detail
PRIORITY = (BOOKING_URGENT, EVENT_TOMORROW, BOOKING_PENDING, PROPOSAL_PENDING, LOW_STOCK)


def _naive_utc(value):
    """Firestore hands back aware datetimes; everything here works with naive UTC"""
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value if isinstance(value, datetime) else None


def key_of(alert_type, entity_id):
    return f'{alert_type}:{entity_id}'


def short_day(day):
    """'2026-10-17' -> 'sáb 17/10'"""
    try:
        parsed = datetime.strptime(day, '%Y-%m-%d')
    except (TypeError, ValueError):
        return day or '?'
    return f'{DAY_NAMES[parsed.weekday()][:3].lower()} {parsed.day}/{parsed.month}'


# ---------- what is wrong right now ----------

def _stock_conditions(db):
    found = {}
    for snap in db.collection('inventory').where('needs_restock', '==', True).stream():
        item = snap.to_dict() or {}
        if item.get('is_active') is False or float(item.get('min_stock') or 0) <= 0:
            continue
        name = item.get('name') or snap.id
        found[key_of(LOW_STOCK, snap.id)] = {
            'type': LOW_STOCK, 'entity_id': snap.id, 'label': name,
            'data': {'current_stock': item.get('current_stock'), 'min_stock': item.get('min_stock'),
                     'unit': item.get('unit')}}
    return found


def _booking_conditions(db, now):
    found, today = {}, clock.today_cl(now)
    for snap in db.collection('bookings').where('status', '==', 'pending').stream():
        booking = snap.to_dict() or {}
        created = _naive_utc(booking.get('created_at'))
        day = event_day(booking.get('event_date'))
        try:
            days_left = (datetime.strptime(day, '%Y-%m-%d').date() - today).days
        except (TypeError, ValueError):
            continue
        if days_left < 0 or created is None or now - created < BOOKING_WAIT:
            continue
        name = (booking.get('client_name') or 'Cliente').strip()
        kind = BOOKING_URGENT if days_left <= URGENT_DAYS else BOOKING_PENDING
        found[key_of(kind, snap.id)] = {
            'type': kind, 'entity_id': snap.id, 'label': f'{name} ({short_day(day)})',
            'data': {'event_date': day, 'days_left': days_left}}
    return found


def _event_conditions(db, now):
    found, tomorrow = {}, (clock.today_cl(now) + timedelta(days=1)).isoformat()
    for snap in db.collection('bookings').where('status', '==', 'confirmed').stream():
        booking = snap.to_dict() or {}
        if event_day(booking.get('event_date')) != tomorrow:
            continue
        name = (booking.get('client_name') or 'Cliente').strip()
        found[key_of(EVENT_TOMORROW, snap.id)] = {
            'type': EVENT_TOMORROW, 'entity_id': snap.id, 'label': name, 'data': {'event_date': tomorrow}}
    return found


def _proposal_conditions(db, now):
    found = {}
    for snap in db.collection('pending_actions').where('status', '==', 'pending').stream():
        action = snap.to_dict() or {}
        created, expires = _naive_utc(action.get('created_at')), _naive_utc(action.get('expires_at'))
        if created is None or now - created < PROPOSAL_WAIT or (expires is not None and expires <= now):
            continue
        found[key_of(PROPOSAL_PENDING, snap.id)] = {
            'type': PROPOSAL_PENDING, 'entity_id': snap.id, 'label': action.get('summary') or 'Propuesta',
            'data': {'action_type': action.get('type')}}
    return found


def current_conditions(db, now):
    """{key: condition} of everything that is wrong at this moment (read-only)"""
    found = {}
    for part in (_stock_conditions(db), _booking_conditions(db, now), _event_conditions(db, now),
                 _proposal_conditions(db, now)):
        found.update(part)
    return found


def _still_low(db, alert):
    """Hysteresis: a low-stock alert whose item is back above the minimum but not clearly above it is kept"""
    if alert.get('type') != LOW_STOCK:
        return False
    snap = db.collection('inventory').document(alert['entity_id']).get()
    if not snap.exists:
        return False
    item = snap.to_dict()
    minimum = float(item.get('min_stock') or 0)
    return minimum > 0 and float(item.get('current_stock') or 0) <= minimum * STOCK_HYSTERESIS


# ---------- the state machine ----------

def evaluate(db, now, persist=True):
    """Bring `assistant_alerts` up to date and return the ACTIVE alerts (each one with its `key`), most important first.

    persist=False computes the same result without writing anything (the admin preview)."""
    current = current_conditions(db, now)
    stored = {snap.id: snap.to_dict() for snap in db.collection(ALERTS).stream()}
    writes, active = {}, {}

    for key, cond in current.items():
        prev = stored.get(key)
        if prev is None:
            doc = {**cond, 'state': 'active', 'episode': 1, 'first_seen_at': now, 'last_seen_at': now,
                   'resolved_at': None, 'notified': {}, 'last_notified_at': None}
        elif prev.get('state') == 'resolved':
            # it came back: a new episode, announced once more (the cooldown still applies at announcement time)
            doc = {**prev, **cond, 'state': 'active', 'episode': int(prev.get('episode') or 1) + 1,
                   'first_seen_at': now, 'last_seen_at': now, 'resolved_at': None, 'notified': {}}
        else:
            doc = {**prev, **cond, 'state': 'active', 'last_seen_at': now}   # same condition: nothing new
        writes[key] = doc
        active[key] = doc

    for key, prev in stored.items():
        if key in current or prev.get('state') != 'active':
            continue
        if _still_low(db, prev):
            writes[key] = {**prev, 'last_seen_at': now}
            active[key] = writes[key]
        else:
            writes[key] = {**prev, 'state': 'resolved', 'resolved_at': now}

    if persist and writes:
        batch = db.batch()
        for key, doc in writes.items():
            batch.set(db.collection(ALERTS).document(key), doc)
        batch.commit()

    rank = {t: i for i, t in enumerate(PRIORITY)}
    ordered = sorted(active.items(), key=lambda kv: (rank.get(kv[1]['type'], 99), str(kv[1].get('label') or ''), kv[0]))
    return [{**doc, 'key': key} for key, doc in ordered]


# ---------- who should hear about what ----------

def default_prefs():
    return {'muted_types': [], 'muted_keys': {}, 'paused': False}


def get_prefs(db, phone):
    snap = db.collection(CONTACTS).document(phone).get()
    stored = ((snap.to_dict() or {}).get('alert_prefs') or {}) if snap.exists else {}
    return {**default_prefs(), **stored}


def is_muted(alert, prefs):
    return bool(prefs.get('paused')) or alert['type'] in (prefs.get('muted_types') or []) \
        or alert['key'] in (prefs.get('muted_keys') or {})


def announceable(alerts, phone, prefs, now):
    """The alerts this number has not heard about yet, is not muting, and whose key is out of cooldown"""
    result = []
    for alert in alerts:
        if is_muted(alert, prefs) or phone in (alert.get('notified') or {}):
            continue
        last = _naive_utc((alert.get('last_notified') or {}).get(phone))   # per number, across episodes
        if last is not None and now - last < COOLDOWN:
            continue
        result.append(alert)
    return result


def mark_notified(db, batch, alerts, phone, now):
    """Queue (in `batch`) that `phone` was told about these alerts"""
    for alert in alerts:
        notified = {**(alert.get('notified') or {}), phone: now}
        history = {**(alert.get('last_notified') or {}), phone: now}
        batch.set(db.collection(ALERTS).document(alert['key']),
                  {'notified': notified, 'last_notified': history, 'last_notified_at': now}, merge=True)
