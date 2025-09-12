from twilio.rest import Client
from firebase_admin import firestore
from decouple import config
import logging
from datetime import datetime
from models.schemas import NotificationCreate

# Configuración de Twilio para WhatsApp
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_WHATSAPP_NUMBER = config('TWILIO_WHATSAPP_NUMBER', default='whatsapp:+14155238886')

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID else None
db = firestore.client()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_whatsapp_notification(phone: str, message: str, notification_type: str) -> bool:
    """
    Enviar notificación por WhatsApp usando Twilio
    
    Args:
        phone: Número de teléfono con código de país
        message: Mensaje a enviar
        notification_type: Tipo de notificación (booking_confirmation, reminder, admin_alert)
    
    Returns:
        bool: True si se envió exitosamente, False en caso contrario
    """
    if not client:
        logger.error("Cliente de Twilio no configurado")
        return False
    
    try:
        # Asegurar formato correcto del número
        if not phone.startswith('whatsapp:'):
            if not phone.startswith('+'):
                phone = '+' + phone
            phone = f'whatsapp:{phone}'
        
        # Enviar mensaje
        message_instance = client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=phone
        )
        
        # Guardar registro en base de datos
        notification_data = {
            "id": message_instance.sid,
            "recipient_phone": phone,
            "message": message,
            "notification_type": notification_type,
            "sent_at": datetime.now(),
            "status": "sent"
        }
        
        db.collection("notifications").document(message_instance.sid).set(notification_data)
        
        logger.info(f"WhatsApp enviado exitosamente a {phone}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando WhatsApp a {phone}: {str(e)}")
        
        # Guardar registro de error
        error_notification = {
            "id": f"error_{datetime.now().timestamp()}",
            "recipient_phone": phone,
            "message": message,
            "notification_type": notification_type,
            "sent_at": datetime.now(),
            "status": "failed",
            "error": str(e)
        }
        
        try:
            db.collection("notifications").add(error_notification)
        except:
            pass
            
        return False

async def send_booking_reminder(booking_id: str) -> bool:
    """
    Enviar recordatorio de evento (24 horas antes)
    """
    try:
        booking_doc = db.collection("bookings").document(booking_id).get()
        if not booking_doc.exists:
            return False
        
        booking_data = booking_doc.to_dict()
        
        message = f"""
⏰ RECORDATORIO - Pablo's Pizza

Hola {booking_data['client_name']},

Te recordamos tu evento programado para MAÑANA:

📅 Fecha: {booking_data['event_date'].strftime('%d/%m/%Y')}
⏰ Hora: {booking_data['event_time']}
👥 Participantes: {booking_data['participants']}
📍 Ubicación: {booking_data['location']}

¡Estamos emocionados por hacer de tu evento algo especial! 🍕✨

Si tienes alguna pregunta, ¡contáctanos!
        """
        
        return await send_whatsapp_notification(
            booking_data['client_phone'],
            message,
            "reminder"
        )
        
    except Exception as e:
        logger.error(f"Error enviando recordatorio para booking {booking_id}: {str(e)}")
        return False

async def send_review_request(event_id: str) -> bool:
    """
    Solicitar review después del evento
    """
    try:
        event_doc = db.collection("events").document(event_id).get()
        if not event_doc.exists:
            return False
        
        event_data = event_doc.to_dict()
        
        # Obtener datos del booking
        booking_doc = db.collection("bookings").document(event_data['booking_id']).get()
        if not booking_doc.exists:
            return False
        
        booking_data = booking_doc.to_dict()
        
        message = f"""
🌟 ¡Gracias por elegir Pablo's Pizza!

Hola {booking_data['client_name']},

¡Esperamos que hayas disfrutado tu experiencia con nosotros!

¿Te gustaría compartir tu opinión? Tu feedback es muy importante para nosotros.

👉 Deja tu reseña aquí: https://pablos-pizza.com/reviews/{event_id}

¡Hasta la próxima! 🍕❤️
        """
        
        return await send_whatsapp_notification(
            booking_data['client_phone'],
            message,
            "review_request"
        )
        
    except Exception as e:
        logger.error(f"Error enviando solicitud de review para evento {event_id}: {str(e)}")
        return False

async def send_admin_daily_summary():
    """
    Enviar resumen diario al administrador
    """
    try:
        from datetime import date, timedelta
        today = date.today()
        
        # Obtener estadísticas del día
        bookings_today = db.collection("bookings").where(
            "created_at", ">=", today
        ).where(
            "created_at", "<", today + timedelta(days=1)
        ).stream()
        
        events_today = db.collection("events").where(
            "start_time", ">=", today
        ).where(
            "start_time", "<", today + timedelta(days=1)
        ).stream()
        
        booking_count = len(list(bookings_today))
        event_count = len(list(events_today))
        
        message = f"""
📊 RESUMEN DIARIO - Pablo's Pizza
{today.strftime('%d/%m/%Y')}

📅 Nuevos agendamientos: {booking_count}
🎉 Eventos realizados: {event_count}

¡Ten un excelente día! 🍕
        """
        
        admin_phone = config('ADMIN_WHATSAPP_NUMBER', default='+1234567890')
        return await send_whatsapp_notification(
            admin_phone,
            message,
            "daily_summary"
        )
        
    except Exception as e:
        logger.error(f"Error enviando resumen diario: {str(e)}")
        return False

async def send_inventory_alert(item_name: str, current_stock: int, min_stock: int):
    """
    Enviar alerta de inventario bajo
    """
    try:
        message = f"""
⚠️ ALERTA DE INVENTARIO

El siguiente producto está por agotarse:

📦 Producto: {item_name}
📊 Stock actual: {current_stock}
📊 Stock mínimo: {min_stock}

¡Es hora de hacer pedido! 📞
        """
        
        admin_phone = config('ADMIN_WHATSAPP_NUMBER', default='+1234567890')
        return await send_whatsapp_notification(
            admin_phone,
            message,
            "inventory_alert"
        )
        
    except Exception as e:
        logger.error(f"Error enviando alerta de inventario: {str(e)}")
        return False