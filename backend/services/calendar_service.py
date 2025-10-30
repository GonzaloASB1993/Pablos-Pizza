"""
Calendar Service
Generate ICS calendar invitations and upload to Firebase Storage
"""
from datetime import datetime, timedelta
import uuid
from database import get_storage_bucket


def generate_calendar_invite(booking_data: dict) -> str:
    """
    Generate ICS calendar invitation content

    Args:
        booking_data: Booking information dict

    Returns:
        str: ICS calendar file content or empty string if error
    """
    try:
        # Parse event date and time
        event_date_str = booking_data.get('event_date', '')
        event_time_str = booking_data.get('event_time', '12:00')

        # Create datetime object
        if 'T' in event_date_str:
            # If it's ISO format
            event_datetime = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
        else:
            # If it's date only, combine with time
            event_date = datetime.strptime(event_date_str.split('T')[0], '%Y-%m-%d').date()
            event_time = datetime.strptime(event_time_str, '%H:%M').time()
            event_datetime = datetime.combine(event_date, event_time)

        # Calculate end time (add duration)
        duration_hours = booking_data.get('duration_hours', 4)
        end_datetime = event_datetime + timedelta(hours=duration_hours)

        # Format for ICS
        start_time = event_datetime.strftime('%Y%m%dT%H%M%S')
        end_time = end_datetime.strftime('%Y%m%dT%H%M%S')

        # Determine service name
        service_types = booking_data.get('service_type', '')
        services = [s.strip() for s in service_types.split(',') if s.strip()]

        if len(services) > 1:
            service_name = 'Pizza Party + Pizzeros en Acción'
        elif 'workshop' in services or 'pizzeros' in services:
            service_name = 'Pizzeros en Acción'
        else:
            service_name = 'Pizza Party'

        # Generate unique UID
        event_uid = str(uuid.uuid4())

        # Create ICS content
        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Pablo's Pizza//Event Calendar//ES
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:{event_uid}
DTSTART:{start_time}
DTEND:{end_time}
SUMMARY:🍕 {service_name} - Pablo's Pizza
DESCRIPTION:¡Tu evento de Pablo's Pizza está confirmado!\\n\\nDetalles:\\n- Servicio: {service_name}\\n- Participantes: {booking_data.get('participants', 'N/A')}\\n- Precio: ${booking_data.get('estimated_price', 0):,.0f} CLP\\n\\n¡Nos vemos pronto para una experiencia increíble!\\n\\nContacto: +56 9 8942 4566
LOCATION:{booking_data.get('location', 'Por confirmar')}
STATUS:CONFIRMED
SEQUENCE:0
ORGANIZER;CN=Pablo's Pizza:mailto:pablospizza.cl@gmail.com
ATTENDEE;CN={booking_data.get('client_name', 'Cliente')}:mailto:{booking_data.get('client_email', '')}
BEGIN:VALARM
TRIGGER:-PT24H
ACTION:DISPLAY
DESCRIPTION:Recordatorio: Tu evento de Pablo's Pizza es mañana
END:VALARM
END:VEVENT
END:VCALENDAR"""

        return ics_content

    except Exception as e:
        print(f"Error generating calendar invite: {e}")
        return ""


def generate_calendar_invite_with_url(booking_data: dict) -> tuple:
    """
    Generate ICS calendar invitation and upload to Firebase Storage

    Args:
        booking_data: Booking information dict

    Returns:
        tuple: (ics_content: str, public_url: str)
    """
    try:
        # Generate ICS content using existing function
        ics_content = generate_calendar_invite(booking_data)

        if not ics_content:
            return "", "https://pablospizza.web.app/agendar"

        # Upload to Firebase Storage
        try:
            bucket = get_storage_bucket()
            if not bucket:
                raise Exception("Storage bucket not initialized")

            booking_id = booking_data.get('id', str(uuid.uuid4()))
            blob_path = f"calendar_invites/{booking_id}.ics"
            blob = bucket.blob(blob_path)

            # Upload ICS file
            blob.upload_from_string(
                ics_content,
                content_type='text/calendar'
            )

            # Make publicly accessible
            blob.make_public()

            # Generate URL pointing to backend API endpoint
            short_url = f"https://us-central1-pablospizza-d84bf.cloudfunctions.net/main/cal/{booking_id}"

            print(f"📅 Calendar invite uploaded with short URL: {short_url}")
            return ics_content, short_url

        except Exception as storage_error:
            print(f"Error uploading calendar to storage: {storage_error}")
            # Fallback: return website URL
            booking_id = booking_data.get('id', '')
            fallback_url = f"https://pablospizza.web.app/agendar" if not booking_id else f"https://us-central1-pablospizza-d84bf.cloudfunctions.net/main/cal/{booking_id}"
            return ics_content, fallback_url

    except Exception as e:
        print(f"Error generating calendar invite with URL: {e}")
        return "", "https://pablospizza.web.app/agendar"
