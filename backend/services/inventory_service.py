"""Inventory business logic shared by the HTTP routes (main.py) and the AI agent.

Pure functions over a Firestore client, no Flask objects. Semantics match the
endpoints they were extracted from (see tests/test_inventory_routes.py), with
two deliberate improvements:
  * stock + movement are written in ONE atomic batch (before: two separate writes);
  * `movement_id` / `item_id` may be supplied to make a call idempotent, which is
    what lets a retried AI confirmation never duplicate a purchase or an item.
"""
import uuid
from datetime import datetime

INVENTORY = 'inventory'
MOVEMENTS = 'inventory_movements'

INBOUND_TYPES = ('purchase', 'production', 'return', 'adjustment')
REQUIRED_ITEM_FIELDS = ('name', 'category', 'current_stock', 'min_stock', 'max_stock', 'unit', 'cost_per_unit')
NUTRITION_FIELDS = (
    'calories', 'proteins', 'carbohydrates', 'sugars', 'fats', 'saturated_fats', 'trans_fats',
    'unsaturated_fats', 'fiber', 'sodium', 'cholesterol', 'calcium', 'iron',
)


class ItemNotFound(Exception):
    pass


class MissingField(ValueError):
    def __init__(self, field):
        super().__init__(f"Missing {field}")
        self.field = field


class InvalidMovement(ValueError):
    pass


class InvalidOperation(ValueError):
    pass


class InsufficientStock(ValueError):
    pass


# ---------- items ----------

def _nutrition(info):
    info = info or {}
    result = {field: float(info.get(field, 0)) for field in NUTRITION_FIELDS}
    result['allergens'] = info.get('allergens', '')
    return result


def create_item(db, data, item_id=None, extra=None):
    """Create an item. With an explicit `item_id` the call is idempotent (returns the existing one)."""
    for field in REQUIRED_ITEM_FIELDS:
        if field not in data:
            raise MissingField(field)

    item_id = item_id or str(uuid.uuid4())
    ref = db.collection(INVENTORY).document(item_id)
    existing = ref.get()
    if existing.exists:
        stored = existing.to_dict()
        stored.setdefault('id', item_id)
        return stored

    current_stock = float(data['current_stock'])
    min_stock = float(data['min_stock'])
    cost_per_unit = float(data['cost_per_unit'])
    item = {
        'id': item_id,
        'name': data['name'],
        'product_type': data.get('product_type', 'raw_material'),
        'category': data['category'],
        'current_stock': current_stock,
        'min_stock': min_stock,
        'max_stock': float(data['max_stock']),
        'unit': data['unit'],
        'cost_per_unit': cost_per_unit,
        'weighted_avg_cost': cost_per_unit,
        'supplier': data.get('supplier', ''),
        'notes': data.get('notes', ''),
        'batch_size': float(data['batch_size']) if data.get('batch_size') else None,
        'shelf_life_days': int(data['shelf_life_days']) if data.get('shelf_life_days') else None,
        'last_updated': datetime.now(),
        'needs_restock': current_stock <= min_stock,
        # Nutritional information per 100g/100ml
        'nutrition_info': _nutrition(data.get('nutrition_info')),
        **(extra or {}),
    }
    ref.set(item)
    return item


def update_item(db, item_id, data):
    ref = db.collection(INVENTORY).document(item_id)
    doc = ref.get()
    if not doc.exists:
        raise ItemNotFound(item_id)

    update = {}
    for key in ('name', 'product_type', 'category', 'unit', 'supplier', 'notes'):
        if key in data:
            update[key] = data[key]
    for key in ('current_stock', 'min_stock', 'max_stock', 'cost_per_unit'):
        if key in data:
            update[key] = float(data[key])
    if 'batch_size' in data:
        update['batch_size'] = float(data['batch_size']) if data['batch_size'] else None
    if 'shelf_life_days' in data:
        update['shelf_life_days'] = int(data['shelf_life_days']) if data['shelf_life_days'] else None
    if 'nutrition_info' in data:
        update['nutrition_info'] = _nutrition(data['nutrition_info'])

    update['last_updated'] = datetime.now()

    if 'current_stock' in update or 'min_stock' in update:
        current = doc.to_dict()
        update['needs_restock'] = update.get('current_stock', current['current_stock']) <= update.get('min_stock', current['min_stock'])

    ref.update(update)
    updated = ref.get()
    result = updated.to_dict()
    result['id'] = updated.id
    return result


