"""Event supplies (estimated stock) and event consumption (confirmed stock): shared by the HTTP
routes in main.py and by the AI agent.

Behavior matches the endpoints these were extracted from (tests/test_event_inventory_routes.py), with
one deliberate improvement: registering a consumption validates EVERYTHING first and then applies the
reversal of the previous consumption, the new movements, the stock updates, the consumption document
and the booking financials in ONE atomic batch. Before, a failure half-way (for example insufficient
stock on the 3rd item) left the old stock already restored and the old movements already deleted.
"""
import uuid
from datetime import datetime

SUPPLIES = 'event_supplies'
CONSUMPTION = 'event_consumption'
BOOKINGS = 'bookings'
INVENTORY = 'inventory'
MOVEMENTS = 'inventory_movements'


class EventInventoryError(Exception):
    """Carries the HTTP status and message the legacy endpoints answered with"""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class BookingNotFound(EventInventoryError):
    def __init__(self):
        super().__init__('Booking not found', 404)


class BookingNotConfirmed(EventInventoryError):
    def __init__(self):
        super().__init__('Booking must be confirmed to add supplies', 400)


class SuppliesNotFound(EventInventoryError):
    def __init__(self):
        super().__init__('Supplies not found', 404)


class InventoryItemNotFound(EventInventoryError):
    def __init__(self, item_id):
        super().__init__(f'Inventory item {item_id} not found', 404)


def _unit_cost(item):
    return item.get('weighted_avg_cost', item.get('cost_per_unit', 0))


def _first(db, collection, booking_id):
    docs = list(db.collection(collection).where('booking_id', '==', booking_id).limit(1).stream())
    return docs[0] if docs else None


# ---------- reads ----------

def get_supplies_for_booking(db, booking_id):
    snapshot = _first(db, SUPPLIES, booking_id)
    return snapshot.to_dict() if snapshot else None


def get_consumption_for_booking(db, booking_id):
    snapshot = _first(db, CONSUMPTION, booking_id)
    return snapshot.to_dict() if snapshot else None


# ---------- supplies (estimate: never moves stock) ----------

def _process_supply_items(db, items, detailed_shortage):
    total, processed = 0, []
    for item in items:
        if not all(k in item for k in ['item_id', 'estimated_quantity']):
            raise EventInventoryError('Each item must have item_id and estimated_quantity', 400)

        snapshot = db.collection(INVENTORY).document(item['item_id']).get()
        if not snapshot.exists:
            raise InventoryItemNotFound(item['item_id'])
        stock_item = snapshot.to_dict()

        if stock_item['current_stock'] < item['estimated_quantity']:
            message = f'Insufficient stock for {stock_item["name"]}'
            if detailed_shortage:
                message += f'. Available: {stock_item["current_stock"]}, Required: {item["estimated_quantity"]}'
            raise EventInventoryError(message, 400)

        cost_per_unit = _unit_cost(stock_item)
        estimated_total_cost = item['estimated_quantity'] * cost_per_unit
        total += estimated_total_cost
        processed.append({
            'item_id': item['item_id'],
            'item_name': stock_item['name'],
            'estimated_quantity': item['estimated_quantity'],
            'unit': stock_item['unit'],
            'cost_per_unit': cost_per_unit,
            'estimated_total_cost': estimated_total_cost,
            'batch_id': item.get('batch_id'),
            'notes': item.get('notes'),
        })
    return processed, total


def _sync_estimated_cost(db, booking_id, total):
    """Mirror the estimate on the booking for the frontend (best effort, like before)"""
    try:
        ref = db.collection(BOOKINGS).document(booking_id)
        snapshot = ref.get()
        if snapshot.exists:
            financials = snapshot.to_dict().get('financials') or {}
            financials['estimated_supply_cost'] = float(total)
            ref.update({'financials': financials, 'updated_at': datetime.now()})
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ Failed to update booking financials with estimated supply cost: {exc}")


def create_supplies(db, data, supplies_id=None):
    """Create the estimate for a confirmed booking. With an explicit `supplies_id` the call is idempotent."""
    if not data or 'booking_id' not in data or 'items' not in data:
        raise EventInventoryError('booking_id and items are required', 400)

    supplies_id = supplies_id or str(uuid.uuid4())
    ref = db.collection(SUPPLIES).document(supplies_id)
    if ref.get().exists:
        return supplies_id, ref.get().to_dict()

    booking = db.collection(BOOKINGS).document(data['booking_id']).get()
    if not booking.exists:
        raise BookingNotFound()
    if booking.to_dict().get('status') != 'confirmed':
        raise BookingNotConfirmed()

    processed, total = _process_supply_items(db, data['items'], detailed_shortage=True)
    supplies = {
        'id': supplies_id,
        'booking_id': data['booking_id'],
        'items': processed,
        'estimated_total_cost': total,
        'notes': data.get('notes'),
        'created_at': datetime.now(),
    }
    ref.set(supplies)
    _sync_estimated_cost(db, data['booking_id'], total)
    return supplies_id, supplies


