"""Twilio rejects WhatsApp template variables that are empty or contain line breaks (HTTP 400 "Content Variables invalid"):
this broke the admin notification when a booking had no location (production, 11/10/2026)"""
import asyncio
import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import whatsapp_service as ws  # noqa: E402


def test_clean_variables_replaces_empty_values_and_line_breaks():
    cleaned = ws.clean_template_variables({'1': 'Vero', '2': '', '3': None, '4': '   ', '5': 'a\nb\tc', '6': 'x    y', '7': 5})
    assert cleaned == {'1': 'Vero', '2': '-', '3': '-', '4': '-', '5': 'a b c', '6': 'x y', '7': '5'}


def test_the_template_is_sent_with_clean_variables(monkeypatch):
    sent = {}
    fake = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: sent.update(kw) or SimpleNamespace(sid='SM1')))
    monkeypatch.setattr(ws, 'twilio_client', fake)
    monkeypatch.setattr(ws, 'prepare_confirmed_booking_variables', lambda booking: {'1': 'Vero', '6': ''})
    assert asyncio.run(ws.send_whatsapp_template('+56911111111', 'booking_confirmed', {})) is True
    assert json.loads(sent['content_variables']) == {'1': 'Vero', '6': '-'}
