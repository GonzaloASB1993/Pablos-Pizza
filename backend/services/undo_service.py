"""Undo for actions confirmed through the AI agent (WhatsApp "deshacer" and the web panel).

The rule is EXACT OR NOT DONE: an action is undone only if everything it touched is still exactly as it left it.
A purchase whose item had later movements cannot be "un-averaged", a booking the customer was already told about
cannot be silently cancelled, so those answer with a reason and an alternative instead.

Shape (one registry entry per action type):
    check(db, action)                              -> plan           read-only, raises CannotUndo
    apply(db, action, plan, undo_id, batch, now)   -> dict           only QUEUES writes in `batch`

`undo()` claims the action transactionally (`undo.state`: processing -> done | failed on the ORIGINAL action, whose
`status` stays `confirmed`), then runs check + apply inside ONE Firestore transaction: the inventory documents the plan
relies on are read again with the transaction (so a movement that lands between the check and the commit aborts the
undo instead of being overwritten) and every write plus the `done` marker commits together: all or nothing. A second
call finds `done` and returns the stored result without touching anything.
Ids are deterministic (uuid5 of the undo id), so a retry after a failure rewrites the same documents.

On WhatsApp undoing also goes through propose -> confirm: the `undo` action type below ({target_action_id}) is
proposed by the "deshacer" command and its executor calls undo(). An `undo` can never be undone.
"""
import logging
import uuid
from datetime import datetime, timedelta

from firebase_admin import firestore
from pydantic import BaseModel, Field

from services import booking_service
from services import event_inventory_service as ev
from services import expenses_service as expenses
from services import inventory_service as inv
from services import pending_actions_service as pending

logger = logging.getLogger(__name__)

UNDO_TYPE = 'undo'
WINDOWS = {'whatsapp': timedelta(hours=24), 'panel': timedelta(days=7)}
STALE_PROCESSING = timedelta(minutes=5)       # a crashed undo must not block the action forever
EXPENSE_EDIT_GRACE = timedelta(seconds=5)     # updated_at - created_at below this = never edited
ROUNDING_TOLERANCE = 0.0051                   # event consumption rounds the stock to 2 decimals
FINANCIAL_KEYS = ('total_expenses', 'supply_cost', 'other_expenses', 'profit')
OLD = 'Esa es antigua, hazlo desde el panel.'


class CannotUndo(pending.PendingActionError):
    """The action cannot be undone. `reason` is a stable code; the message always says what to do instead."""
    status_code = 409

    def __init__(self, reason, message, suggestion=None):
        super().__init__(message, status_code=404 if reason == 'not_found' else None)
        self.reason, self.suggestion = reason, suggestion


def source_for(user):
    return 'whatsapp' if str((user or {}).get('uid', '')).startswith('whatsapp:') else 'panel'


def _clp(n):
    return '$' + f'{round(n or 0):,}'.replace(',', '.')


def _naive(value):
    return pending._naive_utc(value)


def _same(a, b, tolerance=1e-6):
    try:
        return abs(float(a or 0) - float(b or 0)) <= tolerance
    except (TypeError, ValueError):
        return a == b


def _rid(undo_id, key):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'{undo_id}:{key}'))


def _from_inventory(exc):
    return CannotUndo(exc.code, exc.message)


# ---------- naming an action in a few words ----------

def label(action):
    """Short human name: 'Compra Líder $23.450', 'Gasto Copec $20.000'..."""
    kind, payload, ctx = action.get('type'), action.get('payload') or {}, action.get('context') or {}
    try:
        if kind == 'expense':
            return f"Gasto {payload.get('supplier', '')} {_clp(payload.get('total'))}".strip()
        if kind == 'inventory_receipt':
            total = payload.get('total')
            total = total if total is not None else sum(line.get('amount') or 0 for line in payload.get('lines', []))
            who = f" {payload['supplier']}" if payload.get('supplier') else ''
            return f'Compra{who} {_clp(total)}'
        if kind == 'inventory_update':
            name = (ctx.get('items') or {}).get(payload.get('item_id'), {}).get('name')
            return f"Cambio en {name}" if name else 'Cambio de insumo'
        if kind == 'stock_adjustment':
            return (action.get('summary') or 'Ajuste de stock').split(':')[0]
        if kind in ('event_supplies', 'event_consumption'):
            client = (ctx.get('booking') or {}).get('client_name')
            what = 'Insumos' if kind == 'event_supplies' else 'Consumo'
            return f'{what} de {client}' if client else what
        if kind == 'booking':
            return f"Reserva de {payload.get('client_name', '')}".strip()
    except Exception:  # noqa: BLE001 - a label is cosmetic
        pass
    return (action.get('summary') or 'esa acción')[:60]


