"""Shared Flask-Limiter instance.

Behind Cloud Run / Firebase Hosting `request.remote_addr` is the proxy, so the client is identified by the first hop
of X-Forwarded-For (falling back to remote_addr when the header is absent).
"""
from flask import request
from flask_limiter import Limiter

# More reasonable limits for admin operations
DEFAULT_LIMITS = ["10000 per day", "1000 per hour"]


def client_key():
    forwarded = request.headers.get('X-Forwarded-For', '')
    first = forwarded.split(',')[0].strip()
    return first or request.remote_addr or '127.0.0.1'


limiter = Limiter(
    client_key,
    default_limits=DEFAULT_LIMITS,
    storage_uri="memory://",  # in-memory (sufficient for a single instance)
)


def init_limiter(app):
    limiter.init_app(app)
    return limiter
