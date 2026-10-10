"""Shared pytest configuration"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def _plain_messages_endpoint(monkeypatch):
    """Fake Anthropic clients implement `messages.create` only; the beta fallback
    path has its own test (test_server_side_fallback_uses_the_beta_endpoint)."""
    from routes import ai_chat_routes
    monkeypatch.setattr(ai_chat_routes, "AI_CHAT_SERVER_FALLBACK", False)
