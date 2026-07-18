"""
Auto Close Service
Automatically close past events with a fixed profit margin (default 70%).

Replaces the daily WhatsApp reminder loop: instead of nagging the admin to
close events manually, overdue events are closed automatically after
AUTO_CLOSE_DAYS with an AUTO_CLOSE_MARGIN profit margin. The admin is only
notified (once per booking) when an event cannot be closed automatically.
"""
import os
import uuid
import logging
from datetime import datetime, timedelta

from database import get_db

logger = logging.getLogger(__name__)

AUTO_CLOSE_MARGIN = float(os.getenv('AUTO_CLOSE_MARGIN', '0.70'))
AUTO_CLOSE_DAYS = int(os.getenv('AUTO_CLOSE_DAYS', '3'))
AUTO_CLOSE_SOURCE = 'auto_close_70margin'


def parse_event_date(raw) -> str | None:
    """Return ISO date string (YYYY-MM-DD) or None if unparseable."""
    if not raw:
        return None
    if hasattr(raw, 'strftime'):          # datetime / date object
        return raw.strftime('%Y-%m-%d')
    s = str(raw).strip()
    # Accept YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(s[:10], fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def build_event(booking_data: dict, event_cost: float, profit: float,
                source: str = AUTO_CLOSE_SOURCE) -> dict:
    """Build the Firestore event document from booking + financial data."""
    booking_id = booking_data.get('id')
    estimated_price = float(booking_data.get('estimated_price') or 0)
    event_date = parse_event_date(booking_data.get('event_date')) or datetime.now().strftime('%Y-%m-%d')

    service_types = booking_data.get('service_type', '')
    services = [s.strip() for s in service_types.split(',') if s.strip()]

    if len(services) > 1:
        service_name = 'Pizza Party + Pizzeros en Acción'
    elif any(k in services for k in ('workshop', 'pizzeros')):
        service_name = 'Pizzeros en Acción'
    else:
        service_name = 'Pizza Party'

    client_name = booking_data.get('client_name', 'Cliente')
    location = booking_data.get('location', 'nuestra ubicación')
    pizzeros_count = booking_data.get('pizzeros_participants', 0)
    party_guests = booking_data.get('party_guests', booking_data.get('party_participants', 0))
    pizza_qty = booking_data.get('pizza_quantity', 10)

    if len(services) > 1:
        description = (f"Evento de {service_name} con {pizzeros_count} "
                       f"niños en el taller y {party_guests} invitados en la pizza party.")
    elif any(k in services for k in ('workshop', 'pizzeros')):
        description = f"Taller Pizzeros en Acción con {pizzeros_count} participantes."
    else:
        description = f"Pizza Party con {pizza_qty} pizzas para {party_guests} invitados."

    profit_margin_pct = round((profit / estimated_price * 100), 2) if estimated_price > 0 else 0

    return {
        "id": str(uuid.uuid4()),
        "booking_id": booking_id,
        "title": f"{service_name} - {client_name}",
        "description": description,
        "event_date": event_date,
        "participants": booking_data.get('participants', 0),
        "final_price": estimated_price,
        "event_cost": event_cost,
        "profit": profit,
        "notes": f"Evento en {location}. Cliente: {client_name}. Cerrado automáticamente con margen 70%.",
        "status": "completed",
        "created_at": datetime.now(),
        "is_published": False,
        "is_featured": False,
        "category": "workshop" if any(k in services for k in ('workshop', 'pizzeros')) else "party",
        "satisfaction": 5,
        "highlight": service_name,
        "age_group": "Niños y familias",
        "source": source,
        "financials": {
            "income": estimated_price,
            "total_expenses": event_cost,
            "supply_cost": 0,
            "other_expenses": event_cost,
            "profit": profit,
            "profit_margin": profit_margin_pct,
        },
    }


