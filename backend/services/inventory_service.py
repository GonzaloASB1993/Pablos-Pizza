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


def item_update_fields(data, current):
    """The Firestore update an `update_item(data)` makes on an item currently stored as `current`.
    Split out so callers that must write inside their own atomic batch (undo) build the same update."""
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
        update['needs_restock'] = update.get('current_stock', current['current_stock']) <= update.get('min_stock', current['min_stock'])
    return update


def update_item(db, item_id, data):
    ref = db.collection(INVENTORY).document(item_id)
    doc = ref.get()
    if not doc.exists:
        raise ItemNotFound(item_id)

    ref.update(item_update_fields(data, doc.to_dict()))
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


# ---------- exact reversal of movements (undo) ----------
#
# The weighted-average cost cannot be "un-averaged" once anything else happened to the item, so a movement is
# reverted ONLY if the item is exactly where that movement left it: no later movement of the same item and the
# stored stock / average cost equal the movement's stock_after / avg_cost_after. Exact or not done.

REVERSAL_TYPE = 'reversal'
EXACT_TOLERANCE = 1e-6


class MovementNotRevertible(Exception):
    """`code` is stable (tests, the panel); `message` is what a person is told, always with an alternative"""

    def __init__(self, code, message, movement_id=None, item_id=None):
        super().__init__(message)
        self.code, self.message, self.movement_id, self.item_id = code, message, movement_id, item_id


def _naive_utc(value):
    """Firestore returns timezone-aware datetimes, the fakes and the services use naive ones"""
    if isinstance(value, datetime) and value.tzinfo is not None:
        from datetime import timezone
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _same(a, b, tolerance):
    try:
        return abs(float(a or 0) - float(b or 0)) <= tolerance
    except (TypeError, ValueError):
        return False


def _item_average(item):
    return item.get('weighted_avg_cost', item.get('cost_per_unit', 0))


def _recount_suggestion(name):
    return f"Ya hubo movimientos de {name} después, no lo puedo deshacer exacto. Te propongo un conteo: dime cuánto hay."


def check_movements_revertible(db, movement_ids, tolerance=EXACT_TOLERANCE):
    """Read-only check that every movement can be reverted exactly. Several movements of the same item (two lines
    of one receipt) form a chain: they are reverted together, newest first.

    Returns a plan {'movements': {id: dict}, 'items': {item_id: {'item': dict, 'chain': [movement dicts, oldest first]}}}
    or raises MovementNotRevertible."""
    ids = list(dict.fromkeys(movement_ids))
    movements = {}
    for movement_id in ids:
        snapshot = db.collection(MOVEMENTS).document(movement_id).get()
        if not snapshot.exists:
            raise MovementNotRevertible('missing', 'No encuentro ese movimiento de inventario (¿lo borraron?). '
                                        'Revísalo desde el panel.', movement_id)
        movement = snapshot.to_dict()
        movement.setdefault('id', movement_id)
        if movement.get('reverted'):
            raise MovementNotRevertible('already_reverted', 'Ese movimiento ya fue revertido.', movement_id,
                                        movement.get('item_id'))
        if movement.get('movement_type') == REVERSAL_TYPE:
            raise MovementNotRevertible('is_reversal', 'Eso ya es una reversa, no se puede deshacer.', movement_id,
                                        movement.get('item_id'))
        movements[movement_id] = movement

    by_item = {}
    for movement in movements.values():
        by_item.setdefault(movement.get('item_id'), []).append(movement)

    items = {}
    for item_id, group in by_item.items():
        snapshot = db.collection(INVENTORY).document(item_id).get() if item_id else None
        name = group[0].get('item_name') or item_id
        if snapshot is None or not snapshot.exists:
            raise MovementNotRevertible('item_missing', f'El insumo {name} ya no existe, no puedo deshacerlo exacto. '
                                        'Revísalo desde el panel.', group[0]['id'], item_id)
        item = snapshot.to_dict()
        name = item.get('name') or name

        if any(m.get('created_at') is None for m in group):
            raise MovementNotRevertible('chain', _recount_suggestion(name), group[0]['id'], item_id)
        chain = sorted(group, key=lambda m: _naive_utc(m['created_at']))
        group_ids = {m['id'] for m in chain}
        first_at = _naive_utc(chain[0]['created_at'])
        for other in db.collection(MOVEMENTS).where('item_id', '==', item_id).stream():
            if other.id in group_ids:
                continue
            created = _naive_utc((other.to_dict() or {}).get('created_at'))
            if created is None or created >= first_at:   # filtered in Python: no composite index needed; a tie counts as later
                raise MovementNotRevertible('later_movements', _recount_suggestion(name), chain[0]['id'], item_id)

        for previous, following in zip(chain, chain[1:]):
            if not (_same(following.get('stock_before'), previous.get('stock_after'), tolerance)
                    and _same(following.get('avg_cost_before'), previous.get('avg_cost_after'), tolerance)):
                raise MovementNotRevertible('chain', _recount_suggestion(name), following['id'], item_id)
        last = chain[-1]
        if not (_same(item.get('current_stock'), last.get('stock_after'), tolerance)
                and _same(_item_average(item), last.get('avg_cost_after'), tolerance)):
            raise MovementNotRevertible(
                'stock_changed', f"El stock de {name} cambió después de ese movimiento, no lo puedo deshacer exacto. "
                "Te propongo un conteo: dime cuánto hay.", last['id'], item_id)
        items[item_id] = {'item': item, 'chain': chain}
    return {'movements': movements, 'items': items}


