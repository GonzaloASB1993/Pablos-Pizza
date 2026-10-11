"""Tests for the alert state machine: a condition is announced once, re-armed when it clears, never spams"""
import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import alerts_service as alerts  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402

PHONE = '+56911111111'
NOW = datetime(2026, 10, 12, 13, 0, 0)       # 10:00 in Santiago (UTC-3), Monday 12 Oct 2026


@pytest.fixture
def db():
    return FakeFirestore()


def _item(db, item_id='harina', stock=2, minimum=5, **extra):
    db.collection('inventory').document(item_id).set(
        {'name': item_id.capitalize(), 'current_stock': stock, 'min_stock': minimum, 'unit': 'kg',
         'needs_restock': stock <= minimum, **extra})


def _booking(db, booking_id='b1', status='pending', event_date='2026-10-20', created=NOW - timedelta(hours=30), name='Ana'):
    db.collection('bookings').document(booking_id).set(
        {'client_name': name, 'status': status, 'event_date': event_date, 'created_at': created})


def _keys(active):
    return [a['key'] for a in active]


# ============ transitions ============

def test_a_new_condition_becomes_active_in_episode_one_and_is_stored(db):
    _item(db)
    active = alerts.evaluate(db, NOW)
    assert _keys(active) == ['low_stock:harina']
    doc = db.store['assistant_alerts']['low_stock:harina']
    assert doc['state'] == 'active' and doc['episode'] == 1 and doc['notified'] == {} and doc['label'] == 'Harina'


def test_a_condition_that_stays_the_same_is_not_new_again(db):
    _item(db)
    alerts.evaluate(db, NOW)
    db.store['assistant_alerts']['low_stock:harina']['notified'] = {PHONE: NOW}
    db.store['assistant_alerts']['low_stock:harina']['last_notified_at'] = NOW
    active = alerts.evaluate(db, NOW + timedelta(days=1))
    doc = db.store['assistant_alerts']['low_stock:harina']
    assert doc['episode'] == 1 and doc['notified'] == {PHONE: NOW} and doc['last_seen_at'] == NOW + timedelta(days=1)
    assert alerts.announceable(active, PHONE, alerts.default_prefs(), NOW + timedelta(days=1)) == []


def test_it_resolves_when_the_condition_clears_and_is_re_armed_if_it_returns(db):
    _item(db)
    alerts.evaluate(db, NOW)
    db.store['assistant_alerts']['low_stock:harina']['notified'] = {PHONE: NOW}
    _item(db, stock=20)                                            # restocked: clearly above the minimum
    assert alerts.evaluate(db, NOW + timedelta(days=1)) == []
    assert db.store['assistant_alerts']['low_stock:harina']['state'] == 'resolved'

    _item(db, stock=1)                                             # runs low again
    active = alerts.evaluate(db, NOW + timedelta(days=5))
    doc = db.store['assistant_alerts']['low_stock:harina']
    assert doc['state'] == 'active' and doc['episode'] == 2 and doc['notified'] == {}
    assert _keys(alerts.announceable(active, PHONE, alerts.default_prefs(), NOW + timedelta(days=5))) == ['low_stock:harina']


def test_stock_hysteresis_keeps_the_alert_until_it_is_clearly_above_the_minimum(db):
    _item(db, stock=5, minimum=5)
    alerts.evaluate(db, NOW)
    _item(db, stock=5.5, minimum=5)                                # above the minimum but under min * 1.2
    assert _keys(alerts.evaluate(db, NOW + timedelta(days=1))) == ['low_stock:harina']
    assert db.store['assistant_alerts']['low_stock:harina']['episode'] == 1
    _item(db, stock=6.5, minimum=5)                                # 6.5 > 6.0: resolved
    assert alerts.evaluate(db, NOW + timedelta(days=2)) == []
    assert db.store['assistant_alerts']['low_stock:harina']['state'] == 'resolved'


def test_a_flickering_stock_level_does_not_create_new_episodes(db):
    for day, stock in enumerate([5, 5.5, 5, 5.8, 4]):
        _item(db, stock=stock, minimum=5)
        alerts.evaluate(db, NOW + timedelta(days=day))
    assert db.store['assistant_alerts']['low_stock:harina']['episode'] == 1


def test_items_without_a_minimum_never_alert(db):
    _item(db, stock=0, minimum=0)
    assert alerts.evaluate(db, NOW) == []


def test_a_deleted_item_resolves_its_alert(db):
    _item(db)
    alerts.evaluate(db, NOW)
    del db.store['inventory']['harina']
    assert alerts.evaluate(db, NOW + timedelta(days=1)) == []
    assert db.store['assistant_alerts']['low_stock:harina']['state'] == 'resolved'


# ============ the other types ============

def test_a_pending_booking_needs_a_day_without_answer_and_a_future_event(db):
    _booking(db, 'old', created=NOW - timedelta(hours=30))
    _booking(db, 'fresh', created=NOW - timedelta(hours=5))
    _booking(db, 'past', event_date='2026-10-01', created=NOW - timedelta(days=20))
    _booking(db, 'done', status='confirmed', event_date='2026-10-25')
    assert _keys(alerts.evaluate(db, NOW)) == ['booking_pending:old']


