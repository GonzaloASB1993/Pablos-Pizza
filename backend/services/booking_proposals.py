"""AI agent: propose a NEW booking (propose -> confirm).

The agent can only propose creating a booking. It is always created `pending` through booking_service,
exactly like the public form does, and the agent has no way to confirm one: confirming (which notifies the
CUSTOMER by WhatsApp and e-mail) stays a manual action in the admin panel.

What confirming a proposal triggers (shown on the card): WhatsApp `new_booking` to the admin and partner
numbers and an e-mail to the admin, the same as a booking made on the website. The customer gets nothing.
"""
import hashlib
import re
import uuid
from datetime import date as Date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from services import booking_service
from services import pending_actions_service as pending
from services.inventory_proposals import ProposalError
from utils.text_matching import normalize_text

ACTION_TYPE = 'booking'
DEFAULT_COMUNAS = ['Quilicura', 'Lampa', 'Colina', 'Huechuraba']
DEFAULT_SURCHARGE = 20000
SERVICE_CODES = {'pizzeros': 'workshop', 'party': 'pizza_party'}  # what the public form stores in service_type
MIN_PARTY_PIZZAS = 10
EMAIL = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
TIME = re.compile(r'^([01]?\d|2[0-3]):[0-5]\d$')


class BookingPayload(BaseModel):
    client_name: str = Field(min_length=2, max_length=120)
    client_email: Optional[str] = Field(default=None, max_length=120)
    client_phone: Optional[str] = Field(default=None, max_length=30)
    services: list[Literal['pizzeros', 'party']] = Field(min_length=1, max_length=2)
    event_date: Date
    event_time: str = '12:00'
    location: str = Field(min_length=3, max_length=200)
    comuna: Optional[str] = Field(default=None, max_length=80)
    pizzeros_participants: int = Field(default=0, ge=0, le=500)
    pizza_quantity: int = Field(default=0, ge=0, le=1000)
    participants: int = Field(default=0, ge=0, le=1000)
    event_type: Literal['birthday', 'corporate', 'school', 'private'] = 'birthday'
    duration_hours: int = Field(default=4, ge=1, le=12)
    special_requests: str = Field(default='', max_length=500)
    source: Literal['website', 'instagram', 'tiktok', 'word_of_mouth', 'other'] = 'other'
    source_other: str = Field(default='Asistente IA', max_length=80)

    @field_validator('client_name', 'location', 'comuna', 'client_phone', mode='before')
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator('client_email', mode='before')
    @classmethod
    def _email(cls, v):
        v = (v or '').strip().lower()
        if v and not EMAIL.match(v):
            raise ValueError('correo inválido')
        return v or None

    @field_validator('event_time')
    @classmethod
    def _time(cls, v):
        if not TIME.match(v):
            raise ValueError('hora inválida (usa HH:MM)')
        hour, minute = v.split(':')
        return f'{int(hour):02d}:{minute}'

    @field_validator('event_date', mode='before')
    @classmethod
    def _date(cls, v):
        from services.expense_proposals import parse_date  # dd-mm-yyyy is how clients write dates
        return parse_date(v)

    @model_validator(mode='after')
    def _consistency(self):
        if 'pizzeros' in self.services and self.pizzeros_participants < 1:
            raise ValueError('Pizzeros en Acción necesita la cantidad de niños (pizzeros_participants)')
        if 'party' in self.services and self.pizza_quantity < 1:
            raise ValueError('Pizza Party necesita la cantidad de pizzas (pizza_quantity)')
        if len(set(self.services)) != len(self.services):
            raise ValueError('servicio repetido')
        return self


def _surcharge(db, comuna):
    """(extra CLP, True if the comuna is a distant one) from the same settings the public form uses"""
    snapshot = db.collection('settings').document('comunas_lejanas').get()
    config = snapshot.to_dict() if snapshot.exists else {}
    comunas = config.get('comunas', DEFAULT_COMUNAS)
    cargo = config.get('cargo', DEFAULT_SURCHARGE)
    distant = bool(comuna) and normalize_text(comuna) in {normalize_text(c) for c in comunas}
    return (cargo if distant else 0), distant


def _booking_data(db, payload):
    """The same fields (and formats) the public website posts, so the admin panel reads it identically"""
    extra, _ = _surcharge(db, payload.comuna)
    total_people = payload.participants or payload.pizzeros_participants
    return {
        'client_name': payload.client_name,
        'client_email': payload.client_email or '',
        'client_phone': payload.client_phone or '',
        'service_type': ','.join(SERVICE_CODES[s] for s in payload.services),
        'event_type': payload.event_type,
        'event_date': f"{payload.event_date.isoformat()}T{payload.event_time}:00",
        'event_time': payload.event_time,
        'location': payload.location,
        'duration_hours': payload.duration_hours,
        'participants': total_people,
        'pizzeros_participants': payload.pizzeros_participants if 'pizzeros' in payload.services else 0,
        'party_participants': 0,
        'pizza_quantity': payload.pizza_quantity if 'party' in payload.services else 0,
        'special_requests': payload.special_requests,
        'services_selected': list(payload.services),
        'comuna_lejana_extra': extra,
        'selected_comuna': payload.comuna or '',
        'source': payload.source,
        'source_other': payload.source_other if payload.source == 'other' else '',
    }