def check_movement_revertible(db, movement_id, tolerance=EXACT_TOLERANCE):
    return check_movements_revertible(db, [movement_id], tolerance)


def revert_movements_exact(db, pairs, reason, batch, plan=None, tolerance=EXACT_TOLERANCE, delete_originals=False,
                           round_stock=False, now=None):
    """Queue in `batch` (the caller commits it) the exact reversal of several movements.

    `pairs`: [(movement_id, reversal_id)]; the reversal ids are deterministic so a retry rewrites the same documents.
    Each item goes back to the stock / average cost it had before its FIRST reverted movement; one `reversal`
    movement per original keeps the history. The original is marked `reverted` (or deleted with `delete_originals`,
    for event consumption, whose movements must not be found again by the next consumption).
    Returns what was done, with the documents that were overwritten (for the audit log)."""
    now = now or datetime.now()
    plan = plan or check_movements_revertible(db, [movement_id for movement_id, _ in pairs], tolerance)
    reversal_ids = dict(pairs)
    done, snapshots = [], {'movements': {}, 'items': {}}

    for item_id, group in plan['items'].items():
        item, chain = group['item'], group['chain']
        for movement in reversed(chain):
            reversal_id = reversal_ids[movement['id']]
            batch.set(db.collection(MOVEMENTS).document(reversal_id), {
                'id': reversal_id, 'item_id': item_id, 'item_name': movement.get('item_name'),
                'movement_type': REVERSAL_TYPE, 'quantity': -(movement.get('quantity') or 0), 'unit': movement.get('unit'),
                'cost_per_unit': movement.get('cost_per_unit', 0), 'total_cost': movement.get('total_cost', 0),
                'reference_id': movement['id'], 'reference_type': 'movement_reversal', 'notes': reason,
                'reverts_movement_id': movement['id'],
                'stock_before': movement.get('stock_after'), 'stock_after': movement.get('stock_before'),
                'avg_cost_before': movement.get('avg_cost_after'), 'avg_cost_after': movement.get('avg_cost_before'),
                'created_at': now,
            })
            original_ref = db.collection(MOVEMENTS).document(movement['id'])
            if delete_originals:
                batch.delete(original_ref)
            else:
                batch.update(original_ref, {'reverted': True, 'reverted_at': now, 'reversal_movement_id': reversal_id})
            snapshots['movements'][movement['id']] = movement
            done.append({'movement_id': movement['id'], 'reversal_id': reversal_id, 'item_id': item_id})

        first = chain[0]
        stock = first.get('stock_before') or 0
        stock = round(stock, 2) if round_stock else stock
        average = first.get('avg_cost_before', _item_average(item))
        batch.update(db.collection(INVENTORY).document(item_id), {
            'current_stock': stock, 'weighted_avg_cost': average, 'cost_per_unit': average,
            'total_value': stock * average, 'needs_restock': stock <= item.get('min_stock', 0), 'last_updated': now,
        })
        snapshots['items'][item_id] = item
    return {'reversals': done, 'snapshots': snapshots}


def revert_movement_exact(db, movement_id, reversal_id, reason, batch, **options):
    """Single-movement form of revert_movements_exact"""
    return revert_movements_exact(db, [(movement_id, reversal_id)], reason, batch, **options)
