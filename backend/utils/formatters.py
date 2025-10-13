"""
Data Formatting Utilities
Functions for formatting data for templates, WhatsApp messages, and emails
"""
from datetime import datetime


def format_date_for_template(event_date: str) -> str:
    """
    Format date for WhatsApp templates and emails (DD/MM/YYYY)

    Args:
        event_date: Date string in ISO format or YYYY-MM-DD

    Returns:
        str: Formatted date as DD/MM/YYYY or original if parsing fails
    """
    if not event_date:
        return 'No especificada'

    try:
        if 'T' in event_date:
            date_obj = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
        else:
            date_obj = datetime.strptime(event_date, '%Y-%m-%d')
        return date_obj.strftime('%d/%m/%Y')
    except Exception:
        return event_date


def format_participants_info(booking_data: dict) -> str:
    """
    Format participants information for WhatsApp templates

    Standardized variables:
    - pizzeros_participants: Number of children in Pizzeros en Acción
    - party_participants: Number of guests for Pizza Party
    - pizza_quantity: Number of pizzas for Pizza Party

    Args:
        booking_data: Booking dictionary with participant information

    Returns:
        str: Formatted participant information
    """
    pizzeros = booking_data.get('pizzeros_participants', 0)
    party_guests = booking_data.get('party_participants', 0)
    pizzas = booking_data.get('pizza_quantity', 0)

    # Both services
    if pizzeros > 0 and pizzas > 0:
        return f"Pizzeros: {pizzeros} niños, Pizza Party: {pizzas} pizzas"

    # Only Pizzeros
    elif pizzeros > 0:
        return f"{pizzeros} niños (Pizzeros en Acción)"

    # Only Pizza Party
    elif pizzas > 0:
        return f"{pizzas} pizzas (Pizza Party)"

    # Fallback: use general participants
    else:
        participants = booking_data.get('participants', 0)
        return f"{participants} participantes" if participants > 0 else "No especificado"


def format_cantidad_info(booking_data: dict) -> str:
    """
    Format quantity for booking confirmation template

    Standardized variables:
    - pizzeros_participants: Number of children
    - pizza_quantity: Number of pizzas

    Args:
        booking_data: Booking dictionary

    Returns:
        str: Formatted quantity information
    """
    service_types = booking_data.get('service_type', '')
    services = [s.strip() for s in service_types.split(',') if s.strip()]

    pizzeros = booking_data.get('pizzeros_participants', 0)
    pizzas = booking_data.get('pizza_quantity', 0)

    # Combo: show both
    if len(services) > 1:
        return f"{pizzeros} niños + {pizzas} pizzas"

    # Only Pizzeros
    elif 'workshop' in services or 'pizzeros' in services:
        return f"{pizzeros} niños"

    # Only Pizza Party
    else:
        return f"{pizzas} pizzas"


def format_service_name(service_types: str) -> str:
    """
    Get formatted service name from service type string

    Args:
        service_types: Comma-separated service types

    Returns:
        str: Formatted service name
    """
    services = [s.strip() for s in service_types.split(',') if s.strip()]

    if len(services) > 1:
        return 'Pizza Party + Pizzeros en Acción'
    elif 'workshop' in services or 'pizzeros' in services:
        return 'Pizzeros en Acción'
    else:
        return 'Pizza Party'


def format_price(price: float or int) -> str:
    """
    Format price for display

    Args:
        price: Price value

    Returns:
        str: Formatted price with CLP currency
    """
    if price and price > 0:
        return f"${price:,.0f} CLP"
    return "Por definir"


def format_time(time_str: str) -> str:
    """
    Format time string for display

    Args:
        time_str: Time string

    Returns:
        str: Formatted time or 'No especificada'
    """
    return time_str if time_str else "No especificada"