# ---------- per-type: expense ----------

def _expense_doc(db, collection, expense_id):
    """The expense document if it is still there and was never edited, else CannotUndo"""
    if collection not in (expenses.FIXED, expenses.VARIABLE) or not expense_id:
        raise CannotUndo('old', OLD)
    snapshot = db.collection(collection).document(expense_id).get()
    if not snapshot.exists:
        raise CannotUndo('missing', 'Ese gasto ya no existe (¿lo borraron?). Revísalo desde el panel.')
    data = snapshot.to_dict()
    created, updated = _naive(data.get('created_at')), _naive(data.get('updated_at'))
    if created is None or updated is None:
        raise CannotUndo('old', OLD)
    if updated - created >= EXPENSE_EDIT_GRACE:
        raise CannotUndo('edited', 'Ese gasto se editó después de registrarlo, no lo borro por aquí. '
                                   'Corrígelo o bórralo desde el panel.')
    return data


def _check_expense(db, action):
    result = action.get('result') or {}
    data = _expense_doc(db, result.get('collection'), result.get('expense_id'))
    return {'collection': result['collection'], 'expense_id': result['expense_id'], 'data': data,
            'effects': [f"Se borra el gasto {data.get('description')} ({_clp(data.get('amount'))})."]}


def _apply_expense(db, action, plan, undo_id, batch, now):
    batch.delete(db.collection(plan['collection']).document(plan['expense_id']))
    return {'snapshots': {'expenses': {plan['expense_id']: {'collection': plan['collection'], 'data': plan['data']}}}}


# ---------- per-type: inventory_receipt ----------

def _check_receipt(db, action):
    lines = (action.get('result') or {}).get('lines')
    if not isinstance(lines, list) or not lines:
        raise CannotUndo('old', OLD)

    movement_ids, new_items, expense_docs = [], [], {}
    for entry in lines:
        kind = entry.get('classification')
        if kind == 'expense':
            expense_id = entry.get('expense_id')
            expense_docs[expense_id] = (expenses.VARIABLE, _expense_doc(db, expenses.VARIABLE, expense_id))
            continue
        if entry.get('movement_id'):
            movement_ids.append(entry['movement_id'])
        elif kind != 'new':
            raise CannotUndo('old', OLD)
        if kind == 'new':
            new_items.append(entry['item_id'])

    group = None
    if movement_ids:
        try:
            group = inv.check_movements_revertible(db, movement_ids)
        except inv.MovementNotRevertible as exc:
            raise _from_inventory(exc)

    # a new item may only be deleted if nothing else ever happened to it
    new_docs = {}
    for item_id in new_items:
        snapshot = db.collection(inv.INVENTORY).document(item_id).get()
        if not snapshot.exists:
            raise CannotUndo('item_missing', 'El insumo nuevo de esa compra ya no existe. Revísalo desde el panel.')
        item = snapshot.to_dict()
        new_docs[item_id] = item
        mine = {m['id'] for m in (group or {'movements': {}})['movements'].values() if m.get('item_id') == item_id}
        others = [s.id for s in db.collection(inv.MOVEMENTS).where('item_id', '==', item_id).stream() if s.id not in mine]
        if others or (not mine and not _same(item.get('current_stock'), 0)):
            raise CannotUndo('later_movements', inv._recount_suggestion(item.get('name')))

    effects = []
    for item_id, part in (group or {'items': {}})['items'].items():
        first, last = part['chain'][0], part['chain'][-1]
        effects.append(f"{part['item'].get('name')}: stock {last.get('stock_after'):g} → {first.get('stock_before'):g} "
                       f"{part['item'].get('unit') or ''}".rstrip())
    effects += [f"Se borra el insumo nuevo {(db.collection(inv.INVENTORY).document(i).get().to_dict() or {}).get('name')}."
                for i in new_items]
    effects += [f"Se borra el gasto {d.get('description')} ({_clp(d.get('amount'))})." for _, d in expense_docs.values()]
    return {'group': group, 'movement_ids': movement_ids, 'new_items': new_items, 'new_item_docs': new_docs,
            'expenses': expense_docs, 'effects': effects}


