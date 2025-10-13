"""
Data Serialization Utilities
Functions for safely serializing Firestore documents and datetime objects
"""
from datetime import datetime
from google.cloud.firestore_v1.base_document import DocumentSnapshot


def safe_datetime_to_iso(dt):
    """
    Safely convert datetime object to ISO string

    Args:
        dt: datetime object, string, or None

    Returns:
        str: ISO format datetime string or None
    """
    if dt is None:
        return None

    if isinstance(dt, str):
        return dt

    try:
        if hasattr(dt, 'isoformat'):
            return dt.isoformat()
        return str(dt)
    except Exception:
        return None


def serialize_firestore_doc(doc: DocumentSnapshot) -> dict:
    """
    Serialize Firestore document to dict with safe datetime handling

    Args:
        doc: Firestore DocumentSnapshot

    Returns:
        dict: Serialized document with id and converted datetimes
    """
    if not doc.exists:
        return None

    data = doc.to_dict()
    data['id'] = doc.id

    # Convert datetime fields
    datetime_fields = ['created_at', 'updated_at', 'event_date', 'uploaded_at', 'sent_at']

    for field in datetime_fields:
        if field in data and data[field]:
            data[field] = safe_datetime_to_iso(data[field])

    return data


def serialize_firestore_docs(docs: list) -> list:
    """
    Serialize multiple Firestore documents

    Args:
        docs: List of DocumentSnapshot objects

    Returns:
        list: List of serialized documents
    """
    return [serialize_firestore_doc(doc) for doc in docs if doc.exists]
