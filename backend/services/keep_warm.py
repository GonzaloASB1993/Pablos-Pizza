"""Keep the two functions warm during working hours, for free (no paid minimum instance).

Every few minutes a scheduled function:
  1. calls `main` (the web API and the Twilio webhook live there), and
  2. creates `whatsapp_inbox/warmup-<epoch>` so the Firestore trigger wakes the WhatsApp worker, which loads the
     assistant SDK while nobody is waiting; real messages then find everything ready.
Warm-up documents are ignored by the worker (their status is not `received`) and cleaned up here.
"""
import logging
import os
import time
from datetime import datetime, timedelta

from services import whatsapp_agent as wa

logger = logging.getLogger(__name__)

DEFAULT_URL = 'https://main-4kqeqojbsq-uc.a.run.app'
KEEP_FOR = timedelta(minutes=30)
WARMUP_PREFIX = 'warmup-'
CACHE_WARM_EVERY = 45 * 60   # the prompt cache lives 1 h; refresh it before it expires
_last_cache_warm = 0.0


def keep_warm(db, http_get=None, now=None):
    """Returns what it did (for logs/tests). Does nothing while the WhatsApp channel is switched off."""
    if not wa.enabled():
        return {'skipped': 'channel off'}
    now = now or datetime.utcnow()
    done = {}

    try:
        if http_get is None:
            import requests
            http_get = requests.get
        base = os.getenv('KEEP_WARM_URL', DEFAULT_URL).rstrip('/')
        done['main_status'] = http_get(f'{base}/api/ai-chat/health', timeout=8).status_code
    except Exception as exc:  # noqa: BLE001 - a missed ping is not an error worth failing the schedule for
        logger.warning('keep_warm: ping to main failed: %s', exc)
        done['main_status'] = None

    # wake the worker, then drop the old markers so the collection does not grow
    marker = f'{WARMUP_PREFIX}{int(time.time())}'
    db.collection(wa.INBOX).document(marker).set({'status': 'warmup', 'created_at': now})
    removed = 0
    for snapshot in db.collection(wa.INBOX).where('status', '==', 'warmup').stream():
        created = snapshot.to_dict().get('created_at')
        created = created.replace(tzinfo=None) if getattr(created, 'tzinfo', None) else created
        if snapshot.id != marker and created is not None and now - created > KEEP_FOR:
            snapshot.reference.delete()
            removed += 1
    done.update(marker=marker, removed=removed)
    return done


def is_warmup(sid):
    return str(sid).startswith(WARMUP_PREFIX)


def prewarm():
    """Load the heavy bits (assistant SDK client) ahead of the first real message"""
    from routes import ai_chat_routes
    ai_chat_routes.get_anthropic_client()

    global _last_cache_warm
    if os.getenv('AI_WHATSAPP_CACHE_WARM', 'true').strip().lower() == 'false':
        return
    if time.time() - _last_cache_warm >= CACHE_WARM_EVERY:
        _last_cache_warm = time.time()
        try:
            ai_chat_routes.warm_prompt_cache()
        except Exception as exc:  # noqa: BLE001 - cosmetic speed-up: never fail the warm-up
            logger.warning('keep_warm: prompt cache refresh failed: %s', exc)
