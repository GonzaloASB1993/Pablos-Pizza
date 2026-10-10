"""Propose -> confirm workflow for actions suggested by the AI agent.

The agent never writes business data. Its "propose_*" tools create a
document in `pending_actions`; only `confirm()` (deterministic, no LLM)
executes the write through the shared services, exactly once.

Action types register themselves with `register_action_type()`: a Pydantic
model that validates the payload (on creation and again on confirmation,
since the admin may have edited it) and an executor that performs the write.
"""
import uuid
from datetime import datetime, timedelta, timezone

from firebase_admin import firestore
from pydantic import ValidationError

COLLECTION = 'pending_actions'
EXPIRY = timedelta(hours=24)

PENDING, PROCESSING, CONFIRMED, CANCELLED, EXPIRED, FAILED = (
    'pending', 'processing', 'confirmed', 'cancelled', 'expired', 'failed')

# Wrapped so tests can run without a real Firestore transaction
_transactional = firestore.transactional


class PendingActionError(Exception):
    """Base class; `status_code` is the HTTP status the route should answer with"""
    status_code = 400

    def __init__(self, message, status_code=None):
        super().__init__(message)
        if status_code:
            self.status_code = status_code


class ActionNotFound(PendingActionError):
    status_code = 404


class ActionConflict(PendingActionError):
    status_code = 409


class ActionExpired(PendingActionError):
    status_code = 410


class InvalidPayload(PendingActionError):
    status_code = 422

    def __init__(self, errors):
        super().__init__('Datos inválidos')
        self.errors = errors


_registry = {}


def _naive_utc(value):
    """Firestore returns timezone-aware datetimes; the service works with naive UTC"""
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def register_action_type(type_name, model, executor):
    """executor(db, payload_model, user, action_id) -> dict of created ids (stored as `result`).

    `action_id` lets executors derive deterministic document ids, so a retry after a
    partial failure rewrites the same documents instead of duplicating them."""
    _registry[type_name] = (model, executor)


def _type_entry(type_name):
    if type_name not in _registry:
        raise PendingActionError(f'Tipo de acción desconocido: {type_name}')
    return _registry[type_name]


def validate_payload(type_name, payload):
    """Validate against the registered model and return the normalized dict"""
    model, _ = _type_entry(type_name)
    try:
        return model.model_validate(payload).model_dump(mode='json')
    except ValidationError as e:
        raise InvalidPayload(e.errors(include_url=False, include_context=False))


def create(db, type_name, payload, summary, user, warnings=None, attachments=None, dedupe_hash=None,
           context=None):
    now = datetime.utcnow()
    action_id = str(uuid.uuid4())
    action = {
        'id': action_id,
        'type': type_name,
        'status': PENDING,
        'payload': validate_payload(type_name, payload),
        'summary': summary,
        'warnings': list(warnings or []),
        'created_by': {'uid': user.get('uid'), 'email': user.get('email')},
        'created_at': now,
        'expires_at': now + EXPIRY,
        'confirmed_at': None,
        'result': None,
        'error': None,
        'attachments': list(attachments or []),
        'dedupe_hash': dedupe_hash,
        # read-only hints for the card (candidates, known categories...); never executed
        'context': context or {},
    }
    db.collection(COLLECTION).document(action_id).set(action)
    return action


def get(db, action_id):
    """Return the action; a pending one past its expiry is flipped to `expired`"""
    ref = db.collection(COLLECTION).document(action_id)
    snapshot = ref.get()
    if not snapshot.exists:
        raise ActionNotFound('Acción no encontrada')
    action = snapshot.to_dict()
    if action['status'] == PENDING and _naive_utc(action['expires_at']) <= datetime.utcnow():
        ref.update({'status': EXPIRED})
        action['status'] = EXPIRED
    return action


def find_by_dedupe_hash(db, dedupe_hash, statuses=(PENDING, CONFIRMED)):
    """Actions already proposed/confirmed for the same document (duplicate detection)"""
    if not dedupe_hash:
        return []
    found = []
    for snapshot in db.collection(COLLECTION).where('dedupe_hash', '==', dedupe_hash).stream():
        action = snapshot.to_dict()
        if action['status'] in statuses:
            found.append(action)
    return found


def _claim(db, ref, allowed_from):
    """Atomically move the action to `processing`; returns its data before the move"""
    transaction = db.transaction()

    @_transactional
    def run(txn):
        snapshot = ref.get(transaction=txn)
        if not snapshot.exists:
            raise ActionNotFound('Acción no encontrada')
        action = snapshot.to_dict()
        if action['status'] not in allowed_from:
            return action, False
        txn.update(ref, {'status': PROCESSING})
        return action, True

    return run(transaction)


def confirm(db, action_id, user, edited_payload=None, audit=None):
    """Execute the action once. Confirming again returns the stored result."""
    action = get(db, action_id)  # also handles expiry
    ref = db.collection(COLLECTION).document(action_id)

    if action['status'] == CONFIRMED:
        return {**action, 'already_confirmed': True}
    if action['status'] in (CANCELLED, EXPIRED):
        raise (ActionExpired if action['status'] == EXPIRED else ActionConflict)(
            f"La acción está {action['status']}")

    # Revalidate: the admin may have edited the proposal in the card
    payload = validate_payload(action['type'], edited_payload if edited_payload is not None else action['payload'])

    action, claimed = _claim(db, ref, allowed_from=(PENDING, FAILED))
    if not claimed:
        # Someone else is confirming it right now, or it just finished
        latest = get(db, action_id)
        if latest['status'] == CONFIRMED:
            return {**latest, 'already_confirmed': True}
        raise ActionConflict('La acción ya se está procesando')

    model, executor = _type_entry(action['type'])
    try:
        result = executor(db, model.model_validate(payload), user, action_id)
    except Exception as exc:
        ref.update({'status': FAILED, 'error': str(exc)})
        raise

    update = {'status': CONFIRMED, 'confirmed_at': datetime.utcnow(), 'result': result,
              'payload': payload, 'error': None}
    ref.update(update)

    if audit is None:
        from utils.audit import log_audit as audit
    audit(user.get('email'), 'confirm', 'pending_action', action_id,
          changes={'type': action['type'], 'result': result},
          metadata={'source': 'ai_agent', 'uid': user.get('uid')})

    return {**action, **update}


def cancel(db, action_id):
    action = get(db, action_id)
    if action['status'] == CANCELLED:
        return action
    if action['status'] != PENDING:
        raise ActionConflict(f"No se puede cancelar una acción {action['status']}")
    db.collection(COLLECTION).document(action_id).update({'status': CANCELLED})
    return {**action, 'status': CANCELLED}


def serialize(action):
    """JSON-friendly view for the chat card (datetimes as ISO strings)"""
    return {k: (_naive_utc(v).isoformat() + 'Z' if isinstance(v, datetime) else v) for k, v in action.items()}
