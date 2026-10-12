"""Burst grouping and per-phone serialization for the WhatsApp assistant (design block B2).

Why: sending an album of receipts (or a photo and its caption as two messages) makes WhatsApp deliver several messages
within a second or two. Each one fires its own trigger, so without this the person gets several answers and the agent
sees the photos one at a time. Two messages in a row would also overwrite each other's conversation history.

Two mechanisms, both transactional and independent of the order the triggers wake up in:

  * Bursts (`whatsapp_bursts/{phone}`): the WEBHOOK (fast and ordered) joins a message to the open burst or starts one
    (any message with media does; a lone text does not, unless AI_WHATSAPP_TEXT_BURST_SECONDS > 0). The worker of the
    LAST message of a burst is its leader: it waits until the burst is quiet, then answers once for all of them; every
    other worker finds it is not the last message and ends as `merged`.
  * Lock (`whatsapp_locks/{phone}`): one agent turn at a time per phone, so a second turn loads the history the first one
    saved. A lock expires on its own (a crashed turn must not block the person) and is released in a `finally`.

This module must not import whatsapp_agent (the agent imports it).
"""
import logging
import os
from datetime import timedelta

from services import pending_actions_service as pending

logger = logging.getLogger(__name__)

BURSTS = 'whatsapp_bursts'
LOCKS = 'whatsapp_locks'
WARMUP_PREFIX = 'warmup-'          # keep-warm markers never take part in bursts

COLLECTING, PROCESSING, DONE = 'collecting', 'processing', 'done'

MAX_BURST_MESSAGES = 10
MAX_BURST_AGE = 15                 # seconds since the first message of a burst
LEADER_MAX_WAIT = 20               # seconds a leader waits at most before it takes the lead anyway
POLL_SECONDS = 1.0

LOCK_TTL = 300                     # seconds a lock stays valid: the worker's own timeout (an expired lock can be taken over)
LOCK_MAX_WAIT = 120                # seconds a turn waits for the lock before it gives up (it is never stolen while valid)


class LockBusy(Exception):
    """Another turn of the same phone still holds a valid lock after LOCK_MAX_WAIT"""


def _float_env(name, default):
    try:
        return max(0.0, float(os.getenv(name, default)))
    except (TypeError, ValueError):
        return float(default)


def burst_seconds():
    """Quiet time after the last message of a burst before answering"""
    return _float_env('AI_WHATSAPP_BURST_SECONDS', 3)


def text_burst_seconds():
    """Wait applied to a lone text so a photo sent right after can join it (0 = a text never waits)"""
    return _float_env('AI_WHATSAPP_TEXT_BURST_SECONDS', 0)


def _naive(value):
    return value.replace(tzinfo=None) if value is not None and getattr(value, 'tzinfo', None) else value


def _seconds(delta):
    return delta.total_seconds()


# ---------- webhook side: join / start a burst (called INSIDE the store_inbound transaction) ----------

def is_open(data, now):
    """Can a new message still join this burst?"""
    if not data or data.get('state') != COLLECTING:
        return False
    last, started = _naive(data.get('last_at')), _naive(data.get('started_at'))
    if last is None or started is None:
        return False
    window = data.get('window', burst_seconds())
    return (_seconds(now - last) <= window and _seconds(now - started) <= MAX_BURST_AGE
            and len(data.get('sids') or []) < MAX_BURST_MESSAGES)


def join(db, txn, phone, sid, now, has_media):
    """Returns the burst id this message belongs to, or None (a text on its own: nothing to wait for).
    Reads before writes (Firestore transaction rule)."""
    if not phone or str(sid).startswith(WARMUP_PREFIX):
        return None
    ref = db.collection(BURSTS).document(phone)
    snapshot = ref.get(transaction=txn)
    data = snapshot.to_dict() if snapshot.exists else None
    if data and is_open(data, now):
        txn.update(ref, {'sids': list(data.get('sids') or []) + [sid], 'last_sid': sid, 'last_at': now,
                         'window': burst_seconds()})
        return data['id']
    window = burst_seconds() if has_media else text_burst_seconds()
    if not has_media and window <= 0:
        return None
    txn.set(ref, {'id': sid, 'state': COLLECTING, 'started_at': now, 'last_at': now, 'last_sid': sid,
                  'sids': [sid], 'window': window})
    return sid