def estimate(db, payload):
    data = _booking_data(db, payload)
    return booking_service.calculate_estimated_price(
        data['service_type'], data['pizzeros_participants'], data['party_participants'], data['participants'],
        data['pizza_quantity'], data['comuna_lejana_extra'])


def dedupe_hash(payload):
    key = '|'.join([normalize_text(payload.client_name), payload.event_date.isoformat(), payload.event_time,
                    ','.join(sorted(payload.services))])
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def _execute(db, payload, user, action_id):
    """Runs only from pending_actions.confirm(). Creates a PENDING booking (the website does the same)."""
    data = _booking_data(db, payload)
    data.update({'created_via': 'ai_agent', 'created_by': user.get('email')})
    booking = booking_service.create_booking(db, data, booking_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f'{action_id}:booking')), notify=True)
    return {'booking_id': booking['id'], 'estimated_price': booking['estimated_price'], 'customer_id': booking.get('customer_id'),
            'status': booking['status']}


pending.register_action_type(ACTION_TYPE, BookingPayload, _execute)


def _clp(n):
    return '$' + f'{round(n):,}'.replace(',', '.')


def propose_booking(db, tool_input, user, attachments=None):
    payload = BookingPayload.model_validate(tool_input)
    if payload.event_date < Date.today():
        raise ProposalError(f"La fecha {payload.event_date.isoformat()} ya pasó. Pide al usuario una fecha futura.")

    price = estimate(db, payload)
    _, distant = _surcharge(db, payload.comuna)
    warnings = []

    # same-day bookings (any format of event_date), cancelled ones excluded
    day = payload.event_date.isoformat()
    same_day = [b.to_dict() for b in db.collection('bookings').where('event_date', '>=', day).where('event_date', '<=', day + '~').stream()
                if b.to_dict().get('status') != 'cancelled']
    if same_day:
        names = ', '.join(f"{b.get('client_name')} ({b.get('event_time') or 'sin hora'})" for b in same_day[:4])
        warnings.append(f"Ese día ya hay {len(same_day)} reserva(s): {names}. Revisa que no se crucen.")
    if payload.client_email:
        match = list(db.collection('customers').where('email', '==', payload.client_email).limit(1).stream())
        if match:
            warnings.append(f"Ya existe el cliente {match[0].to_dict().get('name')} con ese correo: la reserva se vinculará a él.")
    if not payload.client_email and not payload.client_phone:
        warnings.append('Sin correo ni teléfono: no podrás contactar al cliente desde el panel.')
    if distant:
        warnings.append(f"{payload.comuna} es comuna lejana: incluye un cargo de {_clp(_surcharge(db, payload.comuna)[0])}.")
    if 'party' in payload.services and payload.pizza_quantity < MIN_PARTY_PIZZAS:
        warnings.append(f"Pizza Party: el mínimo habitual es {MIN_PARTY_PIZZAS} pizzas.")
    if 'pizzeros' in payload.services and payload.pizzeros_participants <= 10:
        warnings.append('Pizzeros en Acción hasta 10 niños se cobra el mínimo de $135.000.')
    warnings.append('Al confirmar se avisa por WhatsApp (administrador y socio) y por correo al administrador. '
                    'El cliente no recibe nada: la reserva queda PENDIENTE y la confirmas tú en el panel.')

    h = dedupe_hash(payload)
    for action in pending.find_by_dedupe_hash(db, h):
        state = 'ya confirmada' if action['status'] == pending.CONFIRMED else 'pendiente de confirmar'
        warnings.insert(0, f"Posible duplicado: ya hay una propuesta {state} para el mismo cliente, fecha y hora.")
        break

    services = ' + '.join({'pizzeros': 'Pizzeros en Acción', 'party': 'Pizza Party'}[s] for s in payload.services)
    summary = (f"Reserva (pendiente): {payload.client_name} · {services} · {payload.event_date.strftime('%d-%m-%Y')} "
               f"{payload.event_time} · {payload.location} · {_clp(price)}")
    return pending.create(
        db, ACTION_TYPE, payload.model_dump(mode='json'), summary, user, warnings=warnings, attachments=attachments,
        dedupe_hash=h, context={'estimated_price': price, 'comuna_lejana': distant, 'same_day': len(same_day)})
