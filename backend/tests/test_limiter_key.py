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


def test_uses_first_forwarded_hop():
    assert _key({'X-Forwarded-For': '1.2.3.4, 10.0.0.1, 10.0.0.2'}) == '1.2.3.4'


def test_single_forwarded_value_is_stripped():
    assert _key({'X-Forwarded-For': ' 1.2.3.4 '}) == '1.2.3.4'


def test_falls_back_to_remote_addr():
    assert _key() == '9.9.9.9'


def test_blank_forwarded_header_falls_back():
    assert _key({'X-Forwarded-For': ' , '}) == '9.9.9.9'


def test_main_exports_the_shared_limiter():
    import main
    assert main.limiter is lim.limiter