def close_booking(db, booking_data: dict, margin: float = AUTO_CLOSE_MARGIN,
                  source: str = AUTO_CLOSE_SOURCE) -> dict:
    """Close a single booking with the given margin.

    Creates the completed event (if none exists for the booking) and marks the
    booking as completed. Raises on Firestore errors; caller handles them.
    """
    booking_id = booking_data['id']
    estimated_price = float(booking_data.get('estimated_price') or 0)
    event_cost = round(estimated_price * (1 - margin), 2)
    profit = round(estimated_price * margin, 2)

    existing_events = list(
        db.collection('events')
          .where('booking_id', '==', booking_id)
          .limit(1)
          .stream()
    )

    if not existing_events:
        event_doc = build_event(booking_data, event_cost, profit, source=source)
        db.collection('events').document(event_doc['id']).set(event_doc)

    db.collection('bookings').document(booking_id).update({
        'status': 'completed',
        'event_cost': event_cost,
        'event_profit': profit,
        'updated_at': datetime.now(),
    })

    return {'booking_id': booking_id, 'price': estimated_price,
            'cost': event_cost, 'profit': profit}


async def auto_close_overdue_events() -> dict:
    """Close all overdue bookings automatically with the configured margin.

    A booking is overdue when its event_date is AUTO_CLOSE_DAYS or more in the
    past and its status is still pending/confirmed. Bookings without an
    estimated price cannot be closed; the admin gets a single WhatsApp alert
    for those (flagged on the booking so it never repeats).
    """
    db = get_db()
    if not db:
        logger.error("❌ Database connection failed")
        return {'success': False, 'message': 'Database connection failed',
                'closed': 0, 'unclosable': 0}

    cutoff = (datetime.now() - timedelta(days=AUTO_CLOSE_DAYS)).strftime('%Y-%m-%d')
    logger.info(f"🔒 Auto-closing events with date <= {cutoff} (margin {AUTO_CLOSE_MARGIN:.0%})")

    closed = []
    unclosable = []
    errors = 0

    for doc in db.collection('bookings').stream():
        data = doc.to_dict()
        data['id'] = doc.id

        if data.get('status', '') not in ('pending', 'confirmed'):
            continue

        event_date = parse_event_date(data.get('event_date'))
        if not event_date or event_date > cutoff:
            continue

        if float(data.get('estimated_price') or 0) <= 0:
            unclosable.append(data)
            continue

        try:
            result = close_booking(db, data)
            closed.append(result)
            logger.info(f"✅ Auto-closed booking {doc.id} "
                        f"({data.get('client_name', 'Sin nombre')} - {event_date}): "
                        f"profit ${result['profit']:.2f}")
        except Exception as e:
            errors += 1
            logger.error(f"❌ Error auto-closing booking {doc.id}: {e}")

    alerts_sent = await _alert_unclosable(db, unclosable)

    summary = {
        'success': True,
        'message': f'Auto-close completed: {len(closed)} closed, {len(unclosable)} unclosable',
        'closed': len(closed),
        'unclosable': len(unclosable),
        'alerts_sent': alerts_sent,
        'errors': errors,
        'cutoff_date': cutoff,
    }
    logger.info(f"🔒 {summary['message']}")
    return summary


async def _alert_unclosable(db, bookings: list) -> int:
    """Send a one-time WhatsApp alert for bookings that can't be auto-closed."""
    pending_alert = [b for b in bookings if not b.get('auto_close_alert_sent')]
    if not pending_alert:
        return 0

    from services.whatsapp_service import send_whatsapp_notification

    admin_phone = os.getenv('ADMIN_WHATSAPP_NUMBER', '+56989424566')
    lines = [f"- {b.get('client_name', 'Sin nombre')} ({parse_event_date(b.get('event_date')) or 'sin fecha'})"
             for b in pending_alert[:10]]
    message = ("⚠️ Estos eventos pasados no se pudieron cerrar automáticamente "
               "porque no tienen precio estimado. Agrégales un precio en el panel "
               "y se cerrarán solos:\n" + "\n".join(lines))

    try:
        success = await send_whatsapp_notification(admin_phone, message, 'auto_close_unclosable')
    except Exception as e:
        logger.error(f"❌ Error sending unclosable alert: {e}")
        return 0

    if success:
        for b in pending_alert:
            try:
                db.collection('bookings').document(b['id']).update({'auto_close_alert_sent': True})
            except Exception as e:
                logger.error(f"❌ Error flagging booking {b['id']}: {e}")
        return 1
    return 0
