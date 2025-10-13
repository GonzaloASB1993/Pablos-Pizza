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
