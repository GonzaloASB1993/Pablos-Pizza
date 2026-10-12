"""Shared pytest configuration"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def authenticate_as_admin(monkeypatch, client, email='admin@test.example'):
    """Make every request of `client` carry a Firebase token that verifies as an allowed admin (offline)."""
    from utils import auth
    monkeypatch.setenv('ADMIN_EMAILS', email)
    monkeypatch.delenv('ENVIRONMENT', raising=False)
    monkeypatch.setattr(auth, 'get_db', lambda: object())
    monkeypatch.setattr(auth.firebase_auth, 'verify_id_token', lambda token: {'uid': 'admin-uid', 'email': email})
    client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer test-token'
    return client


@pytest.fixture(autouse=True)
def _plain_messages_endpoint(monkeypatch):
    """Fake Anthropic clients implement `messages.create` only; the beta fallback
    path has its own test (test_server_side_fallback_uses_the_beta_endpoint)."""
    from routes import ai_chat_routes
    monkeypatch.setattr(ai_chat_routes, "AI_CHAT_SERVER_FALLBACK", False)
