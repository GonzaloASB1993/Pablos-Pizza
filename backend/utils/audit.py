"""
Audit logging system for tracking admin actions
Records all critical operations for accountability and debugging
"""

from datetime import datetime
from functools import wraps
from flask import request
from firebase_admin import firestore


def get_db():
    """Get Firestore client with lazy initialization"""
    return firestore.client()


def log_audit(user_email, action, resource_type, resource_id, changes=None, metadata=None):
    """
    Log an audit entry to Firestore

    Args:
        user_email: Email of user performing action
        action: Action performed (create, update, delete, complete, cancel, etc.)
        resource_type: Type of resource (booking, event, inventory, etc.)
        resource_id: ID of the resource
        changes: Dictionary of changes made (optional)
        metadata: Additional metadata (optional)
    """
    try:
        db = get_db()  # Lazy load DB

        audit_entry = {
            "timestamp": datetime.utcnow(),
            "user_email": user_email or "system",
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "changes": changes or {},
            "metadata": metadata or {},
            "ip_address": request.remote_addr if request else None,
            "user_agent": request.headers.get('User-Agent') if request else None
        }

        # Save to Firestore
        db.collection('audit_logs').add(audit_entry)
        print(f"[OK] Audit log: {user_email} {action} {resource_type}/{resource_id}")

    except Exception as e:
        # Don't fail the main operation if audit logging fails
        print(f"[ERROR] Audit logging error: {e}")


def audit_log(resource_type, action=None):
    """
    Decorator for automatic audit logging

    Usage:
        @audit_log('booking', 'update')
        def update_booking(booking_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get resource_id from function arguments
            resource_id = kwargs.get('id') or kwargs.get('booking_id') or kwargs.get('event_id') or 'unknown'

            # Get user email from request (assumes JWT auth)
            user_email = request.headers.get('X-User-Email', 'unknown')

            # Determine action from function name if not provided
            determined_action = action or func.__name__.replace('_', ' ')

            # Execute the original function
            result = func(*args, **kwargs)

            # Log the audit entry
            log_audit(
                user_email=user_email,
                action=determined_action,
                resource_type=resource_type,
                resource_id=str(resource_id),
                metadata={'function': func.__name__}
            )

            return result

        return wrapper
    return decorator
