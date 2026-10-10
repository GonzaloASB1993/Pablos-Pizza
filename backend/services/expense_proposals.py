"""AI agent: propose an expense from a receipt (propose -> confirm) and summarize expenses.

Chilean receipts: thousands separated by dots (`1.234`), dates as dd-mm-yyyy,
19 % VAT. A *factura* gives VAT credit and a *boleta* does not, so the document
type is stored with the expense.
"""
import hashlib
import re
import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from services import expenses_service as expenses
from services import pending_actions_service as pending
from utils.clock import today_cl
from utils.text_matching import normalize_text

# Same options as the expense dialog in the admin (ReportsPage): anything else
# would render as a blank value in its category <Select>.
CATEGORIES = ('general', 'servicios', 'arriendo', 'sueldos', 'marketing', 'otros')
ACTION_TYPE = 'expense'
LINES_TOLERANCE_CLP = 1  # rounding on receipts


def _parse_clp(value):
    """'$1.234' / '1.234,00' / 1234.0 -> 1234 (CLP has no decimals)"""
    if isinstance(value, bool):
        raise ValueError('monto inválido')
    if isinstance(value, (int, float)):
        return round(value)
    if isinstance(value, str):
        text = re.sub(r'[^\d.,-]', '', value)
        if ',' in text:  # 1.234,50 -> decimal comma
            text = text.replace('.', '').replace(',', '.')
        elif re.fullmatch(r'-?\d{1,3}(\.\d{3})+', text):  # 1.234.567 -> thousands
            text = text.replace('.', '')
        if not text:
            raise ValueError('monto inválido')
        return round(float(text))
    raise ValueError('monto inválido')


def parse_date(value):
    """dd-mm-yyyy / dd/mm/yyyy -> date; anything else is left for pydantic (ISO)"""
    if isinstance(value, str):
        m = re.fullmatch(r'\s*(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\s*', value)
        if m:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return value


class ExpenseLine(BaseModel):
    description: str = ''
    amount: int

    @field_validator('amount', mode='before')
    @classmethod
    def _amount(cls, v):
        return _parse_clp(v)