def _apply_receipt(db, action, plan, undo_id, batch, now):
    snapshots = {'movements': {}, 'items': {}, 'expenses': {}}
    if plan['group']:
        pairs = [(m, _rid(undo_id, f'reversal:{m}')) for m in plan['movement_ids']]
        done = inv.revert_movements_exact(db, pairs, f"Deshacer compra ({action.get('summary', '')})"[:200], batch,
                                          plan=plan['group'], now=now)
        snapshots.update(done['snapshots'])
    for item_id in plan['new_items']:
        item = db.collection(inv.INVENTORY).document(item_id).get().to_dict()
        snapshots['items'][item_id] = item
        batch.delete(db.collection(inv.INVENTORY).document(item_id))
    for expense_id, (collection, data) in plan['expenses'].items():
        snapshots['expenses'][expense_id] = {'collection': collection, 'data': data}
        batch.delete(db.collection(collection).document(expense_id))
    return {'snapshots': snapshots}


# ---------- per-type: inventory_update ----------

UPDATE_STRINGS = ('supplier', 'notes')


def _check_update(db, action):
    result, payload = action.get('result') or {}, action.get('payload') or {}
    item_id = result.get('item_id') or payload.get('item_id')
    before = result.get('before') if isinstance(result.get('before'), dict) else (action.get('context') or {}).get('before')
    after = result.get('after') if isinstance(result.get('after'), dict) else (payload.get('changes') or {})
    after = {k: v for k, v in (after or {}).items() if v is not None}
    if not item_id or not isinstance(before, dict) or not after:
        raise CannotUndo('old', OLD)
    snapshot = db.collection(inv.INVENTORY).document(item_id).get()
    if not snapshot.exists:
        raise CannotUndo('item_missing', 'Ese insumo ya no existe. Revísalo desde el panel.')
    item = snapshot.to_dict()

    restore = {}
    for key in after:
        value = before.get(key)
        if value is None and key in UPDATE_STRINGS:
            value = ''
        if value is None:
            raise CannotUndo('old', OLD)
        restore[key] = value
    for key, expected in after.items():
        current = item.get(key)
        same = _same(current, expected) if isinstance(expected, (int, float)) and not isinstance(expected, bool) \
            else current == expected
        if not same:
            raise CannotUndo('edited', f"El insumo {item.get('name')} se volvió a editar después ({key}), no lo toco. "
                                       "Corrígelo desde el panel.")
    if all(_same(restore[k], after[k]) if isinstance(after[k], (int, float)) and not isinstance(after[k], bool)
           else restore[k] == after[k] for k in after):
        raise CannotUndo('noop', 'Ese cambio no modificó nada, no hay nada que deshacer.')
    effects = [f"{item.get('name')}: {key} {after[key]} → {restore[key]}" for key in sorted(restore)]
    return {'item_id': item_id, 'item': item, 'restore': restore, 'effects': effects}


def _apply_update(db, action, plan, undo_id, batch, now):
    fields = inv.item_update_fields(plan['restore'], plan['item'])
    batch.update(db.collection(inv.INVENTORY).document(plan['item_id']), fields)
    return {'snapshots': {'items': {plan['item_id']: plan['item']}}}


# ---------- per-type: stock_adjustment ----------

def _check_adjustment(db, action):
    result = action.get('result') or {}
    movement_id = result.get('movement_id')
    if not movement_id:
        if result.get('delta') == 0:
            raise CannotUndo('noop', 'Ese conteo no cambió nada, no hay nada que deshacer.')
        raise CannotUndo('old', OLD)
    try:
        group = inv.check_movement_revertible(db, movement_id)
    except inv.MovementNotRevertible as exc:
        raise _from_inventory(exc)
    part = next(iter(group['items'].values()))
    first, last = part['chain'][0], part['chain'][-1]
    return {'group': group, 'movement_id': movement_id,
            'effects': [f"{part['item'].get('name')}: stock {last.get('stock_after'):g} → {first.get('stock_before'):g} "
                        f"{part['item'].get('unit') or ''}".rstrip()]}


