"""Booking creation and pricing, shared by the public HTTP endpoint and the AI agent.

`calculate_estimated_price` used to exist twice (main.py and routes/bookings_routes.py); this is the single
copy (a test proves both old versions agree with it). Creating a booking keeps every behavior of the public
endpoint: customer linking, `pending` status, the WhatsApp/e-mail notification to the admin side.

What a created booking triggers (documented on purpose, see tests/test_booking_service.py):
  * creating (always `pending`): WhatsApp template `new_booking` to the ADMIN and PARTNER numbers + e-mail to the admin.
  * NOTHING goes to the customer. Customer notifications only happen when a booking becomes `confirmed`
    (update_booking in routes/bookings_routes.py) and the AI agent has no way to confirm a booking.
"""
import asyncio
import os
import re
import uuid
from datetime import datetime

from firebase_admin import firestore

from services.email_service import send_admin_email_notification
from services.whatsapp_service import send_whatsapp_template
from utils.text_matching import normalize_text

try:
    from config import PricingConfig
except Exception:  # noqa: BLE001 - same fallback the routes always had
    class PricingConfig:
        PIZZEROS_MINIMUM = 135000
        PIZZA_PARTY_BASE_PRICE = 11990

        @staticmethod
        def get_pizzeros_price(p):
            return 13500 if p <= 10 else (10500 if p <= 14 else (9500 if p <= 19 else 9000))

        @staticmethod
        def get_pizza_party_price(pizzas):
            return round(PricingConfig.PIZZA_PARTY_BASE_PRICE * 0.9) if pizzas >= 20 else PricingConfig.PIZZA_PARTY_BASE_PRICE

VALID_SOURCES = {'website', 'instagram', 'tiktok', 'word_of_mouth', 'other'}


class BookingError(Exception):
    """Carries the message and HTTP status the public endpoint answered with"""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def calculate_estimated_price(service_types, pizzeros_participants=0, party_participants=0, participants=0,
                              pizza_quantity=0, comuna_lejana_extra=0):
    """Price from the services (comma separated: workshop|pizzeros, pizza_party|party), people / pizzas and
    the distant-commune surcharge. Pizzeros: tiered per child, with a minimum up to 10. Pizza Party: per pizza."""
    total = 0
    for service in [x.strip() for x in service_types.split(',') if x.strip()]:
        if service in ["workshop", "pizzeros"]:
            people = pizzeros_participants or participants
            if people > 0:
                total += max(PricingConfig.PIZZEROS_MINIMUM if people <= 10 else 0, people * PricingConfig.get_pizzeros_price(people))
        elif service in ["pizza_party", "party"]:
            pizzas = pizza_quantity or party_participants or participants
            if pizzas > 0:
                total += pizzas * PricingConfig.get_pizza_party_price(pizzas)
    total += comuna_lejana_extra
    return round(total, 2)


def notify_new_booking(booking):
    """WhatsApp (admin + partner) and e-mail (admin). Best effort: a notification failure never fails a booking."""
    try:
        for phone in [os.getenv('ADMIN_WHATSAPP_NUMBER', '+56998960858'), os.getenv('PARTNER_WHATSAPP_NUMBER', '+56998960858')]:
            asyncio.run(send_whatsapp_template(phone, 'new_booking', booking))
    except Exception:  # noqa: BLE001
        pass
    try:
        send_admin_email_notification(booking)
    except Exception as exc:  # noqa: BLE001
        print(f"Error sending admin email: {exc}")


