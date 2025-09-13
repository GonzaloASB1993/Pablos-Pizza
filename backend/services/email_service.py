from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from firebase_admin import firestore
from decouple import config
import os
from pathlib import Path
import logging
from datetime import datetime
from typing import Optional

# Buscar archivo .env en el directorio actual
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

# Configuración de email
EMAIL_CONFIG = ConnectionConfig(
    MAIL_USERNAME=config('EMAIL_USERNAME', default='gonzalo.asb@gmail.com'),
    MAIL_PASSWORD=config('EMAIL_PASSWORD', default='izct tpac jcbw mlhb'),
    MAIL_FROM=config('EMAIL_FROM', default='noreply@pablospizza.cl'),
    MAIL_PORT=config('EMAIL_PORT', default=587, cast=int),
    MAIL_SERVER=config('EMAIL_SERVER', default='smtp.gmail.com'),
    MAIL_STARTTLS=config('EMAIL_STARTTLS', default=True, cast=bool),
    MAIL_SSL_TLS=config('EMAIL_SSL_TLS', default=False, cast=bool),
    USE_CREDENTIALS=config('EMAIL_USE_CREDENTIALS', default=True, cast=bool),
    VALIDATE_CERTS=config('EMAIL_VALIDATE_CERTS', default=True, cast=bool)
)

print(f"📧 Email configurado: {EMAIL_CONFIG.MAIL_USERNAME} -> {EMAIL_CONFIG.MAIL_FROM}")

fastmail = FastMail(EMAIL_CONFIG) if EMAIL_CONFIG.MAIL_USERNAME else None
db = firestore.client()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_confirmation_email(booking_data: dict) -> bool:
    """
    Enviar email de confirmación cuando el evento pasa a 'Confirmado'

    Args:
        booking_data: Datos del agendamiento confirmado

    Returns:
        bool: True si se envió exitosamente, False en caso contrario
    """
    if not fastmail:
        logger.error("Servicio de email no configurado")
        return False

    try:
        service_name = 'Pizzeros en Acción' if booking_data['service_type'] == 'workshop' else 'Pizza Party'

        # Crear HTML del email
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Evento Confirmado - Pablo's Pizza</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #ff6b35; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .event-details {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ background-color: #f1f1f1; padding: 15px; text-align: center; color: #666; }}
                .logo {{ font-size: 24px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">🍕 Pablo's Pizza</div>
                <h1>¡Tu evento ha sido confirmado!</h1>
            </div>

            <div class="content">
                <h2>Hola {booking_data['client_name']},</h2>

                <p>¡Excelente noticia! Tu evento ha sido <strong>confirmado</strong> y estamos emocionados de ser parte de tu celebración.</p>

                <div class="event-details">
                    <h3>📋 Detalles de tu evento:</h3>
                    <p><strong>🍕 Servicio:</strong> {service_name}</p>
                    <p><strong>📅 Fecha:</strong> {booking_data['event_date'].strftime('%d/%m/%Y')}</p>
                    <p><strong>⏰ Hora:</strong> {booking_data['event_time']}</p>
                    <p><strong>👥 Participantes:</strong> {booking_data['participants']}</p>
                    <p><strong>📍 Ubicación:</strong> {booking_data['location']}</p>
                    <p><strong>💰 Precio estimado:</strong> ${booking_data.get('estimated_price', 0):,.0f} CLP</p>
                </div>

                <h3>🔥 ¿Qué puedes esperar?</h3>
                <ul>
                    <li>✅ Nuestro equipo llegará puntualmente a la hora acordada</li>
                    <li>✅ Todos los ingredientes y materiales necesarios incluidos</li>
                    <li>✅ Una experiencia divertida y educativa para todos</li>
                    <li>✅ Pizzas deliciosas hechas por los propios participantes</li>
                </ul>

                <h3>📞 Información de contacto:</h3>
                <p>Si tienes alguna pregunta o necesitas hacer cambios:</p>
                <ul>
                    <li><strong>WhatsApp:</strong> +56 9 8942 4566</li>
                    <li><strong>Email:</strong> contacto@pablospizza.com</li>
                </ul>

                <p><strong>¡Nos vemos pronto para una experiencia increíble! 🎉</strong></p>
            </div>

            <div class="footer">
                <p>Pablo's Pizza - Haciendo momentos deliciosos desde siempre 🍕❤️</p>
                <p>Este es un email automático, por favor no responder directamente.</p>
            </div>
        </body>
        </html>
        """

        # Crear mensaje
        message = MessageSchema(
            subject="✅ ¡Tu evento con Pablo's Pizza ha sido confirmado!",
            recipients=[booking_data['client_email']],
            body=html_content,
            subtype="html"
        )

        # Enviar email
        await fastmail.send_message(message)

        # Guardar registro en base de datos
        email_data = {
            "recipient_email": booking_data['client_email'],
            "subject": message.subject,
            "booking_id": booking_data['id'],
            "email_type": "confirmation",
            "sent_at": datetime.now(),
            "status": "sent"
        }

        db.collection("emails").add(email_data)

        logger.info(f"Email de confirmación enviado exitosamente a {booking_data['client_email']}")
        return True

    except Exception as e:
        logger.error(f"Error enviando email de confirmación a {booking_data['client_email']}: {str(e)}")

        # Guardar registro de error
        error_email = {
            "recipient_email": booking_data['client_email'],
            "subject": "Confirmación de evento",
            "booking_id": booking_data['id'],
            "email_type": "confirmation",
            "sent_at": datetime.now(),
            "status": "failed",
            "error": str(e)
        }

        try:
            db.collection("emails").add(error_email)
        except:
            pass

        return False

async def send_welcome_email(client_email: str, client_name: str) -> bool:
    """
    Enviar email de bienvenida a nuevos clientes
    """
    if not fastmail:
        return False

    try:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>¡Bienvenido a Pablo's Pizza!</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #ff6b35; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .services {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ background-color: #f1f1f1; padding: 15px; text-align: center; color: #666; }}
                .logo {{ font-size: 24px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">🍕 Pablo's Pizza</div>
                <h1>¡Bienvenido a la familia!</h1>
            </div>

            <div class="content">
                <h2>¡Hola {client_name}!</h2>

                <p>¡Gracias por confiar en Pablo's Pizza para tu evento! Estamos emocionados de ser parte de tu celebración.</p>

                <div class="services">
                    <h3>🍕 Nuestros servicios:</h3>
                    <p><strong>Pizzeros en Acción:</strong> Experiencia interactiva donde los participantes hacen sus propias pizzas</p>
                    <p><strong>Pizza Party:</strong> Deliciosas pizzas listas para disfrutar en tu evento</p>
                </div>

                <p>Te mantendremos informado sobre el estado de tu agendamiento y te contactaremos pronto para confirmar todos los detalles.</p>

                <p><strong>¡Gracias por elegirnos! 🎉</strong></p>
            </div>

            <div class="footer">
                <p>Pablo's Pizza - Haciendo momentos deliciosos desde siempre 🍕❤️</p>
            </div>
        </body>
        </html>
        """

        message = MessageSchema(
            subject="🍕 ¡Bienvenido a Pablo's Pizza!",
            recipients=[client_email],
            body=html_content,
            subtype="html"
        )

        await fastmail.send_message(message)
        logger.info(f"Email de bienvenida enviado a {client_email}")
        return True

    except Exception as e:
        logger.error(f"Error enviando email de bienvenida a {client_email}: {str(e)}")
        return False