class ExpensePayload(BaseModel):
    kind: Literal['variable', 'fixed'] = 'variable'
    supplier: str = Field(min_length=1, max_length=120)
    date: date
    total: int = Field(gt=0, le=100_000_000)
    category: Literal[CATEGORIES] = 'general'
    document_type: Literal['boleta', 'factura', 'otro'] = 'boleta'
    folio: Optional[str] = Field(default=None, max_length=40)
    notes: str = Field(default='', max_length=500)
    lines: list[ExpenseLine] = Field(default_factory=list, max_length=100)

    @field_validator('date', mode='before')
    @classmethod
    def _date(cls, v):
        return parse_date(v)

    @field_validator('total', mode='before')
    @classmethod
    def _total(cls, v):
        return _parse_clp(v)

    @field_validator('supplier', 'notes', mode='before')
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator('folio', mode='before')
    @classmethod
    def _folio(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        return v or None


def dedupe_hash(payload):
    key = '|'.join([
        normalize_text(payload.supplier), payload.date.isoformat(), str(payload.total),
        normalize_text(payload.folio or ''),
    ])
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def _clp(n):
    return '$' + f'{n:,}'.replace(',', '.')


def build_summary(p):
    doc = {'boleta': 'Boleta', 'factura': 'Factura', 'otro': 'Documento'}[p.document_type]
    folio = f' N°{p.folio}' if p.folio else ''
    kind = 'Gasto fijo' if p.kind == 'fixed' else 'Gasto'
    return f"{kind}: {doc}{folio} · {p.supplier} · {p.date.strftime('%d-%m-%Y')} · {_clp(p.total)} · {p.category}"


def collect_warnings(db, p, h, exclude_action_id=None):
    warnings = []
    for action in pending.find_by_dedupe_hash(db, h):
        if action['id'] != exclude_action_id:
            state = 'ya confirmada' if action['status'] == pending.CONFIRMED else 'pendiente de confirmar'
            warnings.append(f"Posible duplicado: ya hay una propuesta {state} con el mismo proveedor, fecha, total y folio.")
            break
    for snapshot in db.collection(expenses.VARIABLE).where('dedupe_hash', '==', h).stream():
        warnings.append('Posible duplicado: ya existe un gasto registrado con el mismo proveedor, fecha, total y folio.')
        break

    if p.lines:
        lines_total = sum(line.amount for line in p.lines)
        if abs(lines_total - p.total) > LINES_TOLERANCE_CLP:
            warnings.append(
                f"El total ({_clp(p.total)}) no cuadra con la suma de las líneas ({_clp(lines_total)}). "
                "Revisa la boleta antes de confirmar.")
    if p.date > today_cl():
        warnings.append('La fecha del documento es futura.')
    elif (today_cl() - p.date).days > 365:
        warnings.append('La fecha del documento tiene más de un año.')
    if p.document_type == 'factura':
        warnings.append('Factura: el IVA (19 %) es crédito fiscal; el gasto se registra por el total con IVA.')
    if not p.folio:
        warnings.append('Sin folio: la detección de duplicados es menos confiable.')
    return warnings


def _execute(db, payload, user, action_id):
    """Runs only from pending_actions.confirm(); writes through expenses_service"""
    h = dedupe_hash(payload)
    provenance = {
        'source': 'ai_agent', 'supplier': payload.supplier, 'document_type': payload.document_type,
        'folio': payload.folio, 'document_date': payload.date.isoformat(), 'dedupe_hash': h,
        'created_by': user.get('email'),
    }
    description = payload.supplier if not payload.folio else f"{payload.supplier} ({payload.document_type} N°{payload.folio})"
    if payload.kind == 'fixed':
        created = expenses.create_fixed(db, {
            'description': description, 'amount': payload.total, 'category': payload.category,
            'notes': payload.notes, 'effective_from': payload.date.strftime('%Y-%m'),
        }, extra=provenance, expense_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f'{action_id}:expense')))
        return {'collection': expenses.FIXED, 'expense_id': created['id']}
    created = expenses.create_variable(db, {
        'description': description, 'amount': payload.total, 'category': payload.category,
        'notes': payload.notes, 'year': payload.date.year, 'month': payload.date.month,
    }, extra=provenance, expense_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f'{action_id}:expense')))
    return {'collection': expenses.VARIABLE, 'expense_id': created['id']}


pending.register_action_type(ACTION_TYPE, ExpensePayload, _execute)


def propose_expense(db, tool_input, user, attachments=None):
    """Create the pending action (nothing is written to the expense collections)"""
    payload = ExpensePayload.model_validate(tool_input)
    h = dedupe_hash(payload)
    action = pending.create(
        db, ACTION_TYPE, payload.model_dump(mode='json'), build_summary(payload), user,
        warnings=collect_warnings(db, payload, h), attachments=attachments, dedupe_hash=h)
    return action


# ---------- read side ----------

def _in_effect(expense, year, month):
    """Fixed expense active in the given month (YYYY-MM range, None = unbounded)"""
    if not expense.get('is_active', True):
        return False
    ym = f"{year}-{month:02d}"
    start, end = expense.get('effective_from'), expense.get('effective_to')
    return (not start or start <= ym) and (not end or ym <= end)


def get_expenses_summary(db, year, month=None):
    variable = expenses.list_variable(db, year=year, month=month)
    by_category = {}
    for e in variable:
        by_category[e.get('category', 'general')] = by_category.get(e.get('category', 'general'), 0) + (e.get('amount') or 0)

    fixed_all = expenses.list_fixed(db)
    months = [month] if month else list(range(1, 13))
    fixed_total = 0
    fixed_by_category = {}
    for m in months:
        for e in fixed_all:
            if _in_effect(e, year, m):
                amount = e.get('amount') or 0
                fixed_total += amount
                fixed_by_category[e.get('category', 'general')] = fixed_by_category.get(e.get('category', 'general'), 0) + amount

    return {
        'year': year, 'month': month,
        'variable_total': sum(by_category.values()),
        'variable_by_category': by_category,
        'variable_count': len(variable),
        'fixed_total': fixed_total,
        'fixed_by_category': fixed_by_category,
        'total': sum(by_category.values()) + fixed_total,
        'note': 'Gastos de insumos comprados para inventario no se cuentan aquí (se registran como stock).',
    }
