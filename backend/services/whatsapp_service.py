"""
WhatsApp Service
Send WhatsApp notifications via Twilio using approved templates
"""
import os
import asyncio
import json
from twilio.rest import Client
from utils.formatters import (
    format_date_for_template,
    format_participants_info,
    format_cantidad_info,
    format_service_name
)
from services.calendar_service import generate_calendar_invite_with_url

# Twilio WhatsApp Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_FROM = os.getenv('TWILIO_WHATSAPP_FROM', 'whatsapp:+12017620171')

# Twilio WhatsApp Template SIDs
# NOTE: Templates created with English (en) language but Spanish content for faster approval
# Content language doesn't need to match template language setting
TEMPLATE_NEW_BOOKING_SID = os.getenv('TEMPLATE_NEW_BOOKING_SID', 'HXa6b7326d7297f04c9ade01e8d8afaefe')
TEMPLATE_BOOKING_CONFIRMED_SID = os.getenv('TEMPLATE_BOOKING_CONFIRMED_SID', 'HXab45cdc57ca599799b850dd3b889020c')
TEMPLATE_EVENT_OVERDUE_SINGLE_SID = os.getenv('TEMPLATE_EVENT_OVERDUE_SINGLE_SID', 'HXd00b109affda30cc4b0b2888b469014d')
TEMPLATE_EVENT_OVERDUE_MULTIPLE_SID = os.getenv('TEMPLATE_EVENT_OVERDUE_MULTIPLE_SID', 'HXd65d75d0e47eb7b489b112b2f18f3382')

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None


def prepare_new_booking_variables(booking_data: dict) -> dict:
    """
    Prepare variables for new booking WhatsApp template
    Template SID: HXa6b7326d7297f04c9ade01e8d8afaefe

    Twilio Content API variables use string indices matching the order in template:
    "1" - Fecha del evento ({{1}})
    "2" - Hora del evento ({{2}})
    "3" - Participantes ({{3}})
    "4" - Servicio ({{4}})
    "5" - Precio estimado ({{5}})
    "6" - Cliente ({{6}})
    "7" - Teléfono ({{7}})
    "8" - Link al admin panel ({{8}})

    Args:
        booking_data: Booking information dict

    Returns:
        dict: Template variables
    """
    # Format date
    event_date = booking_data.get('event_date', '')
    formatted_date = format_date_for_template(event_date)

    # Format time
    event_time = booking_data.get('event_time', 'No especificada')

    # Determine service name
    service_types = booking_data.get('service_type', '')
    service_name = format_service_name(service_types)

    # Format participants
    participants_info = format_participants_info(booking_data)

    # Format price
    estimated_price = booking_data.get('estimated_price', 0)
    formatted_price = f"${estimated_price:,.0f} CLP" if estimated_price > 0 else "Por definir"

    # Admin panel link
    admin_link = "https://pablospizza.web.app/admin/agendamientos"

    # Ensure no empty or null values (Twilio rejects empty variables)
    variables = {
        "1": formatted_date or "No especificada",
        "2": event_time or "No especificada",
        "3": participants_info or "No especificado",
        "4": service_name or "Pizza Party",
        "5": formatted_price or "Por definir",
        "6": booking_data.get('client_name') or "No especificado",
        "7": booking_data.get('client_phone') or "No especificado",
        "8": admin_link
    }

    # Log variables for debugging
    print(f"🔍 Template variables prepared: {variables}")

    return variables


def prepare_confirmed_booking_variables(booking_data: dict) -> dict:
    """
    Prepare variables for confirmed booking WhatsApp template
    Template SID: HXab45cdc57ca599799b850dd3b889020c

    Variables:
    {{1}} - Nombre del cliente
    {{2}} - Fecha del evento
    {{3}} - Hora del evento
    {{4}} - Nombre del servicio
    {{5}} - Cantidad (participantes/pizzas)
    {{6}} - Ubicación
    {{7}} - Total estimado
    {{8}} - Notas especiales
    {{9}} - Link de calendario

    Args:
        booking_data: Booking information dict

    Returns:
        dict: Template variables
    """
    # Client name
    client_name = booking_data.get('client_name', 'Cliente')

    # Format date
    event_date = booking_data.get('event_date', '')
    formatted_date = format_date_for_template(event_date)

    # Format time
    event_time = booking_data.get('event_time', 'No especificada')

    # Determine service name
    service_types = booking_data.get('service_type', '')
    service_name = format_service_name(service_types)

    # Format quantity based on service
    cantidad_info = format_cantidad_info(booking_data)

    # Location
    location = booking_data.get('location', 'Por confirmar')

    # Format price
    estimated_price = booking_data.get('estimated_price', 0)
    formatted_price = f"${estimated_price:,.0f} CLP" if estimated_price > 0 else "Por definir"

    # Special requests/notes
    special_requests = booking_data.get('special_requests', 'Ninguna')
    if not special_requests or special_requests.strip() == '':
        special_requests = 'Ninguna'

    # Generate calendar link
    _, calendar_url = generate_calendar_invite_with_url(booking_data)

    return {
        "1": client_name,
        "2": formatted_date,
        "3": event_time,
        "4": service_name,
        "5": cantidad_info,
        "6": location,
        "7": formatted_price,
        "8": special_requests,
        "9": calendar_url
    }


