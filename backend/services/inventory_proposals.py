"""AI agent: propose inventory changes (propose -> confirm).

Action types registered here:
  inventory_receipt   a purchase document (or a single purchase / new item) made of lines, each one
                      classified as an EXISTING item (adds stock), a NEW item (created, then stocked)
                      or an EXPENSE (not inventory). One line = exactly one classification, so a
                      purchase can never be counted both as stock and as an expense.
  inventory_update    corrections to an item's data (name, category, unit, supplier, limits, notes)
  stock_adjustment    physical count or waste, as a stock movement with history

Every write goes through inventory_service / expenses_service. Document ids are derived from the
action id (uuid5), so retrying a half-applied confirmation rewrites the same documents.
"""
import uuid
from datetime import date
from datetime import date as Date  # the field below is also called `date`
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from services import expense_proposals, inventory_search
from services import expenses_service as expenses
from services import inventory_service as inv
from services import pending_actions_service as pending
from utils.text_matching import normalize_text

RECEIPT_TYPE = 'inventory_receipt'
UPDATE_TYPE = 'inventory_update'
ADJUSTMENT_TYPE = 'stock_adjustment'
PRICE_JUMP_RATIO = 0.5  # warn when a unit cost differs >50 % from the item's current average


class ProposalError(Exception):
    """The proposal cannot be built; the message goes back to the model so it can ask the user"""


def _id(action_id, key):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'{action_id}:{key}'))


def _clp(n):
    return '$' + f'{round(n):,}'.replace(',', '.')


def _qty(n):
    return f'{n:g}'


# ---------- payload models ----------

class ReceiptLine(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    amount: int = Field(ge=0, le=100_000_000)  # CLP paid for this whole line
    classification: Literal['existing', 'new', 'expense']
    # inventory lines
    quantity: Optional[float] = Field(default=None, ge=0, le=1_000_000)
    unit: Optional[str] = Field(default=None, max_length=20)
    item_id: Optional[str] = None                      # existing
    name: Optional[str] = Field(default=None, max_length=120)      # new
    category: Optional[str] = Field(default=None, max_length=60)   # new
    min_stock: float = Field(default=0, ge=0)          # new (a receipt cannot tell: shown and editable)
    max_stock: float = Field(default=0, ge=0)          # new
    # expense lines
    expense_category: Literal[expense_proposals.CATEGORIES] = 'general'

    @field_validator('amount', mode='before')
    @classmethod
    def _amount(cls, v):
        return expense_proposals._parse_clp(v)

    @field_validator('description', 'name', 'category', 'unit', mode='before')
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode='after')
    def _per_classification(self):
        if self.classification == 'expense':
            if self.amount <= 0:
                raise ValueError('un gasto necesita un monto mayor a 0')
            return self
        if self.classification == 'existing':
            if not self.item_id:
                raise ValueError('un insumo existente necesita item_id')
            if not self.quantity or self.quantity <= 0:
                raise ValueError('un insumo existente necesita cantidad mayor a 0')
            if self.amount <= 0:
                raise ValueError('una compra necesita un monto mayor a 0')
            return self
        # new
        if not self.name or not self.unit or not self.category:
            raise ValueError('un insumo nuevo necesita nombre, unidad y categoría')
        if self.quantity is None:
            self.quantity = 0
        if self.quantity > 0 and self.amount <= 0:
            raise ValueError('un insumo nuevo con stock inicial necesita el monto pagado')
        if self.max_stock and self.max_stock < self.min_stock:
            raise ValueError('el stock máximo no puede ser menor al mínimo')
        return self

    @property
    def unit_cost(self):
        return (self.amount / self.quantity) if self.quantity else 0.0


