from twilio.rest import Client
from decouple import config
import logging
from datetime import datetime
from typing import Optional

# Configuración de Twilio
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_WHATSAPP_FROM = config('TWILIO_WHATSAPP_FROM', default='whatsapp:+14155238886')

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_phone_number(phone: str) -> str:
    """
    Formatear número de teléfono para WhatsApp
    Convierte +56912345678 a whatsapp:+56912345678
    """
    phone = phone.strip()
    if not phone.startswith('+'):
        if phone.startswith('9'):
            phone = '+56' + phone
        else:
            phone = '+56' + phone

    return f"whatsapp:{phone}"

async def send_whatsapp_confirmation(booking_data: dict) -> bool:
    """
    Enviar WhatsApp de confirmación cuando el evento pasa a 'Confirmado'

    Args:
        booking_data: Datos del agendamiento confirmado

    Returns:
        bool: True si se envió exitosamente, False en caso contrario
    """
    if not client:
        logger.error("Servicio de WhatsApp no configurado")
        return False

    try:
        service_name = 'Pizzeros en Acción' if booking_data['service_type'] == 'workshop' else 'Pizza Party'

        message_content = f"""🍕 *Pablo's Pizza*

¡Hola {booking_data['client_name']}!

✅ *Tu evento ha sido CONFIRMADO*

📋 *Detalles:*
🍕 Servicio: {service_name}
📅 Fecha: {booking_data['event_date'].strftime('%d/%m/%Y')}
⏰ Hora: {booking_data['event_time']}
👥 Participantes: {booking_data['participants']}
📍 Ubicación: {booking_data['location']}
💰 Precio estimado: ${booking_data.get('estimated_price', 0):,.0f} CLP

🔥 *¿Qué puedes esperar?*
✅ Llegamos puntualmente
✅ Todos los materiales incluidos
✅ Experiencia divertida y educativa
✅ Pizzas deliciosas hechas por ustedes

¿Tienes alguna pregunta? ¡Responde a este mensaje!

¡Nos vemos pronto para una experiencia increíble! 🎉"""

        # Formatear número de teléfono
        to_whatsapp = format_phone_number(booking_data['client_phone'])

        # Enviar mensaje
        message = client.messages.create(
            body=message_content,
            from_=TWILIO_WHATSAPP_FROM,
            to=to_whatsapp
        )

        logger.info(f"WhatsApp de confirmación enviado exitosamente a {booking_data['client_phone']}")
        logger.info(f"Message SID: {message.sid}")

        return True

    except Exception as e:
        logger.error(f"Error enviando WhatsApp de confirmación a {booking_data['client_phone']}: {str(e)}")
        return False

async def send_whatsapp_reminder(booking_data: dict) -> bool:
    """
    Enviar recordatorio por WhatsApp 24 horas antes del evento
    """
    if not client:
        return False

    try:
        service_name = 'Pizzeros en Acción' if booking_data['service_type'] == 'workshop' else 'Pizza Party'

        message_content = f"""🍕 *Pablo's Pizza - Recordatorio*

¡Hola {booking_data['client_name']}!

⏰ *Recordatorio: Tu evento es MAÑANA*

📋 *Detalles:*
🍕 Servicio: {service_name}
📅 Fecha: {booking_data['event_date'].strftime('%d/%m/%Y')}
⏰ Hora: {booking_data['event_time']}
📍 Ubicación: {booking_data['location']}

🔔 *Preparativos importantes:*
✅ Espacio limpio y despejado
✅ Mesa grande disponible
✅ Acceso a agua
✅ ¡Muchas ganas de divertirse! 🎉

¿Alguna duda de último minuto? ¡Escríbenos!

¡Nos vemos mañana! 🍕❤️"""

        to_whatsapp = format_phone_number(booking_data['client_phone'])

        message = client.messages.create(
            body=message_content,
            from_=TWILIO_WHATSAPP_FROM,
            to=to_whatsapp
        )

        logger.info(f"WhatsApp recordatorio enviado a {booking_data['client_phone']}")
        return True

    except Exception as e:
        logger.error(f"Error enviando WhatsApp recordatorio: {str(e)}")
        return False

async def send_welcome_whatsapp(client_phone: str, client_name: str) -> bool:
    """
    Enviar WhatsApp de bienvenida a nuevos clientes
    """
    if not client:
        return False

    try:
        message_content = f"""🍕 *¡Bienvenido a Pablo's Pizza!*

¡Hola {client_name}!

Gracias por confiar en nosotros para tu evento. Hemos recibido tu solicitud y pronto nos pondremos en contacto contigo.

🍕 *Nuestros servicios:*
• **Pizzeros en Acción**: Experiencia interactiva donde los participantes hacen sus propias pizzas
• **Pizza Party**: Deliciosas pizzas listas para disfrutar

📞 *¿Tienes preguntas?*
¡Responde a este mensaje y te ayudamos!

¡Gracias por elegirnos! 🎉"""

        to_whatsapp = format_phone_number(client_phone)

        message = client.messages.create(
            body=message_content,
            from_=TWILIO_WHATSAPP_FROM,
            to=to_whatsapp
        )

        logger.info(f"WhatsApp de bienvenida enviado a {client_phone}")
        return True

    except Exception as e:
        logger.error(f"Error enviando WhatsApp de bienvenida: {str(e)}")
        return False