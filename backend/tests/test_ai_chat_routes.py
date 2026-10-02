"""Tests for the AI chat endpoint: authentication, model params and financial summary"""
import os
import sys
from types import SimpleNamespace

import pytest
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes import ai_chat_routes  # noqa: E402
from utils import auth  # noqa: E402


class FakeMessages:
    def __init__(self):
        self.calls = []

    def create(self, **params):
        self.calls.append(params)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="ok")],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
            model=params["model"],
        )


@pytest.fixture
def fake_client(monkeypatch):
    client = SimpleNamespace(messages=FakeMessages())
    monkeypatch.setattr(ai_chat_routes, "anthropic_client", client)
    return client


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(auth, "get_db", lambda: object())
    monkeypatch.setattr(auth, "_warned_open_allowlist", False)
    app = Flask(__name__)
    app.register_blueprint(ai_chat_routes.ai_chat_bp)
    return app.test_client()


def _verify_as(monkeypatch, email):
    monkeypatch.setattr(
        auth.firebase_auth, "verify_id_token",
        lambda token: {"uid": "u1", "email": email},
    )


def _post(client, token="good-token"):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/api/ai-chat/", json={"messages": [{"role": "user", "content": "hola"}]}, headers=headers)


def test_rejects_missing_token(client, fake_client):
    assert _post(client, token=None).status_code == 401
    assert fake_client.messages.calls == []


def test_rejects_invalid_token(client, fake_client, monkeypatch):
    def boom(token):
        raise ValueError("bad token")
    monkeypatch.setattr(auth.firebase_auth, "verify_id_token", boom)
    assert _post(client).status_code == 401
    assert fake_client.messages.calls == []


def test_rejects_user_outside_allowlist(client, fake_client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "pablo@example.com")
    _verify_as(monkeypatch, "intruso@example.com")
    assert _post(client).status_code == 403
    assert fake_client.messages.calls == []


def test_accepts_admin_from_allowlist_case_insensitive(client, fake_client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "Pablo@Example.com, otro@example.com")
    _verify_as(monkeypatch, "pablo@example.com")
    response = _post(client)
    assert response.status_code == 200
    assert response.get_json()["response"] == "ok"


def test_accepts_any_authenticated_user_when_allowlist_unset(client, fake_client, monkeypatch):
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    _verify_as(monkeypatch, "cualquiera@example.com")
    assert _post(client).status_code == 200


def test_health_stays_public(client):
    assert client.get("/api/ai-chat/health").status_code in (200, 503)


def test_model_and_temperature_come_from_config(client, fake_client, monkeypatch):
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    _verify_as(monkeypatch, "a@example.com")
    monkeypatch.setattr(ai_chat_routes, "AI_CHAT_MODEL", "test-model")
    monkeypatch.setattr(ai_chat_routes, "AI_CHAT_TEMPERATURE", 0.2)
    _post(client)
    params = fake_client.messages.calls[0]
    assert params["model"] == "test-model"
    assert params["temperature"] == 0.2


def test_temperature_omitted_when_not_configured(client, fake_client, monkeypatch):
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    _verify_as(monkeypatch, "a@example.com")
    monkeypatch.setattr(ai_chat_routes, "AI_CHAT_TEMPERATURE", None)
    _post(client)
    assert "temperature" not in fake_client.messages.calls[0]


def test_financial_summary_does_not_fall_back_to_previous_year(monkeypatch):
    requested = []

    def fake_events(date_from=None, date_to=None, limit=50):
        requested.append((date_from, date_to))
        return {"count": 0, "events": [], "summary": {
            "total_revenue": 0, "total_cost": 0, "total_profit": 0, "average_profit_margin": 0}}

    monkeypatch.setattr(ai_chat_routes, "get_db", lambda: object())
    monkeypatch.setattr(ai_chat_routes, "get_events_data", fake_events)
    current_year = ai_chat_routes.datetime.now().year

    result = ai_chat_routes.get_financial_summary(current_year, 10)

    assert requested == [(f"{current_year}-10-01", f"{current_year}-10-31")]
    assert result["year"] == current_year
    assert result["event_count"] == 0
    assert "fallback_used" not in result
    assert "No hay eventos" in result["note"]