def update_supplies(db, supplies_id, data):
    """Replace the items and/or notes of an estimate (allowed even if a consumption already exists)"""
    ref = db.collection(SUPPLIES).document(supplies_id)
    snapshot = ref.get()
    if not snapshot.exists:
        raise SuppliesNotFound()

    update = {}
    if 'items' in data:
        processed, total = _process_supply_items(db, data['items'], detailed_shortage=False)
        update['items'] = processed
        update['estimated_total_cost'] = total
    if 'notes' in data:
        update['notes'] = data['notes']
    update['updated_at'] = datetime.now()
    ref.update(update)

    updated = ref.get().to_dict()
    if updated.get('booking_id'):
        _sync_estimated_cost(db, updated['booking_id'], update.get('estimated_total_cost', updated.get('estimated_total_cost', 0)))
    return updated


# ---------- consumption (confirmed: moves stock) ----------

def _as_float(value, default=0.0):
    try:
        return float(value)
    except Exception:  # noqa: BLE001 - legacy tolerance: junk counts as the default
        return default


def plan_consumption(db, booking_id, items_consumed, total_other_expenses, supplies=None, existing=None):
    """Validate a consumption and compute everything it would do, WITHOUT writing.

    Returns a plan: per-item rows, the stock each item would end with, the movements of the previous
    consumption that must be reverted and the totals. Raises EventInventoryError on any invalid input.
    """
    supplies = supplies if supplies is not None else get_supplies_for_booking(db, booking_id)
    other = _as_float(total_other_expenses)

    # 1) what the previous consumption took out of stock (to give it back)
    restore, old_movements = {}, []
    for old_item in (existing or {}).get('items_consumed', []):
        found = db.collection(MOVEMENTS) \
            .where('reference_id', '==', booking_id).where('reference_type', '==', 'event_consumption') \
            .where('item_id', '==', old_item['item_id']).stream()
        for movement in found:
            restore[old_item['item_id']] = restore.get(old_item['item_id'], 0) + abs(movement.to_dict().get('quantity', 0))
            old_movements.append(movement.reference)

    stock, inventory, rows, total_supply_cost = {}, {}, [], 0
    for item_id in restore:
        snapshot = db.collection(INVENTORY).document(item_id).get()
        if snapshot.exists:
            inventory[item_id] = snapshot.to_dict()
            stock[item_id] = round(inventory[item_id]['current_stock'] + restore[item_id], 2)

    # 2) the new consumption, validated against the stock AFTER the give-back
    for item in items_consumed:
        if 'item_id' not in item:
            raise EventInventoryError('Each item must have item_id', 400)
        item_id = item['item_id']

        estimated_item = next((s for s in (supplies or {}).get('items', []) if s['item_id'] == item_id), None)
        estimated = float(estimated_item.get('estimated_quantity', 0) or 0) if estimated_item else 0.0

        if 'quantity_returned' in item:
            returned = _as_float(item.get('quantity_returned'))
            if estimated_item is not None:
                if returned > estimated:
                    raise EventInventoryError(
                        f'La cantidad que volvió ({returned}) no puede ser mayor que lo llevado ({estimated})', 400)
                actual = max(0.0, estimated - returned)
            else:
                actual = _as_float(item.get('actual_quantity_consumed'))
        else:
            try:
                actual = float(item.get('actual_quantity_consumed') or 0)
            except Exception:  # noqa: BLE001
                raise EventInventoryError('Each item must have quantity_returned or actual_quantity_consumed', 400)
        actual = max(0.0, actual)

        if item_id not in inventory:
            snapshot = db.collection(INVENTORY).document(item_id).get()
            if not snapshot.exists:
                raise InventoryItemNotFound(item_id)
            inventory[item_id] = snapshot.to_dict()
            stock[item_id] = inventory[item_id]['current_stock']
        stock_item = inventory[item_id]

        if stock[item_id] < actual:
            raise EventInventoryError(
                f'Insufficient stock for {stock_item["name"]}. Available: {stock[item_id]}, Required: {actual}', 400)

        cost_per_unit = _unit_cost(stock_item)
        total_cost = actual * cost_per_unit
        total_supply_cost += total_cost
        rows.append({
            'item_id': item_id,
            'item_name': stock_item['name'],
            'estimated_quantity': estimated,
            'quantity_returned': item.get('quantity_returned', 0),
            'actual_quantity_consumed': actual,
            'unit': stock_item['unit'],
            'cost_per_unit': cost_per_unit,
            'total_cost': total_cost,
            'batch_id': item.get('batch_id'),
            'variance': (actual - estimated) if estimated_item is not None else None,
            '_stock_before': stock[item_id],
        })
        stock[item_id] = stock[item_id] - actual

    return {
        'rows': rows, 'stock': stock, 'inventory': inventory, 'old_movements': old_movements,
        'restore': restore, 'supplies': supplies, 'total_supply_cost': total_supply_cost,
        'other_expenses': other, 'total_cost': total_supply_cost + other,
        'replaces_existing': existing is not None,
    }


