"""Make firebase-functions 0.1.0 accept the schedule time Cloud Scheduler really sends.

The SDK parses X-CloudScheduler-ScheduleTime with strptime('%Y-%m-%dT%H:%M:%S%z'), but Cloud Scheduler sends
'2026-10-12T08:44:04.308248-07:00' (fractional seconds, colon in the offset): every scheduled function answered HTTP 500
before running. Newer SDK versions fixed it (fromisoformat); this keeps 0.1.0 and only widens what strptime accepts.
"""
import datetime as _dt
import types


class _TolerantDatetime(_dt.datetime):
    @classmethod
    def strptime(cls, date_string, fmt):
        try:
            return super().strptime(date_string, fmt)
        except ValueError:
            text = str(date_string)
            if text.endswith('Z'):
                text = text[:-1] + '+00:00'
            return _dt.datetime.fromisoformat(text)   # raises ValueError for garbage, like before


def apply():
    from firebase_functions import scheduler_fn
    shim = types.ModuleType('datetime')
    shim.__dict__.update({k: v for k, v in vars(_dt).items() if not k.startswith('__')})
    shim.datetime = _TolerantDatetime
    scheduler_fn._dt = shim
