"""Shared Flask-Limiter instance.

Behind Cloud Run / Firebase Hosting `request.remote_addr` is the proxy, so the client is identified from
X-Forwarded-For. The LEFT entries are whatever the client sent (spoofable): only the entries appended by Google's own
proxies are trusted, so the key is the Nth entry from the RIGHT (N = TRUSTED_PROXY_HOPS, default 1). Falls back to
remote_addr when the header is absent. Verify N against real logs before relying on per-IP limits.
"""
import os

from flask import request
from flask_limiter import Limiter

# More reasonable limits for admin operations
DEFAULT_LIMITS = ["10000 per day", "1000 per hour"]


def client_key():
    try:
        hops = max(1, int(os.getenv('TRUSTED_PROXY_HOPS', '1')))
    except ValueError:
        hops = 1
    parts = [p.strip() for p in request.headers.get('X-Forwarded-For', '').split(',') if p.strip()]
    if len(parts) >= hops:
        return parts[-hops]
    return request.remote_addr or '127.0.0.1'


limiter = Limiter(
    client_key,
    default_limits=DEFAULT_LIMITS,
    storage_uri="memory://",  # in-memory (sufficient for a single instance)
)


def init_limiter(app):
    limiter.init_app(app)
    return limiter
