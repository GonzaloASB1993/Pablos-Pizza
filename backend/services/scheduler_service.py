"""
Scheduler Service
Check for overdue events and send WhatsApp reminders to admin
"""
import os
import asyncio
from datetime import datetime, timedelta
from database import get_db
from firebase_admin import firestore
from services.whatsapp_service import send_overdue_reminder
from services.notification_service import (
    check_recent_notification,
    log_notification,
    create_batch_notification_log,
    get_daily_notification_count
)
import logging

logger = logging.getLogger(__name__)

# Configuration
ADMIN_PHONE = os.getenv('ADMIN_WHATSAPP_NUMBER', '+56989424566')
ADMIN_NAME = os.getenv('ADMIN_NAME', 'Juan Pablo')
DAYS_THRESHOLD = int(os.getenv('OVERDUE_DAYS_THRESHOLD', '2'))  # Days after event to consider overdue
MAX_REMINDERS_PER_DAY = int(os.getenv('MAX_REMINDERS_PER_DAY', '10'))


async def check_overdue_events() -> dict:
    """
    Check for overdue events and send WhatsApp reminders to admin

    This function:
    1. Queries bookings with event_date > 2 days ago and status != 'completed'
    2. Filters out events that already received reminders recently
    3. Sends single or batch WhatsApp reminder to admin
    4. Logs all notifications sent

    Returns:
        dict: Summary of the check operation
    """
    try:
        logger.info("🔍 Starting overdue events check...")

        # Rate limiting check
        daily_count = get_daily_notification_count('overdue_reminder')
        if daily_count >= MAX_REMINDERS_PER_DAY:
            logger.warning(f"⚠️ Daily reminder limit reached ({daily_count}/{MAX_REMINDERS_PER_DAY})")
            return {
                'success': False,
                'message': 'Daily reminder limit reached',
                'overdue_count': 0,
                'reminders_sent': 0
            }

        db = get_db()
        if not db:
            logger.error("❌ Database connection failed")
            return {
                'success': False,
                'message': 'Database connection failed',
                'overdue_count': 0,
                'reminders_sent': 0
            }

        # Calculate threshold date
        threshold_date = datetime.now() - timedelta(days=DAYS_THRESHOLD)
        threshold_date_str = threshold_date.strftime('%Y-%m-%d')

        logger.info(f"📅 Checking events before: {threshold_date_str}")

        # Query overdue bookings
        # Get all bookings with event_date < threshold, then filter in memory
        # This avoids the need for a composite index
        bookings_query = db.collection('bookings')\
            .where('event_date', '<', threshold_date_str)\
            .order_by('event_date', direction=firestore.Query.DESCENDING)\
            .limit(100)\
            .get()

        all_overdue = []
        for doc in bookings_query:
            booking = doc.to_dict()
            booking['id'] = doc.id

            # Filter out completed events in memory
            status = booking.get('status', '')
            if status != 'completed':
                all_overdue.append(booking)

        logger.info(f"📊 Found {len(all_overdue)} overdue bookings")

        if not all_overdue:
            logger.info("✅ No overdue events found")
            return {
                'success': True,
                'message': 'No overdue events found',
                'overdue_count': 0,
                'reminders_sent': 0
            }

        # Filter out bookings that already received recent reminders
        bookings_to_notify = []
        for booking in all_overdue:
            booking_id = booking.get('id')

            # Check if reminder was sent recently (within 3 days)
            has_recent_reminder = check_recent_notification(
                booking_id,
                'overdue_reminder_single',
                days_threshold=3
            )

            if not has_recent_reminder:
                bookings_to_notify.append(booking)
            else:
                logger.info(f"⏭️ Skipping booking {booking_id} - recent reminder sent")

        logger.info(f"📨 {len(bookings_to_notify)} bookings need reminders")

        if not bookings_to_notify:
            logger.info("✅ All overdue events already have recent reminders")
            return {
                'success': True,
                'message': 'All overdue events already notified recently',
                'overdue_count': len(all_overdue),
                'reminders_sent': 0
            }

        # Send reminder(s)
        reminders_sent = 0

        if len(bookings_to_notify) == 1:
            # Send single event reminder
            booking = bookings_to_notify[0]
            logger.info(f"📱 Sending single event reminder for booking {booking.get('id')}")

            success = await send_overdue_reminder(
                phone=ADMIN_PHONE,
                admin_name=ADMIN_NAME,
                bookings=[booking],
                is_single=True
            )

            if success:
                # Log notification
                log_notification(
                    booking_id=booking.get('id'),
                    notification_type='overdue_reminder_single',
                    recipient=ADMIN_PHONE,
                    template_sid=os.getenv('TEMPLATE_EVENT_OVERDUE_SINGLE_SID', 'HXd00b109affda30cc4b0b2888b469014d'),
                    success=True
                )
                reminders_sent = 1
                logger.info("✅ Single reminder sent successfully")
            else:
                logger.error("❌ Failed to send single reminder")

        else:
            # Send multiple events reminder
            logger.info(f"📱 Sending batch reminder for {len(bookings_to_notify)} bookings")

            success = await send_overdue_reminder(
                phone=ADMIN_PHONE,
                admin_name=ADMIN_NAME,
                bookings=bookings_to_notify,
                is_single=False
            )

            if success:
                # Log batch notification
                booking_ids = [b.get('id') for b in bookings_to_notify]
                create_batch_notification_log(
                    booking_ids=booking_ids,
                    recipient=ADMIN_PHONE,
                    template_sid=os.getenv('TEMPLATE_EVENT_OVERDUE_MULTIPLE_SID', 'HXd65d75d0e47eb7b489b112b2f18f3382'),
                    success=True
                )
                reminders_sent = 1
                logger.info(f"✅ Batch reminder sent successfully for {len(bookings_to_notify)} events")
            else:
                logger.error("❌ Failed to send batch reminder")

        return {
            'success': True,
            'message': f'Check completed. Sent {reminders_sent} reminder(s)',
            'overdue_count': len(all_overdue),
            'pending_reminders': len(bookings_to_notify),
            'reminders_sent': reminders_sent,
            'threshold_date': threshold_date_str,
            'admin_notified': ADMIN_PHONE
        }

    except Exception as e:
        logger.error(f"❌ Error checking overdue events: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f'Error: {str(e)}',
            'overdue_count': 0,
            'reminders_sent': 0
        }


async def manual_check_overdue_events(force: bool = False) -> dict:
    """
    Manually trigger overdue events check (for testing)

    Args:
        force: If True, bypass daily limit check

    Returns:
        dict: Summary of the check operation
    """
    logger.info("🔧 Manual overdue check triggered")

    if force:
        # Temporarily increase limit for manual checks
        global MAX_REMINDERS_PER_DAY
        original_limit = MAX_REMINDERS_PER_DAY
        MAX_REMINDERS_PER_DAY = 999

        result = await check_overdue_events()

        MAX_REMINDERS_PER_DAY = original_limit
        return result
    else:
        return await check_overdue_events()
