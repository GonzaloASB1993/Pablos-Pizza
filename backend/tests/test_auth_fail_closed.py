"""require_admin fails closed in production when ADMIN_EMAILS is not configured"""
import os
import sys

import pytest
from flask import Flask, jsonify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import auth  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(auth, 'get_db', lambda: object())
    monkeypatch.setattr(auth, '_warned_open_allowlist', False)
    monkeypatch.setattr(auth.firebase_auth, 'verify_id_token', lambda t: {'uid': 'u1', 'email': 'a@b.cl'})
    app = Flask(__name__)

    @app.route('/x')
    @auth.require_admin
    def x():
        return jsonify(ok=True)

    return app.test_client()


H = {'Authorization': 'Bearer t'}


def test_production_without_admin_emails_is_503(client, monkeypatch):
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.delenv('ADMIN_EMAILS', raising=False)
    res = client.get('/x', headers=H)
    assert res.status_code == 503 and 'error' in res.get_json()


def test_production_with_blank_admin_emails_is_503(client, monkeypatch):
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setenv('ADMIN_EMAILS', ' , ')
    assert client.get('/x', headers=H).status_code == 503


def test_production_with_allowlist_works(client, monkeypatch):
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setenv('ADMIN_EMAILS', 'a@b.cl')
    assert client.get('/x', headers=H).status_code == 200


def test_production_still_401_without_token(client, monkeypatch):
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.delenv('ADMIN_EMAILS', raising=False)
    assert client.get('/x').status_code == 401


def test_development_keeps_open_mode(client, monkeypatch):
    monkeypatch.setenv('ENVIRONMENT', 'development')
    monkeypatch.delenv('ADMIN_EMAILS', raising=False)
    assert client.get('/x', headers=H).status_code == 200


def test_unset_environment_keeps_open_mode(client, monkeypatch):
    monkeypatch.delenv('ENVIRONMENT', raising=False)
    monkeypatch.delenv('ADMIN_EMAILS', raising=False)
    assert client.get('/x', headers=H).status_code == 200


def test_marker_survives_stacked_decorators():
    def deco(f):
        from functools import wraps

        @wraps(f)
        def w(*a, **k):
            return f(*a, **k)
        return w

    @deco
    @auth.require_admin
    @deco
    def v():
        pass

    @deco
    @auth.require_scheduler_or_admin
    def v2():
        pass

    assert getattr(v, '_requires_admin', False)
    assert getattr(v2, '_requires_admin', False)