def set_stock(db, item_id, new_stock, operation='set'):
    """Direct stock change without a movement record (the legacy PUT /<id>/stock)"""
    ref = db.collection(INVENTORY).document(item_id)
    doc = ref.get()
    if not doc.exists:
        raise ItemNotFound(item_id)

    current = doc.to_dict()
    if operation == 'set':
        final_stock = float(new_stock)
    elif operation == 'add':
        final_stock = current['current_stock'] + float(new_stock)
    elif operation == 'subtract':
        final_stock = max(0, current['current_stock'] - float(new_stock))
    else:
        raise InvalidOperation(operation)

    final_stock = round(final_stock, 2)  # avoid float precision noise
    needs_restock = final_stock <= current['min_stock']
    ref.update({'current_stock': final_stock, 'needs_restock': needs_restock, 'last_updated': datetime.now()})
    return {'new_stock': final_stock, 'needs_restock': needs_restock}


# ---------- movements ----------

def _weighted_average(stock_before, avg_before, quantity, unit_cost):
    """New (average cost, total value) after receiving `quantity` at `unit_cost`"""
    if stock_before <= 0:
        return unit_cost, quantity * unit_cost
    total_value = stock_before * avg_before + quantity * unit_cost
    new_stock = stock_before + quantity
    return (total_value / new_stock if new_stock > 0 else avg_before), total_value


def register_movement(db, item_id, movement_type, quantity, cost_per_unit=0, reference_id=None,
                      reference_type=None, notes=None, supplier=None, movement_id=None):
    """Apply a stock movement with weighted-average costing.

    Inbound types (purchase, production, return, adjustment) add stock; any other type
    removes it. A negative `adjustment` removes stock at the current average cost.
    With an explicit `movement_id` the call is idempotent: if that movement already
    exists nothing is written and its recorded result is returned.
    """
    quantity = float(quantity or 0)
    cost_per_unit = float(cost_per_unit or 0)

    item_ref = db.collection(INVENTORY).document(item_id)
    doc = item_ref.get()
    if not doc.exists:
        raise ItemNotFound(item_id)
    current = doc.to_dict()

    movement_id = movement_id or str(uuid.uuid4())
    movement_ref = db.collection(MOVEMENTS).document(movement_id)
    previous = movement_ref.get()
    if previous.exists:
        recorded = previous.to_dict()
        return {
            'movement_id': movement_id, 'already_applied': True,
            'stock_before': recorded['stock_before'], 'stock_after': recorded['stock_after'],
            'avg_cost_before': recorded['avg_cost_before'], 'avg_cost_after': recorded['avg_cost_after'],
            'needs_restock': current.get('needs_restock', False),
        }

    stock_before = current.get('current_stock', 0)
    avg_before = current.get('weighted_avg_cost', current.get('cost_per_unit', 0))
    is_inbound = movement_type in INBOUND_TYPES

    if not is_inbound and quantity > stock_before:
        raise InsufficientStock(f'Stock insuficiente. Stock actual: {stock_before}, cantidad solicitada: {quantity}')

    if is_inbound and quantity > 0:
        new_avg, new_total_value = _weighted_average(stock_before, avg_before, quantity, cost_per_unit)
        new_stock = stock_before + quantity
        actual_quantity = quantity
    elif not is_inbound and quantity > 0:
        new_stock = max(0, stock_before - quantity)
        new_avg = avg_before
        new_total_value = new_stock * new_avg
        actual_quantity = -min(quantity, stock_before)
    elif movement_type == 'adjustment':  # zero or negative adjustment
        new_stock = max(0, stock_before + quantity)
        new_avg = avg_before
        new_total_value = new_stock * new_avg
        actual_quantity = quantity
    else:
        raise InvalidMovement('Invalid movement type or quantity')

    needs_restock = new_stock <= current.get('min_stock', 0)
    now = datetime.now()
    item_update = {
        'current_stock': new_stock,
        'weighted_avg_cost': new_avg,
        'total_value': new_total_value,
        'cost_per_unit': new_avg,  # kept for compatibility with older readers
        'needs_restock': needs_restock,
        'last_updated': now,
    }
    movement = {
        'id': movement_id,
        'item_id': item_id,
        'item_name': current.get('name'),
        'movement_type': movement_type,
        'quantity': actual_quantity,
        'unit': current.get('unit'),
        'cost_per_unit': cost_per_unit,
        'total_cost': abs(actual_quantity) * cost_per_unit,
        'reference_id': reference_id,
        'reference_type': reference_type,
        'notes': notes,
        'supplier': supplier,
        'stock_before': stock_before,
        'stock_after': new_stock,
        'avg_cost_before': avg_before,
        'avg_cost_after': new_avg,
        'created_at': now,
    }

    batch = db.batch()  # stock and its movement record succeed or fail together
    batch.update(item_ref, item_update)
    batch.set(movement_ref, movement)
    batch.commit()

    return {
        'movement_id': movement_id, 'already_applied': False,
        'stock_before': stock_before, 'stock_after': new_stock,
        'avg_cost_before': avg_before, 'avg_cost_after': new_avg,
        'needs_restock': needs_restock,
    }
