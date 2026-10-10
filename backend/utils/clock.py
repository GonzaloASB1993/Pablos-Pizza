"""Business clock: Cloud Run runs in UTC, but "today" for Pablo's Pizza is the day in Chile.

From about 20:00-21:00 in Santiago the UTC date is already tomorrow's, which would shift "mañana", "el sábado",
the "date already passed" check, etc. Everything that means "today" in the assistant goes through here.
"""
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo('America/Santiago')
except Exception:  # noqa: BLE001 - no tz database on this machine: fixed UTC-3 (Chile's summer offset) is closer than UTC
    _TZ = timezone(timedelta(hours=-3))


def now_cl(now_utc=None):
    """Naive datetime in Chile's local time. `now_utc` (aware or naive UTC) is for tests."""
    base = now_utc if now_utc is not None else datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base.astimezone(_TZ).replace(tzinfo=None)


def today_cl(now_utc=None):
    return now_cl(now_utc).date()