def test_event_date_with_a_time_suffix_is_understood(db):
    _booking(db, 'b1', event_date='2026-10-20T16:00:00')
    _booking(db, 'b2', status='confirmed', event_date='2026-10-13T16:00:00')
    assert set(_keys(alerts.evaluate(db, NOW))) == {'booking_pending:b1', 'event_tomorrow:b2'}


def test_a_pending_booking_close_to_its_date_is_urgent_instead_of_a_plain_reminder(db):
    _booking(db, 'b1', event_date='2026-10-15')                     # 3 days left
    assert _keys(alerts.evaluate(db, NOW)) == ['booking_pending_urgent:b1']


def test_events_for_tomorrow_use_the_chile_calendar_not_utc(db):
    _booking(db, 'tomorrow', status='confirmed', event_date='2026-10-13')
    _booking(db, 'today', status='confirmed', event_date='2026-10-12')
    _booking(db, 'later', status='confirmed', event_date='2026-10-14')
    assert _keys(alerts.evaluate(db, NOW)) == ['event_tomorrow:tomorrow']
    # 00:30 UTC on the 13th is still the evening of the 12th in Chile: "tomorrow" is the 13th, not the 14th
    late = datetime(2026, 10, 13, 0, 30)
    assert _keys(alerts.evaluate(db, late, persist=False)) == ['event_tomorrow:tomorrow']


def test_proposals_wait_three_hours_and_must_not_be_expired(db):
    def action(action_id, age_h, expires_in_h=20, status='pending'):
        db.collection('pending_actions').document(action_id).set(
            {'status': status, 'summary': f'Compra {action_id}', 'type': 'expense',
             'created_at': NOW - timedelta(hours=age_h), 'expires_at': NOW + timedelta(hours=expires_in_h)})
    action('waiting', 4)
    action('fresh', 1)
    action('expired', 30, expires_in_h=-6)
    action('done', 5, status='confirmed')
    assert _keys(alerts.evaluate(db, NOW)) == ['proposal_pending:waiting']


def test_most_important_alerts_come_first(db):
    _item(db)
    _booking(db, 'u', event_date='2026-10-14')
    _booking(db, 't', status='confirmed', event_date='2026-10-13')
    assert [a['type'] for a in alerts.evaluate(db, NOW)] == ['booking_pending_urgent', 'event_tomorrow', 'low_stock']


# ============ who hears about what ============

def test_announceable_skips_what_the_number_already_heard(db):
    _item(db)
    active = alerts.evaluate(db, NOW)
    batch = db.batch()
    alerts.mark_notified(db, batch, active, PHONE, NOW)
    batch.commit()
    again = alerts.evaluate(db, NOW + timedelta(days=1))
    assert alerts.announceable(again, PHONE, alerts.default_prefs(), NOW + timedelta(days=1)) == []
    assert len(alerts.announceable(again, '+56922222222', alerts.default_prefs(), NOW + timedelta(days=1))) == 1


def test_cooldown_of_72_hours_applies_even_to_a_new_episode(db):
    _item(db)
    alerts.evaluate(db, NOW)
    batch = db.batch()
    alerts.mark_notified(db, batch, [{**db.store['assistant_alerts']['low_stock:harina'], 'key': 'low_stock:harina'}], PHONE, NOW)
    batch.commit()
    _item(db, stock=30)
    alerts.evaluate(db, NOW + timedelta(hours=10))                  # resolved
    _item(db, stock=1)
    soon = alerts.evaluate(db, NOW + timedelta(hours=30))           # back: new episode, but announced 30 h ago
    assert db.store['assistant_alerts']['low_stock:harina']['episode'] == 2
    assert alerts.announceable(soon, PHONE, alerts.default_prefs(), NOW + timedelta(hours=30)) == []
    later = alerts.evaluate(db, NOW + timedelta(hours=73))
    assert len(alerts.announceable(later, PHONE, alerts.default_prefs(), NOW + timedelta(hours=73))) == 1


def test_muted_types_keys_and_pause_are_respected(db):
    _item(db)
    _booking(db, 'b1', event_date='2026-10-30')
    _booking(db, 't', status='confirmed', event_date='2026-10-13')
    active = alerts.evaluate(db, NOW)

    def heard(prefs):
        return set(_keys(alerts.announceable(active, PHONE, {**alerts.default_prefs(), **prefs}, NOW)))

    assert heard({}) == {'low_stock:harina', 'booking_pending:b1', 'event_tomorrow:t'}
    assert heard({'muted_types': ['low_stock']}) == {'booking_pending:b1', 'event_tomorrow:t'}
    assert heard({'muted_keys': {'booking_pending:b1': 'x'}}) == {'low_stock:harina', 'event_tomorrow:t'}
    assert heard({'paused': True}) == set()


def test_preview_mode_changes_nothing(db):
    _item(db)
    assert _keys(alerts.evaluate(db, NOW, persist=False)) == ['low_stock:harina']
    assert 'assistant_alerts' not in db.store
