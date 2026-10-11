"""AI agent: propose supplies (estimate) and consumption (real) for an event (propose -> confirm).

  event_supplies     what is taken to the event. An estimate: it does NOT move stock.
  event_consumption  what was really consumed. It DEDUCTS stock; registering again replaces the previous
                     consumption (its movements are reverted and its stock given back).

Every write goes through event_inventory_service, which validates first and applies atomically. Ids are
derived from the action id, so confirming a retried action rewrites the same documents.
"""
import uuid
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from services import event_inventory_service as ev
from services import pending_actions_service as pending
from services.inventory_proposals import ProposalError

SUPPLIES_TYPE = 'event_supplies'
CONSUMPTION_TYPE = 'event_consumption'
VARIANCE_WARNING_RATIO = 0.3


def _id(action_id, key):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'{action_id}:{key}'))


def _clp(n):
    return '$' + f'{round(n):,}'.replace(',', '.')


def _qty(n):
    return f'{n:g}'


# ---------- payload models ----------

class SuppliesItem(BaseModel):
    item_id: str = Field(min_length=1)
    estimated_quantity: float = Field(gt=0, le=1_000_000)
    notes: Optional[str] = Field(default=None, max_length=200)


class SuppliesPayload(BaseModel):
    booking_id: str = Field(min_length=1)
    items: list[SuppliesItem] = Field(min_length=1, max_length=60)
    notes: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode='after')
    def _unique_items(self):
        ids = [i.item_id for i in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError('un insumo aparece más de una vez')
        return self


class ConsumptionItem(BaseModel):
    item_id: str = Field(min_length=1)
    quantity_returned: Optional[float] = Field(default=None, ge=0, le=1_000_000)   # what came back
    actual_quantity_consumed: Optional[float] = Field(default=None, ge=0, le=1_000_000)

    @model_validator(mode='after')
    def _exactly_one(self):
        if (self.quantity_returned is None) == (self.actual_quantity_consumed is None):
            raise ValueError('indica quantity_returned O actual_quantity_consumed (uno solo)')
        return self


class ConsumptionPayload(BaseModel):
    booking_id: str = Field(min_length=1)
    items: list[ConsumptionItem] = Field(min_length=1, max_length=60)
    total_other_expenses: int = Field(default=0, ge=0, le=100_000_000)
    notes: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode='after')
    def _unique_items(self):
        ids = [i.item_id for i in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError('un insumo aparece más de una vez')
        return self


# ---------- executors (run only from pending_actions.confirm) ----------

def _supplies_request(payload):
    return {
        'booking_id': payload.booking_id,
        'items': [{'item_id': i.item_id, 'estimated_quantity': i.estimated_quantity, 'notes': i.notes} for i in payload.items],
        'notes': payload.notes,
    }


def _booking_financials(db, booking_id):
    snapshot = db.collection(ev.BOOKINGS).document(booking_id).get()
    return ((snapshot.to_dict() or {}).get('financials') or {}) if snapshot.exists else {}


def _execute_supplies(db, payload, user, action_id):
    request = _supplies_request(payload)
    existing = ev.get_supplies_for_booking(db, payload.booking_id)
    own_id = _id(action_id, 'supplies')
    # What undo needs to put things back as they were. When this confirmation is a retry of one that already wrote
    # (our own document exists) the "before" is gone: those keys are left out and undo answers "antigua".
    undo_data = {}
    if existing is None or existing['id'] != own_id:
        undo_data = {
            'created': existing is None,
            'previous': None if existing is None else {
                key: existing.get(key) for key in ('items', 'notes', 'estimated_total_cost')},
            'prev_estimated_supply_cost': _booking_financials(db, payload.booking_id).get('estimated_supply_cost'),
        }
    try:
        if existing:
            supplies = ev.update_supplies(db, existing['id'], request)
            supplies_id = existing['id']
        else:
            supplies_id, supplies = ev.create_supplies(db, request, supplies_id=own_id)
    except ev.EventInventoryError as exc:
        raise RuntimeError(exc.message)
    return {'supplies_id': supplies_id, 'estimated_total_cost': supplies['estimated_total_cost'],
            'replaced': existing is not None and existing['id'] != own_id, **undo_data}


def _consumption_request(payload):
    items = []
    for item in payload.items:
        entry = {'item_id': item.item_id}
        if item.quantity_returned is not None:
            entry['quantity_returned'] = item.quantity_returned
        else:
            entry['actual_quantity_consumed'] = item.actual_quantity_consumed
        items.append(entry)
    return items


FINANCIAL_KEYS = ('total_expenses', 'supply_cost', 'other_expenses', 'profit')


def _execute_consumption(db, payload, user, action_id):
    own_id = _id(action_id, 'consumption')
    existing = ev.get_consumption_for_booking(db, payload.booking_id)
    # Undo data (see _execute_supplies): skipped when this is a retry of a confirmation that already wrote
    undo_data = {}
    if existing is None or existing['id'] != own_id:
        before = _booking_financials(db, payload.booking_id)
        undo_data = {'replaced': existing is not None,
                     'prev_financials': {key: before[key] for key in FINANCIAL_KEYS if key in before}}
    try:
        consumption_id, saved = ev.save_consumption(
            db, payload.booking_id, _consumption_request(payload), payload.total_other_expenses,
            notes=payload.notes, consumption_id=own_id,
            movement_ids=lambda index: _id(action_id, f'movement:{index}'))
    except ev.EventInventoryError as exc:
        raise RuntimeError(exc.message)
    count = len(saved['items_consumed'])
    if undo_data:
        undo_data['movement_ids'] = [_id(action_id, f'movement:{index}') for index in range(count)]
    return {'consumption_id': consumption_id, 'total_cost': saved['total_cost'],
            'total_supply_cost': saved['total_supply_cost'], 'items': count, **undo_data}


pending.register_action_type(SUPPLIES_TYPE, SuppliesPayload, _execute_supplies)
pending.register_action_type(CONSUMPTION_TYPE, ConsumptionPayload, _execute_consumption)


# ---------- proposals ----------

def _booking_or_error(db, booking_id):
    snapshot = db.collection(ev.BOOKINGS).document(booking_id).get()
    if not snapshot.exists:
        raise ProposalError(f"No existe la reserva {booking_id}. Búscala con search_bookings.")
    booking = snapshot.to_dict()
    if booking.get('status') != 'confirmed':
        raise ProposalError(
            f"La reserva de {booking.get('client_name')} está '{booking.get('status')}': solo se pueden cargar insumos o "
            "consumo a reservas confirmadas. Si ya se completó, edítala desde el panel.")
    return {'id': booking_id, 'client_name': booking.get('client_name'), 'event_date': booking.get('event_date'),
            'status': booking.get('status'), 'participants': booking.get('participants'),
            'service_type': booking.get('service_type')}


def _label(booking):
    return f"{booking['client_name']} ({booking['event_date']})"


def propose_event_supplies(db, tool_input, user, attachments=None):
    payload = SuppliesPayload.model_validate(tool_input)
    booking = _booking_or_error(db, payload.booking_id)

    rows, total, warnings = [], 0, []
    for item in payload.items:
        snapshot = db.collection(ev.INVENTORY).document(item.item_id).get()
        if not snapshot.exists:
            raise ProposalError(f"No existe el insumo {item.item_id}. Búscalo con search_inventory.")
        stock_item = snapshot.to_dict()
        if stock_item['current_stock'] < item.estimated_quantity:
            raise ProposalError(
                f"No hay stock suficiente de {stock_item['name']}: disponible {_qty(stock_item['current_stock'])} "
                f"{stock_item['unit']}, pedido {_qty(item.estimated_quantity)}.")
        cost = stock_item.get('weighted_avg_cost', stock_item.get('cost_per_unit', 0))
        total += item.estimated_quantity * cost
        rows.append({'item_id': item.item_id, 'item_name': stock_item['name'], 'unit': stock_item['unit'],
                     'current_stock': stock_item['current_stock'], 'cost_per_unit': cost})

    existing = ev.get_supplies_for_booking(db, payload.booking_id)
    if existing:
        warnings.append(f"Esta reserva ya tiene una estimación ({len(existing.get('items', []))} insumos, "
                        f"{_clp(existing.get('estimated_total_cost', 0))}). Confirmar la REEMPLAZA.")
    summary = f"Insumos para {_label(booking)}: {len(payload.items)} insumo(s) · costo estimado {_clp(total)}"
    return pending.create(
        db, SUPPLIES_TYPE, payload.model_dump(mode='json'), summary, user, warnings=warnings, attachments=attachments,
        context={'booking': booking, 'rows': rows, 'replaces': existing is not None})


def propose_event_consumption(db, tool_input, user, attachments=None):
    payload = ConsumptionPayload.model_validate(tool_input)
    booking = _booking_or_error(db, payload.booking_id)

    existing = ev.get_consumption_for_booking(db, payload.booking_id)
    supplies = ev.get_supplies_for_booking(db, payload.booking_id)
    try:
        plan = ev.plan_consumption(db, payload.booking_id, _consumption_request(payload), payload.total_other_expenses,
                                   supplies=supplies, existing=existing)
    except ev.EventInventoryError as exc:
        raise ProposalError(exc.message)

    warnings = []
    if existing:
        warnings.append(f"Esta reserva ya tiene un consumo registrado ({_clp(existing.get('total_cost', 0))}). "
                        "Confirmar lo REEMPLAZA: se devuelve ese stock y se descuenta el nuevo.")
    if not supplies:
        warnings.append('La reserva no tiene estimación de insumos: el consumo se registra directo, sin variación.')
    estimated_ids = {i['item_id'] for i in (supplies or {}).get('items', [])}
    rows = []
    for row in plan['rows']:
        rows.append({k: row[k] for k in ('item_id', 'item_name', 'unit', 'estimated_quantity', 'quantity_returned',
                                         'actual_quantity_consumed', 'cost_per_unit', 'total_cost', 'variance')}
                    | {'stock_before': row['_stock_before'], 'stock_after': row['_stock_before'] - row['actual_quantity_consumed']})
        if supplies and row['item_id'] not in estimated_ids:
            warnings.append(f"{row['item_name']} no estaba en la estimación de insumos.")
        elif row['estimated_quantity'] and row['variance'] is not None \
                and row['variance'] > row['estimated_quantity'] * VARIANCE_WARNING_RATIO:
            warnings.append(f"{row['item_name']}: se consumió {_qty(row['actual_quantity_consumed'])} {row['unit']}, "
                            f"{round(row['variance'] / row['estimated_quantity'] * 100)} % más de lo estimado "
                            f"({_qty(row['estimated_quantity'])}).")
    for item in payload.items:
        planned = next(r for r in plan['rows'] if r['item_id'] == item.item_id)
        if item.quantity_returned is not None and planned['estimated_quantity'] == 0:
            warnings.append(f"{planned['item_name']}: no hay cantidad estimada, así que 'volvió' no permite calcular el "
                            "consumo (quedó en 0). Indica la cantidad consumida.")
    if payload.total_other_expenses == 0:
        warnings.append('Otros gastos del evento en $0. Si hubo bencina u otros gastos, edítalo en la tarjeta.')

    summary = (f"Consumo de {_label(booking)}: {len(payload.items)} insumo(s) · insumos {_clp(plan['total_supply_cost'])} + "
               f"otros {_clp(plan['other_expenses'])} = {_clp(plan['total_cost'])}")
    return pending.create(
        db, CONSUMPTION_TYPE, payload.model_dump(mode='json'), summary, user, warnings=warnings, attachments=attachments,
        context={'booking': booking, 'rows': rows, 'replaces': existing is not None,
                 'total_supply_cost': plan['total_supply_cost']})