class ReceiptPayload(BaseModel):
    supplier: Optional[str] = Field(default=None, max_length=120)
    date: Date = Field(default_factory=Date.today)
    total: Optional[int] = Field(default=None, ge=0, le=100_000_000)
    document_type: Literal['boleta', 'factura', 'otro'] = 'boleta'
    folio: Optional[str] = Field(default=None, max_length=40)
    notes: str = Field(default='', max_length=500)
    lines: list[ReceiptLine] = Field(min_length=1, max_length=60)

    @field_validator('date', mode='before')
    @classmethod
    def _date(cls, v):
        return expense_proposals.parse_date(v)

    @field_validator('total', mode='before')
    @classmethod
    def _total(cls, v):
        return None if v in (None, '') else expense_proposals._parse_clp(v)

    @field_validator('supplier', 'folio', mode='before')
    @classmethod
    def _blank_to_none(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        return v or None

    @property
    def lines_total(self):
        return sum(line.amount for line in self.lines)

    @property
    def document_total(self):
        return self.total if self.total is not None else self.lines_total


class UpdateChanges(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    category: Optional[str] = Field(default=None, min_length=1, max_length=60)
    unit: Optional[str] = Field(default=None, min_length=1, max_length=20)
    supplier: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = Field(default=None, max_length=500)
    min_stock: Optional[float] = Field(default=None, ge=0)
    max_stock: Optional[float] = Field(default=None, ge=0)


class UpdatePayload(BaseModel):
    item_id: str = Field(min_length=1)
    changes: UpdateChanges

    @model_validator(mode='after')
    def _not_empty(self):
        if not self.changes.model_dump(exclude_none=True):
            raise ValueError('no hay cambios que aplicar')
        return self


class AdjustmentPayload(BaseModel):
    item_id: str = Field(min_length=1)
    mode: Literal['count', 'waste']  # count: set stock to what was physically counted; waste: remove stock
    quantity: float = Field(ge=0, le=1_000_000)
    reason: str = Field(default='', max_length=200)

    @model_validator(mode='after')
    def _waste_positive(self):
        if self.mode == 'waste' and self.quantity <= 0:
            raise ValueError('la merma debe ser mayor a 0')
        return self


# ---------- executors (run only from pending_actions.confirm) ----------

def _execute_receipt(db, payload, user, action_id):
    provenance = {'source': 'ai_agent', 'pending_action_id': action_id}
    h = expense_proposals.dedupe_hash(_HashView(payload)) if payload.supplier else None
    applied = []

    for index, line in enumerate(payload.lines):
        entry = {'index': index, 'classification': line.classification}

        if line.classification == 'expense':
            description = f"{payload.supplier} · {line.description}" if payload.supplier else line.description
            created = expenses.create_variable(db, {
                'description': description, 'amount': line.amount, 'category': line.expense_category,
                'notes': payload.notes, 'year': payload.date.year, 'month': payload.date.month,
            }, extra={**provenance, 'supplier': payload.supplier, 'document_type': payload.document_type,
                      'folio': payload.folio, 'document_date': payload.date.isoformat(),
                      'receipt_line': index, 'dedupe_hash': h, 'created_by': user.get('email')},
                expense_id=_id(action_id, f'{index}:expense'))
            entry['expense_id'] = created['id']

        else:
            if line.classification == 'new':
                item = inv.create_item(db, {
                    'name': line.name, 'category': line.category, 'unit': line.unit,
                    'current_stock': 0, 'min_stock': line.min_stock, 'max_stock': line.max_stock,
                    'cost_per_unit': line.unit_cost, 'supplier': payload.supplier or '', 'notes': payload.notes,
                }, item_id=_id(action_id, f'{index}:item'), extra=provenance)
                item_id = item['id']
                entry['item_id'] = item_id
            else:
                item_id = line.item_id
                entry['item_id'] = item_id

            if line.quantity and line.quantity > 0:
                moved = inv.register_movement(
                    db, item_id, 'purchase', line.quantity, line.unit_cost,
                    reference_id=action_id, reference_type='ai_receipt', supplier=payload.supplier,
                    notes=f"{payload.document_type} N°{payload.folio}" if payload.folio else payload.notes or None,
                    movement_id=_id(action_id, f'{index}:movement'))
                entry['movement_id'] = moved['movement_id']
                entry['stock_after'] = moved['stock_after']
        applied.append(entry)

    return {
        'lines': applied,
        'inventory_lines': sum(1 for e in applied if e['classification'] != 'expense'),
        'expense_lines': sum(1 for e in applied if e['classification'] == 'expense'),
    }


def _execute_update(db, payload, user, action_id):
    changes = payload.changes.model_dump(exclude_none=True)
    item = inv.update_item(db, payload.item_id, changes)
    return {'item_id': item['id'], 'changed': sorted(changes)}


def _execute_adjustment(db, payload, user, action_id):
    snapshot = db.collection(inv.INVENTORY).document(payload.item_id).get()
    if not snapshot.exists:
        raise inv.ItemNotFound(payload.item_id)
    item = snapshot.to_dict()
    average = item.get('weighted_avg_cost', item.get('cost_per_unit', 0))
    movement_id = _id(action_id, 'adjustment')
    note = payload.reason or ('Conteo físico' if payload.mode == 'count' else 'Merma')

    if payload.mode == 'waste':
        moved = inv.register_movement(db, payload.item_id, 'waste', payload.quantity, average,
                                      reference_id=action_id, reference_type='ai_adjustment',
                                      notes=note, movement_id=movement_id)
    else:
        delta = round(payload.quantity - item.get('current_stock', 0), 4)
        if delta == 0:
            return {'item_id': payload.item_id, 'delta': 0, 'stock_after': item.get('current_stock', 0)}
        moved = inv.register_movement(db, payload.item_id, 'adjustment', delta, average,
                                      reference_id=action_id, reference_type='ai_adjustment',
                                      notes=note, movement_id=movement_id)
    return {'item_id': payload.item_id, 'movement_id': moved['movement_id'], 'stock_after': moved['stock_after']}


pending.register_action_type(RECEIPT_TYPE, ReceiptPayload, _execute_receipt)
pending.register_action_type(UPDATE_TYPE, UpdatePayload, _execute_update)
pending.register_action_type(ADJUSTMENT_TYPE, AdjustmentPayload, _execute_adjustment)


# ---------- proposals ----------

def _item_or_error(db, item_id):
    snapshot = db.collection(inv.INVENTORY).document(item_id).get()
    if not snapshot.exists:
        raise ProposalError(f"No existe un insumo con id {item_id}. Búscalo con search_inventory.")
    item = snapshot.to_dict()
    item['id'] = item_id
    return item


def _brief(item):
    return {'id': item['id'], 'name': item.get('name'), 'unit': item.get('unit'),
            'current_stock': item.get('current_stock', 0),
            'cost_per_unit': item.get('weighted_avg_cost', item.get('cost_per_unit', 0))}


def build_receipt_summary(p):
    parts = {'existing': 0, 'new': 0, 'expense': 0}
    for line in p.lines:
        parts[line.classification] += 1
    pieces = []
    if parts['existing']:
        pieces.append(f"{parts['existing']} compra{'s' if parts['existing'] != 1 else ''} de insumo")
    if parts['new']:
        pieces.append(f"{parts['new']} insumo{'s' if parts['new'] != 1 else ''} nuevo{'s' if parts['new'] != 1 else ''}")
    if parts['expense']:
        pieces.append(f"{parts['expense']} gasto{'s' if parts['expense'] != 1 else ''}")
    doc = {'boleta': 'Boleta', 'factura': 'Factura', 'otro': 'Documento'}[p.document_type]
    folio = f' N°{p.folio}' if p.folio else ''
    who = f' · {p.supplier}' if p.supplier else ''
    return f"Compra: {doc}{folio}{who} · {p.date.strftime('%d-%m-%Y')} · {_clp(p.document_total)} · {', '.join(pieces)}"


def propose_receipt(db, tool_input, user, attachments=None):
    payload = ReceiptPayload.model_validate(tool_input)
    warnings, candidates, items = [], {}, {}
    categories, units = inventory_search.catalog_vocabulary(db)

    for index, line in enumerate(payload.lines):
        label = f"Línea {index + 1} ({line.description})"
        if line.classification == 'existing':
            item = _item_or_error(db, line.item_id)
            items[line.item_id] = _brief(item)
            if line.unit and normalize_text(line.unit) != normalize_text(item.get('unit', '')):
                warnings.append(f"{label}: la unidad ({line.unit}) no coincide con la del insumo ({item.get('unit')}). "
                                "Verifica la cantidad.")
            average = item.get('weighted_avg_cost', item.get('cost_per_unit', 0)) or 0
            if average > 0 and abs(line.unit_cost - average) / average > PRICE_JUMP_RATIO:
                warnings.append(f"{label}: el costo por {item.get('unit')} ({_clp(line.unit_cost)}) difiere más de "
                                f"{round(PRICE_JUMP_RATIO * 100)} % del promedio actual ({_clp(average)}).")
        elif line.classification == 'new':
            found = inventory_search.find_duplicates(db, line.name)
            exact = [m for m in found if m['match'] == 'exact']
            if exact:
                raise ProposalError(
                    f"{label}: ya existe el insumo '{exact[0]['name']}' (id {exact[0]['id']}). "
                    "Usa classification 'existing' con ese item_id, o pregunta al usuario.")
            if found:
                warnings.append(f"{label}: se parece a '{found[0]['name']}' que ya existe. "
                                "Si es el mismo producto, cámbialo a insumo existente.")
            if categories and line.category not in categories:
                warnings.append(f"{label}: la categoría '{line.category}' es nueva (existentes: {', '.join(categories)}).")
            if line.quantity and line.max_stock == 0 and line.min_stock == 0:
                warnings.append(f"{label}: stock mínimo y máximo en 0 (no se pueden leer de la boleta). Ajústalos si quieres alertas.")

        # alternatives the admin can switch to in the card
        pool = inventory_search.search_items(db, line.name or line.description, limit=3, threshold=0.5)
        if pool:
            candidates[str(index)] = pool

    if payload.total is not None and abs(payload.total - payload.lines_total) > expense_proposals.LINES_TOLERANCE_CLP:
        warnings.append(f"El total ({_clp(payload.total)}) no cuadra con la suma de las líneas ({_clp(payload.lines_total)}). "
                        "Revisa la boleta antes de confirmar.")
    if payload.date > date.today():
        warnings.append('La fecha del documento es futura.')
    if payload.document_type == 'factura':
        warnings.append('Factura: los montos de las líneas suelen venir netos; el IVA (19 %) es crédito fiscal. '
                        'Revisa si el monto de cada línea incluye IVA.')

    h = expense_proposals.dedupe_hash(_HashView(payload)) if payload.supplier else None
    if h:
        for action in pending.find_by_dedupe_hash(db, h):
            state = 'confirmada' if action['status'] == pending.CONFIRMED else 'pendiente de confirmar'
            warnings.append(f"Posible duplicado: ya hay una propuesta {state} con el mismo proveedor, fecha, total y folio.")
            break
        if any(True for _ in db.collection(expenses.VARIABLE).where('dedupe_hash', '==', h).stream()):
            warnings.append('Posible duplicado: ya hay gastos registrados con el mismo proveedor, fecha, total y folio.')

    return pending.create(
        db, RECEIPT_TYPE, payload.model_dump(mode='json'), build_receipt_summary(payload), user,
        warnings=warnings, attachments=attachments, dedupe_hash=h,
        context={'known_categories': categories, 'known_units': units, 'candidates': candidates, 'items': items})


class _HashView:
    """Gives a receipt the supplier/date/total/folio shape that dedupe_hash() expects"""

    def __init__(self, payload):
        self.supplier, self.date, self.folio = payload.supplier, payload.date, payload.folio
        self.total = payload.document_total


def propose_inventory_item(db, tool_input, user, attachments=None):
    """New item (optionally with its first purchase) as a one-line receipt"""
    line = {
        'description': tool_input.get('name', ''), 'classification': 'new',
        'name': tool_input.get('name'), 'category': tool_input.get('category'), 'unit': tool_input.get('unit'),
        'quantity': tool_input.get('quantity', 0), 'amount': tool_input.get('total_cost', 0),
        'min_stock': tool_input.get('min_stock', 0), 'max_stock': tool_input.get('max_stock', 0),
    }
    return propose_receipt(db, {
        'supplier': tool_input.get('supplier'), 'date': tool_input.get('date') or date.today().isoformat(),
        'folio': tool_input.get('folio'), 'notes': tool_input.get('notes', ''), 'lines': [line],
    }, user, attachments)


def propose_inventory_purchase(db, tool_input, user, attachments=None):
    """Stock purchase of an item that already exists, as a one-line receipt"""
    item = _item_or_error(db, tool_input.get('item_id', ''))
    line = {
        'description': item.get('name', ''), 'classification': 'existing', 'item_id': item['id'],
        'quantity': tool_input.get('quantity'), 'unit': tool_input.get('unit') or item.get('unit'),
        'amount': tool_input.get('total_cost'),
    }
    return propose_receipt(db, {
        'supplier': tool_input.get('supplier'), 'date': tool_input.get('date') or date.today().isoformat(),
        'folio': tool_input.get('folio'), 'notes': tool_input.get('notes', ''), 'lines': [line],
    }, user, attachments)


def propose_inventory_update(db, tool_input, user, attachments=None):
    payload = UpdatePayload.model_validate({'item_id': tool_input.get('item_id', ''),
                                            'changes': tool_input.get('changes') or {}})
    item = _item_or_error(db, payload.item_id)
    changes = payload.changes.model_dump(exclude_none=True)
    diff = ', '.join(f"{k}: {item.get(k, '—')} → {v}" for k, v in changes.items())
    warnings = []
    if 'name' in changes:
        for match in inventory_search.find_duplicates(db, changes['name']):
            if match['id'] != item['id']:
                warnings.append(f"El nuevo nombre se parece a '{match['name']}', que ya existe.")
                break
    return pending.create(
        db, UPDATE_TYPE, payload.model_dump(mode='json'), f"Editar insumo {item.get('name')}: {diff}", user,
        warnings=warnings, attachments=attachments, context={'items': {item['id']: _brief(item)}, 'before': {
            k: item.get(k) for k in changes}})


def propose_stock_adjustment(db, tool_input, user, attachments=None):
    payload = AdjustmentPayload.model_validate({
        'item_id': tool_input.get('item_id', ''), 'mode': tool_input.get('mode'),
        'quantity': tool_input.get('quantity'), 'reason': tool_input.get('reason', '')})
    item = _item_or_error(db, payload.item_id)
    stock, unit = item.get('current_stock', 0), item.get('unit', '')
    warnings = []
    if payload.mode == 'count':
        delta = payload.quantity - stock
        summary = (f"Conteo de {item.get('name')}: {_qty(stock)} → {_qty(payload.quantity)} {unit} "
                   f"({'+' if delta >= 0 else ''}{_qty(round(delta, 4))})")
        if abs(delta) > 0 and stock > 0 and abs(delta) / stock > 0.5:
            warnings.append('La diferencia con el stock registrado es mayor al 50 %. Verifica el conteo y la unidad.')
    else:
        summary = f"Merma de {item.get('name')}: -{_qty(payload.quantity)} {unit} (stock {_qty(stock)} → {_qty(max(0, stock - payload.quantity))})"
        if payload.quantity > stock:
            raise ProposalError(f"La merma ({_qty(payload.quantity)}) supera el stock registrado ({_qty(stock)} {unit}).")
    return pending.create(
        db, ADJUSTMENT_TYPE, payload.model_dump(mode='json'), summary, user, warnings=warnings,
        attachments=attachments, context={'items': {item['id']: _brief(item)}})