def _apply_adjustment(db, action, plan, undo_id, batch, now):
    done = inv.revert_movement_exact(db, plan['movement_id'], _rid(undo_id, f"reversal:{plan['movement_id']}"),
                                     f"Deshacer ajuste ({action.get('summary', '')})"[:200], batch, plan=plan['group'], now=now)
    return {'snapshots': done['snapshots']}


# ---------- per-type: event_supplies ----------

def _booking(db, booking_id):
    snapshot = db.collection(ev.BOOKINGS).document(booking_id).get()
    return snapshot.to_dict() if snapshot.exists else None


def _check_supplies(db, action):
    result, payload = action.get('result') or {}, action.get('payload') or {}
    if 'created' not in result or 'prev_estimated_supply_cost' not in result:
        raise CannotUndo('old', OLD)
    if not result['created'] and not isinstance(result.get('previous'), dict):
        raise CannotUndo('old', OLD)
    supplies_id = result.get('supplies_id')
    snapshot = db.collection(ev.SUPPLIES).document(supplies_id).get() if supplies_id else None
    if snapshot is None or not snapshot.exists:
        raise CannotUndo('missing', 'Esa estimación de insumos ya no existe. Revísala desde el panel.')
    supplies = snapshot.to_dict()
    booking_id = supplies.get('booking_id') or payload.get('booking_id')
    if ev.get_consumption_for_booking(db, booking_id):
        raise CannotUndo('consumption_exists', 'Ya se registró el consumo de ese evento, no toco la estimación. '
                                              'Corrígela desde el panel.')
    wrote = {(i['item_id'], float(i['estimated_quantity'])) for i in payload.get('items', [])}
    now_items = {(i.get('item_id'), float(i.get('estimated_quantity') or 0)) for i in supplies.get('items', [])}
    if wrote != now_items or (supplies.get('notes') or None) != (payload.get('notes') or None):
        raise CannotUndo('edited', 'Esa estimación se modificó después, no la toco por aquí. Corrígela desde el panel.')
    effects = ['Se borra la estimación de insumos.' if result['created']
               else 'Se vuelve a la estimación anterior de insumos.']
    return {'supplies_id': supplies_id, 'supplies': supplies, 'booking_id': booking_id, 'effects': effects}


def _financials_update(db, booking_id, mutate, batch, now):
    booking = _booking(db, booking_id)
    if booking is None:
        return
    financials = dict(booking.get('financials') or {})
    mutate(financials)
    batch.update(db.collection(ev.BOOKINGS).document(booking_id), {'financials': financials, 'updated_at': now})


def _apply_supplies(db, action, plan, undo_id, batch, now):
    result = action['result']
    ref = db.collection(ev.SUPPLIES).document(plan['supplies_id'])
    if result['created']:
        batch.delete(ref)
    else:
        previous = result['previous']
        batch.update(ref, {'items': previous.get('items'), 'notes': previous.get('notes'),
                           'estimated_total_cost': previous.get('estimated_total_cost'), 'updated_at': now})

    def restore(financials):
        if result['prev_estimated_supply_cost'] is None:
            financials.pop('estimated_supply_cost', None)
        else:
            financials['estimated_supply_cost'] = result['prev_estimated_supply_cost']
    _financials_update(db, plan['booking_id'], restore, batch, now)
    return {'snapshots': {'supplies': {plan['supplies_id']: plan['supplies']}}}


# ---------- per-type: event_consumption ----------

