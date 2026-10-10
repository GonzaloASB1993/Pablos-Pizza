"""
Firebase ID token authentication for admin-only endpoints.

The frontend sends `Authorization: Bearer <Firebase ID token>`. The token is
verified with the Firebase Admin SDK and, when the ADMIN_EMAILS environment
variable is set (comma separated), the caller must be on that allowlist.
"""
import logging
import os
from functools import wraps

from firebase_admin import auth as firebase_auth
from flask import g, jsonify, request

from database import get_db

logger = logging.getLogger(__name__)

_warned_open_allowlist = False


def _admin_emails():
    """Return the lowercase set of allowed admin emails (empty = not configured)."""
    raw = os.getenv('ADMIN_EMAILS', '')
    return {email.strip().lower() for email in raw.split(',') if email.strip()}


def _extract_bearer_token():
    header = request.headers.get('Authorization', '')
    scheme, _, token = header.partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        return None
    return token.strip()


def require_admin(view):
    """Reject requests without a valid Firebase ID token from an allowed admin.

    On success the verified identity is available as `g.current_user`
    ({'uid': ..., 'email': ...}).
    """
    @wraps(view)
    def wrapper(*args, **kwargs):
        # CORS preflight carries no credentials
        if request.method == 'OPTIONS':
            return view(*args, **kwargs)

        token = _extract_bearer_token()
        if not token:
            return jsonify({"error": "Authentication required"}), 401

        # Make sure the default Firebase app is initialized before verifying
        if get_db() is None:
            logger.error("Firebase is not initialized; cannot verify token")
            return jsonify({"error": "Authentication service unavailable"}), 503

        try:
            decoded = firebase_auth.verify_id_token(token)
        except Exception as exc:  # invalid, expired or revoked token
            logger.warning(f"Invalid ID token: {type(exc).__name__}")
            return jsonify({"error": "Invalid or expired token"}), 401

        email = (decoded.get('email') or '').lower()
        allowed = _admin_emails()

        if allowed:
            if email not in allowed:
                logger.warning(f"Non-admin user tried to access {request.path}: {email}")
                return jsonify({"error": "Forbidden"}), 403
        else:
            global _warned_open_allowlist
            if not _warned_open_allowlist:
                logger.warning(
                    "ADMIN_EMAILS is not set: any authenticated Firebase user is accepted. "
                    "Set ADMIN_EMAILS to restrict access to admins."
                )
                _warned_open_allowlist = True

        g.current_user = {'uid': decoded.get('uid'), 'email': email}
        return view(*args, **kwargs)

    return wrapper