async def send_whatsapp_template(phone: str, template_type: str, booking_data: dict) -> bool:
    """
    Send WhatsApp using approved Twilio templates

    Args:
        phone: Destination phone number
        template_type: 'new_booking' or 'booking_confirmed'
        booking_data: Booking information

    Returns:
        bool: True if sent successfully
    """
    if not twilio_client:
        print("❌ Twilio client not configured")
        return False

    try:
        # Format phone number
        if not phone.startswith('whatsapp:'):
            if not phone.startswith('+'):
                phone = '+' + phone
            phone = f'whatsapp:{phone}'

        # Determine template and prepare variables
        if template_type == 'new_booking':
            content_sid = TEMPLATE_NEW_BOOKING_SID
            template_vars = prepare_new_booking_variables(booking_data)
        elif template_type == 'booking_confirmed':
            content_sid = TEMPLATE_BOOKING_CONFIRMED_SID
            template_vars = prepare_confirmed_booking_variables(booking_data)
        else:
            raise ValueError(f"Invalid template type: {template_type}")

        print(f"📱 Sending WhatsApp template '{template_type}' to {phone}")
        print(f"📋 Template SID: {content_sid}")
        print(f"📋 Template variables: {template_vars}")

        # Send using Twilio template
        # Twilio Content API expects variables as a JSON string
        # The format must match what's defined in the template
        variables_json = json.dumps(template_vars)
        print(f"📋 Variables JSON: {variables_json}")

        template_message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=phone,
            content_sid=content_sid,
            content_variables=variables_json
        )

        print(f"✅ WhatsApp template sent successfully, SID: {template_message.sid}")
        return True

    except Exception as e:
        print(f"❌ Template sending failed for {phone}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def send_whatsapp_notification(phone: str, message: str, notification_type: str) -> bool:
    """
    Send WhatsApp notification using Twilio

    Args:
        phone: Destination phone number
        message: Message text
        notification_type: Type of notification (for logging)

    Returns:
        bool: True if sent successfully
    """
    if not twilio_client:
        print("Twilio client not configured")
        return False

    try:
        if not phone.startswith('whatsapp:'):
            if not phone.startswith('+'):
                phone = '+' + phone
            phone = f'whatsapp:{phone}'

        message_instance = twilio_client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_FROM,
            to=phone
        )

        print(f"WhatsApp sent successfully to {phone}")
        return True

    except Exception as e:
        print(f"Error sending WhatsApp to {phone}: {str(e)}")
        return False


def prepare_single_overdue_reminder_variables(admin_name: str, booking_data: dict, days_overdue: int) -> dict:
    """
    Prepare variables for single event overdue reminder WhatsApp template
    Template SID: HXd00b109affda30cc4b0b2888b469014d

    Template structure:
    Hola {{1}}! 👋
    Recordatorio: El siguiente evento necesita ser completado:
    🎉 Evento: {{2}}
    📆 Fecha: {{3}} (hace {{4}} días)
    ⚠️ Estado: Pendiente de completar
    Por favor completa el evento:
    🔗 {{5}}
    Esto ayuda a mantener registros precisos y control de costos. 💰📊
    ¡Gracias!

    Variables:
    {{1}} - Admin name (Juan Pablo)
    {{2}} - Event title (client name + service)
    {{3}} - Event date (formatted)
    {{4}} - Days overdue
    {{5}} - Direct booking link

    Args:
        admin_name: Name of the admin (Juan Pablo)
        booking_data: Booking information dict
        days_overdue: Number of days since event date

    Returns:
        dict: Template variables
    """
    from datetime import datetime

    # Format date
    event_date = booking_data.get('event_date', '')
    formatted_date = format_date_for_template(event_date)

    # Create event title
    client_name = booking_data.get('client_name', 'Cliente')
    service_types = booking_data.get('service_type', '')
    service_name = format_service_name(service_types)
    event_title = f"{client_name} - {service_name}"

    # Direct link to booking
    booking_id = booking_data.get('id', '')
    booking_link = f"https://pablospizza.web.app/admin/agendamientos"

    variables = {
        "1": admin_name,
        "2": event_title,
        "3": formatted_date,
        "4": str(days_overdue),
        "5": booking_link
    }

    print(f"🔍 Single overdue reminder variables: {variables}")
    return variables