def _check_consumption(db, action):
    result = action.get('result') or {}
    if not all(key in result for key in ('replaced', 'prev_financials', 'movement_ids')):
        raise CannotUndo('old', OLD)
    if result['replaced']:
        raise CannotUndo('replaced', 'Ese consumo reemplazó a uno anterior y no puedo reconstruir el anterior. '
                                     'Corrígelo desde el panel con el consumo correcto.')
    snapshot = db.collection(ev.CONSUMPTION).document(result.get('consumption_id') or '-').get()
    if not snapshot.exists:
        raise CannotUndo('missing', 'Ese consumo ya no existe (¿lo reemplazaron?). Revísalo desde el panel.')
    consumption = snapshot.to_dict()
    if consumption.get('updated_at') is not None:
        raise CannotUndo('edited', 'Ese consumo se modificó después, no lo toco por aquí. Corrígelo desde el panel.')
    booking_id = consumption.get('booking_id')
    booking = _booking(db, booking_id)
    if booking is None:
        raise CannotUndo('missing', 'La reserva de ese consumo ya no existe. Revísalo desde el panel.')
    if booking.get('status') == 'completed':
        raise CannotUndo('booking_completed', 'Ese evento ya está completado, no toco su consumo. Corrígelo desde el panel.')
    financials = booking.get('financials') or {}
    if not (_same(financials.get('total_expenses'), consumption.get('total_cost'), 0.01)
            and _same(financials.get('supply_cost'), consumption.get('total_supply_cost'), 0.01)
            and _same(financials.get('other_expenses'), consumption.get('total_other_expenses'), 0.01)):
        raise CannotUndo('financials_changed', 'Los números de ese evento cambiaron después, no los toco por aquí. '
                                               'Corrígelos desde el panel.')
    try:
        group = inv.check_movements_revertible(db, result['movement_ids'], tolerance=ROUNDING_TOLERANCE)
    except inv.MovementNotRevertible as exc:
        raise _from_inventory(exc)
    if len(group['movements']) != len(consumption.get('items_consumed', [])):
        raise CannotUndo('old', OLD)
    effects = []
    for part in group['items'].values():
        first, last = part['chain'][0], part['chain'][-1]
        effects.append(f"{part['item'].get('name')}: stock {last.get('stock_after'):g} → {first.get('stock_before'):g} "
                       f"{part['item'].get('unit') or ''}".rstrip())
    effects.append('Se borra el consumo y los números del evento vuelven a como estaban.')
    return {'group': group, 'consumption': consumption, 'booking_id': booking_id, 'effects': effects}


def _apply_consumption(db, action, plan, undo_id, batch, now):
    result = action['result']
    pairs = [(m, _rid(undo_id, f'reversal:{m}')) for m in result['movement_ids']]
    # The movements are DELETED, not marked: plan_consumption() finds a booking's consumption movements and gives
    # their stock back, so a leftover one would be given back a second time by the next consumption.
    done = inv.revert_movements_exact(db, pairs, f"Deshacer consumo ({action.get('summary', '')})"[:200], batch,
                                      plan=plan['group'], tolerance=ROUNDING_TOLERANCE, delete_originals=True,
                                      round_stock=True, now=now)
    batch.delete(db.collection(ev.CONSUMPTION).document(result['consumption_id']))

    def restore(financials):
        for key in FINANCIAL_KEYS:
            if key in result['prev_financials']:
                financials[key] = result['prev_financials'][key]
            else:
                financials.pop(key, None)
    _financials_update(db, plan['booking_id'], restore, batch, now)
    return {'snapshots': {**done['snapshots'], 'consumption': {result['consumption_id']: plan['consumption']}}}


# ---------- per-type: booking ----------

def _check_booking(db, action):
    result = action.get('result') or {}
    if 'customer_created' not in result or not result.get('booking_id'):
        raise CannotUndo('old', OLD)
    booking = _booking(db, result['booking_id'])
    if booking is None:
        raise CannotUndo('missing', 'Esa reserva ya no existe. Revísala desde el panel.')
    status = booking.get('status')
    if status in ('confirmed', 'completed', 'in_progress'):
        raise CannotUndo('booking_confirmed', 'Ya la confirmaste y al cliente le llegó el aviso; cancélala desde el panel.')
    if status != 'pending':
        raise CannotUndo('booking_not_pending', f"Esa reserva está '{status}', no hay nada que deshacer. Revísala desde el panel.")
    if ev.get_supplies_for_booking(db, result['booking_id']):
        raise CannotUndo('has_supplies', 'Esa reserva ya tiene insumos cargados; cancélala desde el panel.')
    customer_id = booking.get('customer_id')
    customer = None
    if customer_id:
        snapshot = db.collection('customers').document(customer_id).get()
        customer = snapshot.to_dict() if snapshot.exists else None
    effects = [f"La reserva de {booking.get('client_name')} queda cancelada (sin avisarle al cliente)."]
    if customer:
        effects.append(f"Se descuenta 1 reserva del cliente {customer.get('name')}.")
    return {'booking': booking, 'customer_id': customer_id if customer else None, 'effects': effects,
            'warnings': ['Ojo: el aviso de reserva nueva ya les llegó.']}