def save_consumption(db, booking_id, items_consumed, total_other_expenses, notes=None, event_id=None,
                     consumption_id=None, movement_ids=None):
    """Register the real consumption of a booking and move stock. Registering again replaces the
    previous consumption (its movements are reverted and its stock given back).

    `consumption_id` / `movement_ids` (a callable item_index -> id) make the write deterministic, so a retry
    of the same call rewrites the same documents.
    """
    booking_ref = db.collection(BOOKINGS).document(booking_id)
    booking = booking_ref.get()
    if not booking.exists:
        raise BookingNotFound()
    booking_data = booking.to_dict()

    existing_snapshot = _first(db, CONSUMPTION, booking_id)
    existing = existing_snapshot.to_dict() if existing_snapshot else None
    plan = plan_consumption(db, booking_id, items_consumed, total_other_expenses, existing=existing)

    now = datetime.now()
    batch = db.batch()

    for reference in plan['old_movements']:
        batch.delete(reference)

    for index, row in enumerate(plan['rows']):
        movement_id = movement_ids(index) if movement_ids else str(uuid.uuid4())
        quantity = row['actual_quantity_consumed']
        batch.set(db.collection(MOVEMENTS).document(movement_id), {
            'id': movement_id,
            'item_id': row['item_id'],
            'item_name': row['item_name'],
            'movement_type': 'sale',  # outbound: consumption at an event
            'quantity': -quantity,
            'unit': row['unit'],
            'cost_per_unit': row['cost_per_unit'],
            'total_cost': row['total_cost'],
            'reference_id': booking_id,
            'reference_type': 'event_consumption',
            'notes': f"Consumo en evento - {notes or ''}",
            'stock_before': row['_stock_before'],
            'stock_after': row['_stock_before'] - quantity,
            'avg_cost_before': row['cost_per_unit'],
            'avg_cost_after': row['cost_per_unit'],
            'created_at': now,
        })

    for item_id, final_stock in plan['stock'].items():
        final_stock = round(final_stock, 2)
        batch.update(db.collection(INVENTORY).document(item_id), {
            'current_stock': final_stock,
            'needs_restock': final_stock <= plan['inventory'][item_id].get('min_stock', 0),
            'last_updated': now,
        })

    processed = [{k: v for k, v in row.items() if not k.startswith('_')} for row in plan['rows']]
    fields = {
        'items_consumed': processed,
        'total_supply_cost': plan['total_supply_cost'],
        'total_other_expenses': plan['other_expenses'],
        'total_cost': plan['total_cost'],
        'notes': notes,
    }
    if existing_snapshot:
        consumption_id = existing_snapshot.id
        batch.update(db.collection(CONSUMPTION).document(consumption_id), {**fields, 'updated_at': now})
        saved = {**existing, **fields, 'updated_at': now}
    else:
        consumption_id = consumption_id or str(uuid.uuid4())
        saved = {
            'id': consumption_id, 'event_id': event_id, 'booking_id': booking_id, **fields,
            'supplies_id': plan['supplies']['id'] if plan['supplies'] else None, 'created_at': now,
        }
        batch.set(db.collection(CONSUMPTION).document(consumption_id), saved)

    financials = booking_data.get('financials') or {}
    financials.update({
        'total_expenses': plan['total_cost'],
        'supply_cost': plan['total_supply_cost'],
        'other_expenses': plan['other_expenses'],
    })
    if 'income' in financials:
        financials['profit'] = financials['income'] - plan['total_cost']
    batch.update(booking_ref, {'financials': financials, 'updated_at': now})

    batch.commit()  # reversal + new movements + stock + consumption + booking: all or nothing
    return consumption_id, saved
