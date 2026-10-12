"""Find bookings (events) by client name / date / status, with the data the agent needs to
ask "which event?": date, client, status and whether supplies / consumption already exist."""
from datetime import date, datetime

from services import event_inventory_service as events
from utils.text_matching import calculate_similarity, normalize_text

BOOKINGS = 'bookings'
DAY_NAMES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
NAME_THRESHOLD = 0.7
MAX_SCANNED = 300


_SERVICE_NAMES = {'workshop': 'Pizzeros en Acción', 'pizzeros': 'Pizzeros en Acción', 'pizza_party': 'Pizza Party',
                  'party': 'Pizza Party'}


def service_label(service_type):
    """'workshop' / 'pizza_party' / 'pizzeros,party' (how bookings store it) -> 'Pizzeros en Acción + Pizza Party'; anything else as is"""
    parts = [p.strip() for p in str(service_type or '').split(',') if p.strip()]
    return ' + '.join(dict.fromkeys(_SERVICE_NAMES.get(p.lower(), p[:40]) for p in parts))


def event_day(event_date):
    """'2026-10-20T16:00:00' or '2026-10-20' -> '2026-10-20' (the public form stores the first kind)"""
    return str(event_date)[:10] if event_date else None


def _day_of_week(event_date):
    try:
        return DAY_NAMES[datetime.strptime(event_day(event_date), '%Y-%m-%d').weekday()]
    except (TypeError, ValueError):
        return None


def _name_matches(needle, name):
    candidate = normalize_text(name)
    return needle in candidate or any(
        calculate_similarity(needle, token) >= NAME_THRESHOLD for token in candidate.split())


def _proximity(event_date, today):
    """Upcoming events first (soonest first), then past ones (most recent first)"""
    try:
        delta = (datetime.strptime(event_day(event_date), '%Y-%m-%d').date() - today).days
    except (TypeError, ValueError):
        return (2, 0)
    return (0, delta) if delta >= 0 else (1, -delta)


def search_bookings(db, client_name=None, date_from=None, date_to=None, status=None, limit=8):
    """Matching bookings: exact name matches first, nearest to today first. Cancelled ones are
    skipped unless asked for.

    At most ONE Firestore filter is used (no composite indexes needed); the rest is filtered here.
    """
    query = db.collection(BOOKINGS)
    if date_from or date_to:
        if date_from:
            query = query.where('event_date', '>=', date_from)
        if date_to:
            # '~' sorts after any time suffix, so "2026-10-25T16:00:00" still falls inside date_to="2026-10-25"
            query = query.where('event_date', '<=', date_to + '~')
    elif status:
        query = query.where('status', '==', status)
    query = query.limit(MAX_SCANNED)

    needle = normalize_text(client_name) if client_name else ''
    today = date.today()
    found = []
    for snapshot in query.stream():
        booking = snapshot.to_dict()
        if status and booking.get('status') != status:
            continue
        if not status and booking.get('status') == 'cancelled':
            continue
        if needle and not _name_matches(needle, booking.get('client_name', '')):
            continue
        found.append((snapshot.id, booking))

    # exact name matches first, fuzzy ones (typos, "Martín" for "Martina") after; each group by date proximity
    found.sort(key=lambda row: (
        0 if not needle or needle in normalize_text(row[1].get('client_name', '')) else 1,
        _proximity(row[1].get('event_date'), today)))

    results = []
    for booking_id, booking in found[:limit]:
        supplies = events.get_supplies_for_booking(db, booking_id)
        consumption = events.get_consumption_for_booking(db, booking_id)
        results.append({
            'id': booking_id,
            'client_name': booking.get('client_name'),
            'service_type': booking.get('service_type'),
            'event_date': event_day(booking.get('event_date')),
            'day_of_week': _day_of_week(booking.get('event_date')),
            'event_time': booking.get('event_time'),
            'participants': booking.get('participants'),
            'status': booking.get('status'),
            'location': booking.get('location'),
            'has_supplies': supplies is not None,
            'estimated_supply_cost': supplies.get('estimated_total_cost') if supplies else None,
            'has_consumption': consumption is not None,
        })
    return results