def _apply_booking(db, action, plan, undo_id, batch, now):
    booking_id = action['result']['booking_id']
    # never notifies: the customer was not told about a pending booking, and the admin side already was
    booking_service.cancel_pending_booking(db, booking_id, 'Deshecho: reserva creada por el asistente', batch=batch, now=now)
    if plan['customer_id']:
        batch.update(db.collection('customers').document(plan['customer_id']),
                     {'total_bookings': firestore.Increment(-1), 'updated_at': now})
    return {'snapshots': {'bookings': {booking_id: plan['booking']}}}


# ---------- registry ----------

HANDLERS = {
    'expense': (_check_expense, _apply_expense),
    'inventory_receipt': (_check_receipt, _apply_receipt),
    'inventory_update': (_check_update, _apply_update),
    'stock_adjustment': (_check_adjustment, _apply_adjustment),
    'event_supplies': (_check_supplies, _apply_supplies),
    'event_consumption': (_check_consumption, _apply_consumption),
    'booking': (_check_booking, _apply_booking),
}


# ---------- engine ----------

def _stock_signature(item):
    return (item.get('current_stock'), inv._item_average(item))


def _assert_inventory_unchanged(db, txn, plan):
    """Read (inside the transaction) every inventory document the plan relies on and compare it with what the check saw.
    Firestore also aborts the commit if one of them changes after this read, so check and apply cannot be separated by
    a concurrent movement."""
    checked = {item_id: part['item'] for item_id, part in ((plan.get('group') or {}).get('items') or {}).items()}
    checked.update(plan.get('new_item_docs') or {})
    for item_id, before in checked.items():
        snapshot = db.collection(inv.INVENTORY).document(item_id).get(transaction=txn)
        now_item = snapshot.to_dict() if snapshot.exists else None
        if now_item is None:
            raise CannotUndo('item_missing', f"El insumo {before.get('name')} ya no existe. Revísalo desde el panel.")
        if not all(_same(a, b) for a, b in zip(_stock_signature(now_item), _stock_signature(before))):
            raise CannotUndo('stock_changed', f"El stock de {before.get('name')} cambió justo ahora, no lo deshago. "
                                              'Te propongo un conteo: dime cuánto hay.')


def _load(db, action_id):
    snapshot = db.collection(pending.COLLECTION).document(action_id).get()
    if not snapshot.exists:
        raise CannotUndo('not_found', 'No encuentro esa acción.')
    action = snapshot.to_dict()
    action.setdefault('id', action_id)
    return action


def _eligible(action, source, now):
    """Rules that do not depend on the business data: type, status, time window"""
    if action.get('type') == UNDO_TYPE:
        raise CannotUndo('is_undo', 'Un deshacer no se puede deshacer. Si te equivocaste, registra de nuevo lo que corresponda.')
    if action.get('type') not in HANDLERS:
        raise CannotUndo('unsupported', 'Ese tipo de acción no se puede deshacer. Hazlo desde el panel.')
    if action.get('status') != pending.CONFIRMED:
        raise CannotUndo('not_confirmed', 'Esa acción no está confirmada, no hay nada que deshacer.')
    confirmed_at = _naive(action.get('confirmed_at'))
    if confirmed_at is None:
        raise CannotUndo('old', OLD)
    if now - confirmed_at > WINDOWS[source]:
        if source == 'whatsapp':
            raise CannotUndo('window', 'Pasaron más de 24 horas, ya no lo deshago por aquí. Hazlo desde el panel.')
        raise CannotUndo('window', 'Pasaron más de 7 días, ya no se puede deshacer.')


def describe(db, action_id, source='panel', now=None):
    """What undoing would do (read-only). Raises CannotUndo with the reason and the alternative."""
    now = now or datetime.utcnow()
    action = _load(db, action_id)
    if (action.get('undo') or {}).get('state') == 'done':
        raise CannotUndo('already_undone', 'Eso ya lo deshice.')
    _eligible(action, source, now)
    plan = HANDLERS[action['type']][0](db, action)
    return {'can_undo': True, 'action_id': action_id, 'type': action['type'], 'label': label(action),
            'effects': plan.get('effects', []), 'warnings': plan.get('warnings', [])}


