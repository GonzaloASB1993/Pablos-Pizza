"""Fixed / variable expenses business logic, shared by the HTTP routes and the AI agent.

Pure functions over a Firestore client: no Flask objects here. Validation of
untrusted input (e.g. what the LLM proposes) belongs to the caller; these
functions keep the exact semantics the HTTP API has always had.
"""
import uuid
from datetime import datetime

FIXED = "fixed_expenses"
VARIABLE = "variable_expenses"


class ExpenseNotFound(Exception):
    """Raised when updating or deleting an expense that does not exist"""


class MissingField(ValueError):
    """Raised when a required field is absent from the payload"""

    def __init__(self, field):
        super().__init__(f"Missing {field}")
        self.field = field


def _require(data, fields):
    for field in fields:
        if field not in data:
            raise MissingField(field)


def _with_id(snapshot):
    data = snapshot.to_dict()
    data['id'] = snapshot.id
    return data


def _newest_first(items):
    items.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
    return items


# ---------- fixed expenses ----------

def list_fixed(db):
    return _newest_first([_with_id(s) for s in db.collection(FIXED).get()])


def create_fixed(db, data, extra=None, expense_id=None):
    """`extra`: additional stored fields (e.g. provenance of an AI-proposed expense)"""
    _require(data, ['description', 'amount'])
    expense_id = expense_id or str(uuid.uuid4())
    expense = {
        'id': expense_id,
        'description': data['description'],
        'amount': float(data['amount']),
        'category': data.get('category', 'general'),
        'notes': data.get('notes', ''),
        'is_active': data.get('is_active', True),
        # Optional effective date range (YYYY-MM). None means "no limit" on that side.
        'effective_from': data.get('effective_from') or None,
        'effective_to': data.get('effective_to') or None,
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        **(extra or {}),
    }
    db.collection(FIXED).document(expense_id).set(expense)
    return expense


def update_fixed(db, expense_id, data):
    ref = db.collection(FIXED).document(expense_id)
    if not ref.get().exists:
        raise ExpenseNotFound(expense_id)

    update = {'updated_at': datetime.now()}
    for key in ('description', 'category', 'notes', 'is_active'):
        if key in data:
            update[key] = data[key]
    if 'amount' in data:
        update['amount'] = float(data['amount'])
    for key in ('effective_from', 'effective_to'):
        if key in data:
            update[key] = data[key] or None

    ref.update(update)
    updated = ref.get().to_dict()
    updated['id'] = expense_id
    return updated


def delete_fixed(db, expense_id):
    _delete(db, FIXED, expense_id)


# ---------- variable expenses ----------

def list_variable(db, year=None, month=None):
    """Filtered in Python to avoid requiring Firestore composite indexes"""
    result = []
    for snapshot in db.collection(VARIABLE).get():
        data = _with_id(snapshot)
        if year and data.get('year') != int(year):
            continue
        if month and data.get('month') != int(month):
            continue
        result.append(data)
    return _newest_first(result)


def create_variable(db, data, extra=None, expense_id=None):
    _require(data, ['description', 'amount', 'year', 'month'])
    expense_id = expense_id or str(uuid.uuid4())
    expense = {
        'id': expense_id,
        'description': data['description'],
        'amount': float(data['amount']),
        'category': data.get('category', 'general'),
        'notes': data.get('notes', ''),
        'year': int(data['year']),
        'month': int(data['month']),
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        **(extra or {}),
    }
    db.collection(VARIABLE).document(expense_id).set(expense)
    return expense


def update_variable(db, expense_id, data):
    ref = db.collection(VARIABLE).document(expense_id)
    if not ref.get().exists:
        raise ExpenseNotFound(expense_id)

    update = {'updated_at': datetime.now()}
    for key in ('description', 'category', 'notes'):
        if key in data:
            update[key] = data[key]
    if 'amount' in data:
        update['amount'] = float(data['amount'])
    for key in ('year', 'month'):
        if key in data:
            update[key] = int(data[key])

    ref.update(update)
    updated = ref.get().to_dict()
    updated['id'] = expense_id
    return updated


def delete_variable(db, expense_id):
    _delete(db, VARIABLE, expense_id)


def _delete(db, collection, expense_id):
    ref = db.collection(collection).document(expense_id)
    if not ref.get().exists:
        raise ExpenseNotFound(expense_id)
    ref.delete()