# ---------- worker side ----------

def lead(db, phone, burst_id, sid, deps):
    """Called by the worker of a message that belongs to a burst. Waits until the burst is quiet.
    Returns the ordered list of sids this worker must answer for, or None when it is `merged` into another worker's turn."""
    ref = db.collection(BURSTS).document(phone)
    started = deps.now()
    waited = 0.0   # also counted by what we really slept: a clock that does not advance must not loop forever
    while True:
        snapshot = ref.get()
        data = snapshot.to_dict() if snapshot.exists else None
        if not data or data.get('id') != burst_id or data.get('last_sid') != sid or data.get('state') != COLLECTING:
            return None
        now = deps.now()
        remaining = _seconds(_naive(data['last_at']) + timedelta(seconds=data.get('window', burst_seconds())) - now)
        if remaining <= 0 or _seconds(now - started) >= LEADER_MAX_WAIT or waited >= LEADER_MAX_WAIT:
            return _take_lead(db, ref, burst_id, sid)
        step = min(remaining, POLL_SECONDS)
        deps.sleep(step)
        waited += step


def _take_lead(db, ref, burst_id, sid):
    """collecting -> processing, only for the burst's last message (a newer one may have arrived meanwhile)"""
    transaction = db.transaction()

    @pending._transactional
    def run(txn):
        snapshot = ref.get(transaction=txn)
        if not snapshot.exists:
            return None
        data = snapshot.to_dict()
        if data.get('id') != burst_id or data.get('state') != COLLECTING or data.get('last_sid') != sid:
            return None
        txn.update(ref, {'state': PROCESSING})
        return list(data.get('sids') or [])

    return run(transaction)


def finish(db, phone, burst_id):
    """processing -> done (only if the doc still holds OUR burst: a newer one may have replaced it)"""
    ref = db.collection(BURSTS).document(phone)
    transaction = db.transaction()

    @pending._transactional
    def run(txn):
        snapshot = ref.get(transaction=txn)
        if snapshot.exists and snapshot.to_dict().get('id') == burst_id:
            txn.update(ref, {'state': DONE})

    run(transaction)


# ---------- per-phone lock ----------

def _try_lock(db, phone, owner, now):
    ref = db.collection(LOCKS).document(phone)
    transaction = db.transaction()

    @pending._transactional
    def run(txn):
        snapshot = ref.get(transaction=txn)
        data = snapshot.to_dict() if snapshot.exists else None
        until = _naive(data.get('until')) if data else None
        free = (not data or not data.get('owner_sid') or data['owner_sid'] == owner
                or until is None or until <= now)
        if not free:
            return False
        txn.set(ref, {'owner_sid': owner, 'until': now + timedelta(seconds=LOCK_TTL)})
        return True

    return run(transaction)


def acquire_lock(db, phone, owner, deps):
    """One agent turn at a time per phone. Retries every second; a lock is only taken over once it EXPIRED (`until <= now`,
    LOCK_TTL is the worker's timeout, so a holder that is still running is never robbed). After LOCK_MAX_WAIT it gives up
    with LockBusy: running next to a live turn would let two turns overwrite each other's history and proposals."""
    started = deps.now()
    waited = 0
    while True:
        now = deps.now()
        if _try_lock(db, phone, owner, now):
            return
        if _seconds(now - started) >= LOCK_MAX_WAIT or waited >= LOCK_MAX_WAIT:
            logger.warning('WhatsApp lock for %s still held after %ss', phone[-4:], LOCK_MAX_WAIT)
            raise LockBusy(f'lock busy after {LOCK_MAX_WAIT}s')
        deps.sleep(1)
        waited += 1


def release_lock(db, phone, owner, now):
    """Only releases a lock that is still ours (it may have been taken over). Never raises."""
    ref = db.collection(LOCKS).document(phone)
    try:
        transaction = db.transaction()

        @pending._transactional
        def run(txn):
            snapshot = ref.get(transaction=txn)
            if snapshot.exists and snapshot.to_dict().get('owner_sid') == owner:
                txn.update(ref, {'owner_sid': None, 'until': now})

        run(transaction)
    except Exception as exc:  # noqa: BLE001 - the lock expires by itself; never mask the real result
        logger.warning('Releasing the WhatsApp lock failed: %s', exc)
