"""Script to complete all pending events from 2025"""
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Add current directory to path
CURRENT_DIR = Path(__file__).parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Import database
from database import get_db

def complete_2025_events():
    """Complete all pending events from 2025"""
    try:
        db = get_db()

        # Get all bookings
        bookings_ref = db.collection("bookings")
        all_bookings = bookings_ref.stream()

        updated_count = 0
        skipped_count = 0

        for booking_doc in all_bookings:
            booking_data = booking_doc.to_dict()
            booking_id = booking_doc.id

            # Check if event is from 2025
            event_date = booking_data.get('event_date', '')
            status = booking_data.get('status', '')

            # Check if date is from 2025
            if event_date and '2025' in str(event_date):
                # Update if status is pending or confirmed (not already completed/cancelled)
                if status in ['pending', 'confirmed']:
                    print(f"Updating booking {booking_id}: {booking_data.get('client_name')} - {event_date} (status: {status} -> completed)")

                    # Update status to completed
                    bookings_ref.document(booking_id).update({
                        'status': 'completed',
                        'updated_at': datetime.now()
                    })

                    updated_count += 1
                else:
                    print(f"Skipping {booking_id} - already {status}")
                    skipped_count += 1

        print(f"\nProceso completado!")
        print(f"   - Eventos actualizados: {updated_count}")
        print(f"   - Eventos omitidos (ya completados/cancelados): {skipped_count}")

        return updated_count

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    print("Iniciando actualizacion de eventos del 2025...")
    print("=" * 60)
    complete_2025_events()