def create_booking(db, data, booking_id=None, notify=True):
    """Create a `pending` booking, linking or creating its customer. Returns the stored booking.

    With an explicit `booking_id` the call is idempotent: an existing booking is returned untouched
    and nobody is notified twice.
    """
    if not data:
        raise BookingError('No data', 400)
    for field in ['service_type', 'source']:
        if not data.get(field):
            raise BookingError(f'Missing {field}', 400)
    if data['source'] not in VALID_SOURCES:
        raise BookingError(f"Invalid source. Must be one of: {', '.join(VALID_SOURCES)}", 400)

    data = dict(data)
    if data.get('source') != 'other':
        data['source_other'] = ''

    booking_id = booking_id or str(uuid.uuid4())
    ref = db.collection('bookings').document(booking_id)
    existing = ref.get()
    if existing.exists:
        stored = existing.to_dict()
        stored.setdefault('id', booking_id)
        return stored

    comuna_lejana_extra = int(data.get('comuna_lejana_extra', 0))
    estimated_price = calculate_estimated_price(
        data.get('service_type', ''), data.get('pizzeros_participants', 0), data.get('party_participants', 0),
        data.get('participants', 0), data.get('pizza_quantity', 0), comuna_lejana_extra)

    # Customer linking / creation
    customer_id = data.get('customer_id')
    client_email = (data.get('client_email') or '').strip().lower()
    if not customer_id and client_email:
        matches = list(db.collection("customers").where("email", "==", client_email).limit(1).get())
        if matches:
            customer_id = matches[0].id
            print(f"🔗 Linking booking to existing customer: {customer_id}")
        else:
            customer_id = str(uuid.uuid4())
            now = datetime.now()
            db.collection("customers").document(customer_id).set({
                "id": customer_id,
                "name": (data.get('client_name') or '').strip(),
                "email": client_email,
                "phone": (data.get('client_phone') or '').strip(),
                "address": data.get('location'),
                "notes": None,
                "total_bookings": 1,
                "last_booking_date": data.get('event_date'),
                "created_at": now,
                "updated_at": now,
                "is_active": True,
            })
            print(f"✅ New customer created: {customer_id}")

    notes = data.get('special_requests') or data.get('notes', '')
    booking = {"id": booking_id, **data, "customer_id": customer_id, "notes": notes, "status": "pending",
               "created_at": datetime.now(), "estimated_price": estimated_price}
    ref.set(booking)

    if customer_id:
        try:
            db.collection("customers").document(customer_id).update({
                "total_bookings": firestore.Increment(1),
                "last_booking_date": data.get('event_date'),
                "updated_at": datetime.now(),
            })
        except Exception:  # noqa: BLE001
            pass

    if notify:
        notify_new_booking(booking)
    return booking


# ---------------------------------------------------------------------------------------------------------------
# PUBLIC input: the website posts to POST /api/bookings/ without a token, so only a whitelist of fields is kept.
# The AI agent and the panel call create_booking() directly and are NOT affected by this.
# ---------------------------------------------------------------------------------------------------------------
PUBLIC_SERVICE_TYPES = {'workshop', 'pizza_party', 'pizzeros', 'party'}
PUBLIC_EVENT_TYPES = {'birthday', 'corporate', 'school', 'private'}
MAX_NAME, MAX_EMAIL, MAX_PHONE, MAX_TEXT, MAX_SHORT = 100, 120, 20, 1000, 100
MAX_PEOPLE = 500
DEFAULT_COMUNAS_LEJANAS = ['Quilicura', 'Lampa', 'Colina', 'Huechuraba']
DEFAULT_CARGO_COMUNA_LEJANA = 20000
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _public_text(data, key, max_len, label, required=False):
    value = data.get(key)
    if value is None or value == '':
        if required:
            raise BookingError(f'Falta {label}', 400)
        return ''
    if not isinstance(value, str):
        raise BookingError(f'{label} no es válido', 400)
    value = value.strip()
    if required and not value:
        raise BookingError(f'Falta {label}', 400)
    if len(value) > max_len:
        raise BookingError(f'{label} es demasiado largo (máximo {max_len} caracteres)', 400)
    return value


def _public_int(data, key, maximum=MAX_PEOPLE):
    value = data.get(key, 0)
    if value is None or value == '':
        return 0
    if isinstance(value, bool):
        raise BookingError(f'{key} no es válido', 400)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise BookingError(f'{key} no es válido', 400)
    if number != number or number < 0 or number > maximum:
        raise BookingError(f'{key} debe estar entre 0 y {maximum}', 400)
    return int(number)


def _distant_surcharge(db, comuna):
    """CLP surcharge for `comuna` from settings/comunas_lejanas (same source the public form shows), else 0"""
    comunas, cargo = DEFAULT_COMUNAS_LEJANAS, DEFAULT_CARGO_COMUNA_LEJANA
    if db is not None:
        try:
            snapshot = db.collection('settings').document('comunas_lejanas').get()
            if snapshot.exists:
                config = snapshot.to_dict() or {}
                comunas = config.get('comunas', comunas)
                cargo = config.get('cargo', cargo)
        except Exception:  # noqa: BLE001 - settings unreadable: fall back to the defaults the form uses
            pass
    try:
        cargo = int(cargo)
    except (TypeError, ValueError):
        cargo = DEFAULT_CARGO_COMUNA_LEJANA
    if cargo < 0 or not comuna:
        return 0
    wanted = normalize_text(comuna)
    return cargo if wanted in {normalize_text(c) for c in comunas if isinstance(c, str)} else 0


