"""Panel endpoints: GET /pending/<id>/undo-preview and POST /pending/<id>/undo (admin only)"""
import os
import sys
from datetime import datetime, timedelta

import pytest
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402,F401
from routes import ai_chat_routes  # noqa: E402
from services import inventory_service as inv  # noqa: E402
from services import pending_actions_service as pas  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402
from tests.undo_support import confirmed, doc, item, seed_item  # noqa: E402
from utils import auth  # noqa: E402


@pytest.fixture
def env(monkeypatch):
    db = FakeFirestore()
    monkeypatch.setattr(auth, 'get_db', lambda: object())
    monkeypatch.setattr(auth, '_warned_open_allowlist', False)
    monkeypatch.setattr(ai_chat_routes, 'get_db', lambda: db)
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))
    monkeypatch.setattr('utils.audit.log_audit', lambda *a, **k: None)
    monkeypatch.delenv('ADMIN_EMAILS', raising=False)
    monkeypatch.setattr(auth.firebase_auth, 'verify_id_token', lambda token: {'uid': 'u1', 'email': 'admin@example.com'})
    app = Flask(__name__)
    app.register_blueprint(ai_chat_routes.ai_chat_bp)
    return app.test_client(), db


HEADERS = {'Authorization': 'Bearer t'}


def waste_action(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    return confirmed(db, 'stock_adjustment', {'item_id': 'flour', 'mode': 'waste', 'quantity': 3},
                     summary='Merma de Harina: -3 kg')


def test_both_endpoints_require_an_admin(env):
    client, _ = env
    assert client.get('/api/ai-chat/pending/x/undo-preview').status_code == 401
    assert client.post('/api/ai-chat/pending/x/undo').status_code == 401


def test_a_non_admin_is_rejected(env, monkeypatch):
    client, db = env
    action = waste_action(db)
    monkeypatch.setenv('ADMIN_EMAILS', 'pablo@example.com')
    assert client.get(f"/api/ai-chat/pending/{action['id']}/undo-preview", headers=HEADERS).status_code == 403
    assert client.post(f"/api/ai-chat/pending/{action['id']}/undo", headers=HEADERS).status_code == 403
    assert item(db, 'flour')['current_stock'] == 7


def test_preview_describes_without_writing(env):
    client, db = env
    action = waste_action(db)
    body = client.get(f"/api/ai-chat/pending/{action['id']}/undo-preview", headers=HEADERS).get_json()
    assert body['can_undo'] is True and body['label'] == 'Merma de Harina' and 'Harina: stock 7 → 10' in body['effects'][0]
    assert item(db, 'flour')['current_stock'] == 7


def test_preview_says_why_not(env):
    client, db = env
    action = waste_action(db)
    inv.register_movement(db, 'flour', 'purchase', 1, 1000, movement_id='later')
    response = client.get(f"/api/ai-chat/pending/{action['id']}/undo-preview", headers=HEADERS)
    body = response.get_json()
    assert response.status_code == 200 and body['can_undo'] is False
    assert body['reason'] == 'later_movements' and 'conteo' in body['message']


def test_undo_works_and_a_second_call_is_idempotent(env):
    client, db = env
    action = waste_action(db)
    first = client.post(f"/api/ai-chat/pending/{action['id']}/undo", headers=HEADERS)
    assert first.status_code == 200 and first.get_json()['undone'] is True and first.get_json()['already_undone'] is False
    assert item(db, 'flour')['current_stock'] == 10
    second = client.post(f"/api/ai-chat/pending/{action['id']}/undo", headers=HEADERS)
    assert second.status_code == 200 and second.get_json()['already_undone'] is True
    assert item(db, 'flour')['current_stock'] == 10 and len(db.store['inventory_movements']) == 2
    stored = client.get(f"/api/ai-chat/pending/{action['id']}", headers=HEADERS).get_json()['pending_action']
    assert stored['status'] == 'confirmed' and stored['undo']['state'] == 'done' and stored['undo']['by'] == 'admin@example.com'
    preview = client.get(f"/api/ai-chat/pending/{action['id']}/undo-preview", headers=HEADERS).get_json()
    assert preview['can_undo'] is False and preview['reason'] == 'already_undone'


def test_refusals_are_409_with_the_reason_and_unknown_ids_404(env):
    client, db = env
    action = waste_action(db)
    inv.register_movement(db, 'flour', 'purchase', 1, 1000, movement_id='later')
    res = client.post(f"/api/ai-chat/pending/{action['id']}/undo", headers=HEADERS)
    assert res.status_code == 409 and res.get_json()['reason'] == 'later_movements'
    assert client.post('/api/ai-chat/pending/nope/undo', headers=HEADERS).status_code == 404
    assert client.get('/api/ai-chat/pending/nope/undo-preview', headers=HEADERS).status_code == 404


def test_the_panel_window_is_7_days(env):
    client, db = env
    action = waste_action(db)
    db.collection('pending_actions').document(action['id']).update({'confirmed_at': datetime.utcnow() - timedelta(days=3)})
    assert client.post(f"/api/ai-chat/pending/{action['id']}/undo", headers=HEADERS).status_code == 200   # 24 h would refuse
    other = confirmed(db, 'stock_adjustment', {'item_id': 'flour', 'mode': 'waste', 'quantity': 1})
    db.collection('pending_actions').document(other['id']).update({'confirmed_at': datetime.utcnow() - timedelta(days=9)})
    res = client.post(f"/api/ai-chat/pending/{other['id']}/undo", headers=HEADERS)
    assert res.status_code == 409 and res.get_json()['reason'] == 'window'


def test_an_unexpected_failure_is_a_500_that_changed_nothing(env, monkeypatch):
    client, db = env
    action = waste_action(db)
    from tests import fakes

    def boom(self, *args, **kwargs):   # the fake applies a transaction's writes at once: failing the FIRST one = a failed commit
        raise RuntimeError('firestore down')
    monkeypatch.setattr(fakes.FakeTransaction, 'set', boom)
    res = client.post(f"/api/ai-chat/pending/{action['id']}/undo", headers=HEADERS)
    assert res.status_code == 500 and 'firestore down' not in res.get_data(as_text=True)
    assert item(db, 'flour')['current_stock'] == 7
    assert doc(db, 'pending_actions', action['id'])['undo']['state'] == 'failed'
