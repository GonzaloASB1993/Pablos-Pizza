"""Rate-limit key: first X-Forwarded-For hop (Cloud Run / Firebase Hosting), else remote_addr"""
import os
import sys

from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import limiter as lim  # noqa: E402


def _key(headers=None, addr='9.9.9.9'):
    app = Flask(__name__)
    with app.test_request_context('/', headers=headers or {}, environ_base={'REMOTE_ADDR': addr}):
        return lim.client_key()


def test_the_last_forwarded_hop_is_the_key():
    assert _key({'X-Forwarded-For': '6.6.6.6, 1.2.3.4'}) == '1.2.3.4'


def test_a_spoofed_left_entry_does_not_change_the_key():
    assert _key({'X-Forwarded-For': '1.1.1.1, 1.2.3.4'}) == _key({'X-Forwarded-For': '2.2.2.2, 1.2.3.4'})


def test_trusted_hops_is_configurable(monkeypatch):
    monkeypatch.setenv('TRUSTED_PROXY_HOPS', '2')
    assert _key({'X-Forwarded-For': '6.6.6.6, 1.2.3.4, 10.0.0.1'}) == '1.2.3.4'


def test_single_forwarded_value_is_stripped():
    assert _key({'X-Forwarded-For': ' 1.2.3.4 '}) == '1.2.3.4'


def test_falls_back_to_remote_addr():
    assert _key() == '9.9.9.9'


def test_blank_forwarded_header_falls_back():
    assert _key({'X-Forwarded-For': ' , '}) == '9.9.9.9'


def test_main_exports_the_shared_limiter():
    import main
    assert main.limiter is lim.limiter