def sanitize_public_booking(data, db=None):
    """Whitelist + validate what the PUBLIC website may send. Unknown / privileged fields (payments, status,
    estimated_price, customer_id, id, notes...) are dropped silently; invalid values raise BookingError(400).
    `comuna_lejana_extra` is decided here: the configured `cargo` only if the event comuna is a configured distant one."""
    if data is None or data == {}:
        return {}  # create_booking answers 'No data'
    if not isinstance(data, dict):
        raise BookingError('Datos inválidos', 400)
    if not data.get('service_type') or not data.get('source'):
        # create_booking answers 'Missing service_type' / 'Missing source' exactly as before
        return {'service_type': data.get('service_type') and 'x' or '', 'source': data.get('source') and 'x' or ''}

    clean = {}
    service_type = _public_text(data, 'service_type', MAX_SHORT, 'el servicio', required=True)
    services = [s.strip() for s in service_type.split(',') if s.strip()]
    if not services or any(s not in PUBLIC_SERVICE_TYPES for s in services):
        raise BookingError('Servicio no válido', 400)
    clean['service_type'] = ','.join(services)

    clean['client_name'] = _public_text(data, 'client_name', MAX_NAME, 'el nombre', required=True)
    email = _public_text(data, 'client_email', MAX_EMAIL, 'el email')
    if email and not _EMAIL_RE.match(email):
        raise BookingError('El email no es válido', 400)
    clean['client_email'] = email
    clean['client_phone'] = _public_text(data, 'client_phone', MAX_PHONE, 'el teléfono')

    event_type = _public_text(data, 'event_type', MAX_SHORT, 'el tipo de evento') or 'private'
    if event_type not in PUBLIC_EVENT_TYPES:
        raise BookingError('Tipo de evento no válido', 400)
    clean['event_type'] = event_type

    event_date = _public_text(data, 'event_date', 40, 'la fecha del evento', required=True)
    try:
        datetime.fromisoformat(event_date)
    except ValueError:
        raise BookingError('La fecha del evento no es válida', 400)
    clean['event_date'] = event_date
    clean['event_time'] = _public_text(data, 'event_time', 10, 'la hora del evento')
    clean['location'] = _public_text(data, 'location', MAX_TEXT, 'la ubicación')
    clean['special_requests'] = _public_text(data, 'special_requests', MAX_TEXT, 'los comentarios')

    hours = data.get('duration_hours', 4)
    try:
        hours = float(hours) if hours not in (None, '') and not isinstance(hours, bool) else 4
    except (TypeError, ValueError):
        raise BookingError('La duración no es válida', 400)
    if not 0 < hours <= 24:
        raise BookingError('La duración debe estar entre 0 y 24 horas', 400)
    clean['duration_hours'] = int(hours) if hours == int(hours) else hours

    for key in ('participants', 'pizzeros_participants', 'party_participants', 'pizza_quantity'):
        clean[key] = _public_int(data, key)

    selected = data.get('services_selected')
    if selected is not None:
        if not isinstance(selected, list) or len(selected) > 5:
            raise BookingError('Los servicios seleccionados no son válidos', 400)
        clean['services_selected'] = [s.strip()[:30] for s in selected if isinstance(s, str) and s.strip()]

    clean['selected_comuna'] = _public_text(data, 'selected_comuna', MAX_SHORT, 'la comuna')
    clean['comuna_lejana_extra'] = _distant_surcharge(db, clean['selected_comuna'])

    clean['source'] = _public_text(data, 'source', MAX_SHORT, 'el origen')
    clean['source_other'] = _public_text(data, 'source_other', MAX_SHORT, 'el detalle del origen')
    return clean


def cancel_pending_booking(db, booking_id, reason, batch=None, now=None):
    """Cancel a booking that is still `pending` WITHOUT notifying anyone (not the customer, not the admin side).

    Used by undo: the customer never heard of a pending booking, so there is nothing to tell them. A booking that
    is already confirmed / completed is refused: the customer was told, cancelling it is a decision for the panel.
    With a `batch` the write is only queued (the caller commits it together with its other writes).
    Returns the booking as it will be stored."""
    ref = db.collection('bookings').document(booking_id)
    snapshot = ref.get()
    if not snapshot.exists:
        raise BookingError('Booking not found', 404)
    booking = snapshot.to_dict()
    if booking.get('status') != 'pending':
        raise BookingError(f"Only a pending booking can be cancelled here (it is {booking.get('status')})", 409)
    now = now or datetime.now()
    fields = {'status': 'cancelled', 'cancel_reason': reason, 'cancelled_at': now, 'updated_at': now}
    if batch is not None:
        batch.update(ref, fields)
    else:
        ref.update(fields)
    return {**booking, **fields}