def prepare_multiple_overdue_reminder_variables(admin_name: str, bookings_list: list, booking_link: str) -> dict:
    """
    Prepare variables for multiple events overdue reminder WhatsApp template
    Template SID: HXd65d75d0e47eb7b489b112b2f18f3382

    Template structure:
    Hola {{1}}! 👋
    Tienes {{2}} eventos pendientes de completar:
    {{3}}
    Por favor revisa y completa los eventos:
    🔗 {{4}}
    Esto ayuda a mantener registros precisos y control de costos. 💰📊
    ¡Gracias!

    Variables:
    {{1}} - Admin name (Juan Pablo)
    {{2}} - Number of pending events
    {{3}} - List of events (formatted as bullet points)
    {{4}} - Booking management link

    Args:
        admin_name: Name of the admin (Juan Pablo)
        bookings_list: List of overdue bookings
        booking_link: Link to bookings management page

    Returns:
        dict: Template variables
    """
    # Count events
    event_count = len(bookings_list)

    # Format event list
    event_records = []
    for idx, booking in enumerate(bookings_list[:5], 1):  # Limit to first 5 events
        client_name = booking.get('client_name', 'Cliente')
        event_date = booking.get('event_date', '')
        formatted_date = format_date_for_template(event_date)
        service_name = format_service_name(booking.get('service_type', ''))

        event_records.append(f"{idx}. {client_name} - {service_name} ({formatted_date})")

    # Add "..." if there are more events
    if event_count > 5:
        event_records.append(f"... y {event_count - 5} más")

    record_list = "\n".join(event_records)

    variables = {
        "1": admin_name,
        "2": str(event_count),
        "3": record_list,
        "4": booking_link
    }

    print(f"🔍 Multiple overdue reminder variables: {variables}")
    return variables


async def send_overdue_reminder(phone: str, admin_name: str, bookings: list, is_single: bool = True) -> bool:
    """
    Send overdue event reminder using appropriate template

    Args:
        phone: Admin phone number
        admin_name: Name of the admin (Juan Pablo)
        bookings: List of overdue booking dictionaries (or single booking as list)
        is_single: True for single event, False for multiple events

    Returns:
        bool: True if sent successfully
    """
    if not twilio_client:
        print("❌ Twilio client not configured")
        return False

    try:
        # Format phone number
        if not phone.startswith('whatsapp:'):
            if not phone.startswith('+'):
                phone = '+' + phone
            phone = f'whatsapp:{phone}'

        if is_single and len(bookings) == 1:
            # Single event reminder
            from datetime import datetime, timedelta

            booking = bookings[0]
            event_date_str = booking.get('event_date', '')

            # Calculate days overdue
            try:
                if 'T' in event_date_str:
                    event_date = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
                else:
                    event_date = datetime.strptime(event_date_str, '%Y-%m-%d')

                days_overdue = (datetime.now() - event_date).days
            except:
                days_overdue = 3  # Default fallback

            content_sid = TEMPLATE_EVENT_OVERDUE_SINGLE_SID
            template_vars = prepare_single_overdue_reminder_variables(admin_name, booking, days_overdue)

        else:
            # Multiple events reminder
            content_sid = TEMPLATE_EVENT_OVERDUE_MULTIPLE_SID
            booking_link = "https://pablospizza.web.app/admin/agendamientos"
            template_vars = prepare_multiple_overdue_reminder_variables(admin_name, bookings, booking_link)

        print(f"📱 Sending overdue reminder WhatsApp to {phone}")
        print(f"📋 Template SID: {content_sid}")
        print(f"📋 Template variables: {template_vars}")

        # Send using Twilio template
        variables_json = json.dumps(template_vars)

        template_message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=phone,
            content_sid=content_sid,
            content_variables=variables_json
        )

        print(f"✅ Overdue reminder sent successfully, SID: {template_message.sid}")
        return True

    except Exception as e:
        print(f"❌ Overdue reminder sending failed for {phone}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
