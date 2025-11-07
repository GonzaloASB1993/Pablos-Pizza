"""
Diagnostic script to investigate why overdue event notifications are not being sent
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from database import get_db
from firebase_admin import firestore

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv('.env')

def diagnose_scheduler_issue():
    """
    Diagnose why overdue event reminders are not being sent
    """
    print("=" * 80)
    print("SCHEDULER DIAGNOSTIC TOOL")
    print("=" * 80)

    # Configuration check
    print("\n📋 CONFIGURATION:")
    DAYS_THRESHOLD = int(os.getenv('OVERDUE_DAYS_THRESHOLD', '2'))
    MAX_REMINDERS_PER_DAY = int(os.getenv('MAX_REMINDERS_PER_DAY', '10'))
    ADMIN_PHONE = os.getenv('ADMIN_WHATSAPP_NUMBER', '+56989424566')

    print(f"   Days Threshold: {DAYS_THRESHOLD}")
    print(f"   Max Reminders per Day: {MAX_REMINDERS_PER_DAY}")
    print(f"   Admin Phone: {ADMIN_PHONE}")

    # Date calculation
    threshold_date = datetime.now() - timedelta(days=DAYS_THRESHOLD)
    threshold_date_str = threshold_date.strftime('%Y-%m-%d')

    print(f"\n📅 DATE CALCULATION:")
    print(f"   Today: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Threshold Date: {threshold_date_str}")
    print(f"   Looking for events before: {threshold_date_str}")

    # Database connection
    db = get_db()
    if not db:
        print("\n❌ ERROR: Database connection failed")
        return

    print("\n✅ Database connected successfully")

    # Query overdue bookings
    print(f"\n🔎 SEARCHING FOR OVERDUE BOOKINGS:")
    print(f"   Query: event_date < '{threshold_date_str}' AND status != 'completed'")

    bookings_query = db.collection('bookings')\
        .where('event_date', '<', threshold_date_str)\
        .order_by('event_date', direction=firestore.Query.DESCENDING)\
        .limit(100)\
        .get()

    all_overdue = []
    completed_count = 0

    print("\n📊 FOUND BOOKINGS:")
    for idx, doc in enumerate(bookings_query, 1):
        booking = doc.to_dict()
        booking['id'] = doc.id

        event_date = booking.get('event_date', 'N/A')
        status = booking.get('status', 'N/A')
        client_name = booking.get('client_name', 'N/A')

        print(f"\n   [{idx}] Booking ID: {doc.id}")
        print(f"       Client: {client_name}")
        print(f"       Event Date: {event_date}")
        print(f"       Status: {status}")

        if status == 'completed':
            print(f"       ⏭️  SKIPPED (status is 'completed')")
            completed_count += 1
        else:
            all_overdue.append(booking)
            print(f"       ✅ INCLUDED (status is '{status}')")

    print(f"\n📈 SUMMARY:")
    print(f"   Total bookings found: {len(list(bookings_query))}")
    print(f"   Completed (skipped): {completed_count}")
    print(f"   Overdue (not completed): {len(all_overdue)}")

    if not all_overdue:
        print("\n⚠️  NO OVERDUE EVENTS FOUND")
        print("   Either all events are completed or there are no events before the threshold date")
        return

    # Check notification history for each overdue booking
    print("\n📨 CHECKING NOTIFICATION HISTORY:")

    from services.notification_service import check_recent_notification, get_daily_notification_count

    # Check daily limit
    daily_count = get_daily_notification_count('overdue_reminder')
    print(f"\n   Daily notifications sent today: {daily_count}/{MAX_REMINDERS_PER_DAY}")

    if daily_count >= MAX_REMINDERS_PER_DAY:
        print(f"   ⚠️  DAILY LIMIT REACHED - No more reminders will be sent today")

    bookings_to_notify = []
    for booking in all_overdue:
        booking_id = booking.get('id')
        client_name = booking.get('client_name', 'N/A')
        event_date = booking.get('event_date', 'N/A')

        print(f"\n   Booking: {client_name} ({event_date})")
        print(f"   ID: {booking_id}")

        # Check recent notifications
        has_recent_single = check_recent_notification(booking_id, 'overdue_reminder_single', days_threshold=3)

        # Also check if this booking was part of a batch notification
        # Get batch notifications that include this booking_id
        try:
            batch_notifications = db.collection('notifications')\
                .where('notification_type', '==', 'overdue_reminder_multiple')\
                .where('success', '==', True)\
                .order_by('created_at', direction=firestore.Query.DESCENDING)\
                .limit(10)\
                .get()

            has_recent_batch = False
            threshold = datetime.now() - timedelta(days=3)

            for batch_doc in batch_notifications:
                batch_data = batch_doc.to_dict()
                booking_ids = batch_data.get('booking_ids', [])
                created_at = batch_data.get('created_at')

                if booking_id in booking_ids and created_at >= threshold:
                    has_recent_batch = True
                    print(f"   ⏭️  Found in batch notification on {created_at}")
                    break

            has_recent = has_recent_single or has_recent_batch

        except Exception as e:
            print(f"   ⚠️  Error checking batch notifications: {e}")
            has_recent = has_recent_single

        if has_recent:
            print(f"   ⏭️  SKIPPED - Recent reminder sent within 3 days")
        else:
            bookings_to_notify.append(booking)
            print(f"   ✅ NEEDS REMINDER - No recent notifications found")

    print(f"\n🎯 FINAL RESULT:")
    print(f"   Bookings that need reminders: {len(bookings_to_notify)}")

    if len(bookings_to_notify) > 0:
        print(f"\n   📝 List of bookings to notify:")
        for booking in bookings_to_notify:
            print(f"      - {booking.get('client_name')} ({booking.get('event_date')})")

        if daily_count >= MAX_REMINDERS_PER_DAY:
            print(f"\n   ⚠️  BUT REMINDERS WON'T BE SENT - Daily limit reached")
        else:
            print(f"\n   ✅ These bookings SHOULD receive reminders when scheduler runs")
    else:
        print(f"\n   ℹ️  All overdue bookings already have recent reminders")

    print("\n" + "=" * 80)
    print("🏁 DIAGNOSTIC COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    diagnose_scheduler_issue()
