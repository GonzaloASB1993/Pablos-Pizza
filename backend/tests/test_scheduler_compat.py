"""Cloud Scheduler sends X-CloudScheduler-ScheduleTime like 2026-10-12T08:44:04.308248-07:00 and firebase-functions 0.1.0
only parses '%Y-%m-%dT%H:%M:%S%z': every scheduled function answered HTTP 500 before running (keep_warm never warmed
anything, 12/10/2026). utils/scheduler_compat.py makes the SDK accept it."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402,F401  (applies the patch on import)
from firebase_functions import scheduler_fn  # noqa: E402


def _call(header):
    seen = []

    @scheduler_fn.on_schedule(schedule="* * * * *")
    def job(event):
        seen.append(event)

    headers = {'X-CloudScheduler-JobName': 'j'}
    if header:
        headers['X-CloudScheduler-ScheduleTime'] = header
    with main.app.app_context():
        response = job(SimpleNamespace(headers=headers))
    return response, seen


def test_fractional_seconds_with_an_offset_are_accepted():
    response, seen = _call('2026-10-12T08:44:04.308248-07:00')
    assert getattr(response, 'status_code', 200) == 200 and len(seen) == 1
    assert seen[0].schedule_time.utcoffset() is not None


def test_the_old_formats_and_a_missing_header_still_work():
    for header in ('2026-10-12T08:44:04+0000', '2026-10-12T15:44:04Z', None):
        response, seen = _call(header)
        assert getattr(response, 'status_code', 200) == 200 and len(seen) == 1, header