def _claim(db, ref, undo_id, email, now):
    """None/failed -> processing, atomically. Returns (action, outcome)"""
    transaction = db.transaction()

    @pending._transactional
    def run(txn):
        snapshot = ref.get(transaction=txn)
        if not snapshot.exists:
            return None, 'not_found'
        action = snapshot.to_dict()
        state = action.get('undo') or {}
        if state.get('state') == 'done':
            return action, 'done'
        if state.get('state') == 'processing':
            started = _naive(state.get('at'))
            if started is not None and now - started < STALE_PROCESSING:
                return action, 'busy'
        txn.update(ref, {'undo': {'state': 'processing', 'undo_id': undo_id, 'at': now, 'by': email}})
        return action, 'claimed'

    return run(transaction)


def _mark_failed(ref, undo_id, email, now, error):
    try:
        ref.update({'undo': {'state': 'failed', 'undo_id': undo_id, 'at': now, 'by': email, 'error': str(error)[:300]}})
    except Exception:  # noqa: BLE001 - the original error matters more
        logger.error('Could not mark undo %s as failed', undo_id, exc_info=True)


def undo(db, action_id, user, source=None, now=None, audit=None):
    """Undo a confirmed action, exactly or not at all. Idempotent: undoing twice returns the first result."""
    source = source or source_for(user)
    now = now or datetime.utcnow()
    email = (user or {}).get('email')
    ref = db.collection(pending.COLLECTION).document(action_id)

    action = _load(db, action_id)
    stored = action.get('undo') or {}
    if stored.get('state') == 'done':
        return {**(stored.get('result') or {}), 'already_undone': True}
    _eligible(action, source, now)

    undo_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f'{action_id}:undo'))
    action, outcome = _claim(db, ref, undo_id, email, now)
    if outcome == 'done':
        return {**((action.get('undo') or {}).get('result') or {}), 'already_undone': True}
    if outcome == 'busy':
        raise CannotUndo('busy', 'Ya se está deshaciendo, dame un momento.')
    if outcome == 'not_found':
        raise CannotUndo('not_found', 'No encuentro esa acción.')

    try:
        check, apply = HANDLERS[action['type']]
        transaction = db.transaction()

        @pending._transactional
        def run(txn):
            # check + apply + the `done` marker in one transaction: all or nothing, and nothing can slip in between
            plan = check(db, action)
            _assert_inventory_unchanged(db, txn, plan)
            applied = apply(db, action, plan, undo_id, txn, now)
            outcome = {'type': action['type'], 'label': label(action), 'effects': plan.get('effects', []),
                       'warnings': plan.get('warnings', []), 'snapshots': applied.get('snapshots', {})}
            txn.update(ref, {'undo': {'state': 'done', 'undo_id': undo_id, 'at': now, 'by': email, 'source': source,
                                      'result': outcome}})
            return outcome

        result = run(transaction)
    except Exception as exc:
        _mark_failed(ref, undo_id, email, now, getattr(exc, 'reason', None) or exc)
        raise

    if audit is None:
        from utils.audit import log_audit as audit
    audit(email, 'undo', 'pending_action', action_id,
          changes={'type': action['type'], 'result': {'label': result['label'], 'effects': result['effects']},
                   'snapshots': result['snapshots']},
          metadata={'source': source, 'uid': (user or {}).get('uid'), 'undo_id': undo_id})
    return result


# ---------- the `undo` action type (WhatsApp: propose -> confirm) ----------

class UndoPayload(BaseModel):
    target_action_id: str = Field(min_length=1)


def _execute_undo(db, payload, user, action_id):
    result = undo(db, payload.target_action_id, user)
    return {'target_action_id': payload.target_action_id, 'undone_type': result.get('type'), 'label': result.get('label'),
            'effects': result.get('effects', []), 'warnings': result.get('warnings', []),
            'already_undone': bool(result.get('already_undone'))}


pending.register_action_type(UNDO_TYPE, UndoPayload, _execute_undo)


def propose_undo(db, target_action_id, user, source='whatsapp', now=None):
    """Check that the target can be undone and create the pending `undo` action (nothing is written yet).
    Raises CannotUndo with what to do instead."""
    info = describe(db, target_action_id, source=source, now=now)
    warnings = list(info['warnings'])
    return pending.create(
        db, UNDO_TYPE, {'target_action_id': target_action_id}, f"Deshacer: {info['label']}", user, warnings=warnings,
        context={'label': info['label'], 'effects': info['effects'], 'target_type': info['type']})
