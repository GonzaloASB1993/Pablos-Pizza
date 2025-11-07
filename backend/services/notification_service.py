"""
Notification Service
Track WhatsApp notifications sent to prevent duplicates and maintain history
"""
from datetime import datetime, timedelta
from database import get_db
from firebase_admin import firestore
import logging

logger = logging.getLogger(__name__)


def log_notification(booking_id: str, notification_type: str, recipient: str,
                     template_sid: str, success: bool, error_message: str = None) -> str:
    """
    Log a notification attempt in Firestore

    Args:
        booking_id: ID of the booking/event
        notification_type: Type of notification (e.g., 'overdue_reminder_single')
        recipient: Phone number of recipient
        template_sid: Twilio template SID used
        success: Whether the notification was sent successfully
        error_message: Error message if failed

    Returns:
        str: ID of the notification log document
    """
    try:
        db = get_db()
        notification_data = {
            'booking_id': booking_id,
            'notification_type': notification_type,
            'recipient': recipient,
            'template_sid': template_sid,
            'success': success,
            'error_message': error_message,
            'created_at': datetime.now(),
            'sent_at': datetime.now() if success else None
        }

        doc_ref = db.collection('notifications').add(notification_data)
        notification_id = doc_ref[1].id

        logger.info(f"✅ Notification logged: {notification_id} for booking {booking_id}")
        return notification_id

    except Exception as e:
        logger.error(f"❌ Error logging notification: {e}")
        return None


def check_recent_notification(booking_id: str, notification_type: str,
                              days_threshold: int = 3) -> bool:
    """
    Check if a notification was recently sent for this booking

    Args:
        booking_id: ID of the booking/event
        notification_type: Type of notification to check
        days_threshold: Number of days to consider as "recent" (default: 3)

    Returns:
        bool: True if a recent notification exists, False otherwise
    """
    try:
        db = get_db()
        threshold_date = datetime.now() - timedelta(days=days_threshold)

        # Query for recent successful notifications
        recent_notifications = db.collection('notifications')\
            .where('booking_id', '==', booking_id)\
            .where('notification_type', '==', notification_type)\
            .where('success', '==', True)\
            .where('created_at', '>=', threshold_date)\
            .limit(1)\
            .get()

        has_recent = len(list(recent_notifications)) > 0

        if has_recent:
            logger.info(f"⚠️ Recent notification found for booking {booking_id} within {days_threshold} days")

        return has_recent

    except Exception as e:
        error_message = str(e)
        logger.error(f"❌ Error checking recent notification: {error_message}")

        # If it's an index error, allow the notification to be sent
        # (missing indexes shouldn't block legitimate notifications)
        if "requires an index" in error_message or "index" in error_message.lower():
            logger.warning(f"⚠️ Index missing - allowing notification (create indexes to fix)")
            return False

        # For other errors, fail safe: return True to prevent duplicate sends
        logger.warning(f"⚠️ Unknown error - blocking notification as failsafe")
        return True


def get_notification_history(booking_id: str) -> list:
    """
    Get all notifications sent for a specific booking

    Args:
        booking_id: ID of the booking/event

    Returns:
        list: List of notification documents
    """
    try:
        db = get_db()
        notifications = db.collection('notifications')\
            .where('booking_id', '==', booking_id)\
            .order_by('created_at', direction=firestore.Query.DESCENDING)\
            .get()

        return [{'id': doc.id, **doc.to_dict()} for doc in notifications]

    except Exception as e:
        logger.error(f"❌ Error getting notification history: {e}")
        return []


def get_daily_notification_count(notification_type: str = None) -> int:
    """
    Get count of notifications sent today

    Args:
        notification_type: Optional filter by notification type

    Returns:
        int: Number of notifications sent today
    """
    try:
        db = get_db()
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        query = db.collection('notifications')\
            .where('created_at', '>=', today_start)\
            .where('success', '==', True)

        if notification_type:
            query = query.where('notification_type', '==', notification_type)

        notifications = query.get()
        count = len(list(notifications))

        logger.info(f"📊 Daily notification count: {count}")
        return count

    except Exception as e:
        logger.error(f"❌ Error getting daily notification count: {e}")
        return 0


def create_batch_notification_log(booking_ids: list, recipient: str,
                                  template_sid: str, success: bool) -> str:
    """
    Log a batch notification (multiple events in one message)

    Args:
        booking_ids: List of booking IDs included in the batch
        recipient: Phone number of recipient
        template_sid: Twilio template SID used
        success: Whether the notification was sent successfully

    Returns:
        str: ID of the batch notification log document
    """
    try:
        db = get_db()
        batch_data = {
            'booking_ids': booking_ids,
            'booking_count': len(booking_ids),
            'notification_type': 'overdue_reminder_multiple',
            'recipient': recipient,
            'template_sid': template_sid,
            'success': success,
            'created_at': datetime.now(),
            'sent_at': datetime.now() if success else None
        }

        doc_ref = db.collection('notifications').add(batch_data)
        batch_id = doc_ref[1].id

        logger.info(f"✅ Batch notification logged: {batch_id} for {len(booking_ids)} bookings")
        return batch_id

    except Exception as e:
        logger.error(f"❌ Error logging batch notification: {e}")
        return None
