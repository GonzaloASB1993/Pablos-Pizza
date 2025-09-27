from firebase_functions import https_fn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Import after loading env variables
import firebase_admin
from firebase_admin import firestore, storage
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# WhatsApp service imports
import asyncio
from twilio.rest import Client

# Initialize Flask app
app = Flask(__name__)

# Twilio WhatsApp Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_FROM = os.getenv('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None

async def send_whatsapp_notification(phone: str, message: str, notification_type: str) -> bool:
    """Send WhatsApp notification using Twilio"""
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

async def send_whatsapp_with_template_fallback(phone: str, message: str, notification_type: str, booking_data: dict) -> bool:
    """
    Send WhatsApp notification using template (always uses template now)
    """
    if not twilio_client:
        print("Twilio client not configured")
        return False

    # Format phone number
    if not phone.startswith('whatsapp:'):
        if not phone.startswith('+'):
            phone = '+' + phone
        phone = f'whatsapp:{phone}'

    try:
        # Prepare template variables - Handle multiple services properly
        service_types = booking_data.get('service_type', '')
        services = [s.strip() for s in service_types.split(',') if s.strip()]

        if len(services) > 1:
            service_name = 'Pizza Party + Pizzeros en Acción'
        elif 'workshop' in services or 'pizzeros' in services:
            service_name = 'Pizzeros en Acción'
        else:
            service_name = 'Pizza Party'

        # Format date properly
        event_date = booking_data.get('event_date', '')
        formatted_date = 'No especificada'
        if event_date:
            try:
                from datetime import datetime
                if 'T' in event_date:
                    date_obj = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                    formatted_date = date_obj.strftime('%d/%m/%Y')
                else:
                    date_obj = datetime.strptime(event_date, '%Y-%m-%d')
                    formatted_date = date_obj.strftime('%d/%m/%Y')
            except:
                formatted_date = event_date

        # Format time properly
        event_time = booking_data.get('event_time', '')
        formatted_time = 'No especificada'
        if event_time:
            formatted_time = event_time

        # Format participants info based on new pizza structure
        participants_info = "No especificado"
        if booking_data.get('pizzeros_participants') and booking_data.get('party_participants'):
            participants_info = f"Pizzeros: {booking_data['pizzeros_participants']} niños, Pizza Party: {booking_data.get('pizza_quantity', booking_data['party_participants'])} pizzas"
        elif booking_data.get('pizzeros_participants'):
            participants_info = f"{booking_data['pizzeros_participants']} niños (Pizzeros en Acción)"
        elif booking_data.get('party_participants'):
            pizza_qty = booking_data.get('pizza_quantity', booking_data['party_participants'])
            participants_info = f"{pizza_qty} pizzas (Pizza Party)"
        elif booking_data.get('participants'):
            participants_info = f"{booking_data['participants']} participantes"

        # Format price properly
        estimated_price = booking_data.get('estimated_price', 0)
        formatted_price = 'Por definir'
        if estimated_price and estimated_price > 0:
            try:
                formatted_price = f"${estimated_price:,.0f} CLP"
            except:
                formatted_price = f"${estimated_price} CLP"

        # Prepare template variables as JSON string (Twilio requirement)
        template_vars = {
            "1": str(formatted_date),
            "2": str(formatted_time),
            "3": str(participants_info),
            "4": str(service_name),
            "5": str(formatted_price),
            "6": str(booking_data.get('client_name', 'No especificado')),
            "7": str(booking_data.get('client_phone', 'No especificado'))
        }

        print(f"📱 Sending WhatsApp template to {phone}")
        print(f"📋 Template variables: {template_vars}")

        # Use template with properly formatted variables as JSON string
        import json
        template_message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=phone,
            content_sid='HXa33f59e4520c860c5024643fcb7139f3',
            content_variables=json.dumps(template_vars)
        )

        print(f"✅ WhatsApp template sent successfully to {phone}, SID: {template_message.sid}")
        return True

    except Exception as template_error:
        print(f"Template sending failed for {phone}: {str(template_error)}")
        return False

def send_admin_email_notification(booking_data: dict) -> bool:
    """Send email notification to admin about new booking"""
    try:
        # Handle multiple services properly
        service_types = booking_data.get('service_type', '')
        services = [s.strip() for s in service_types.split(',') if s.strip()]

        if len(services) > 1:
            service_name = 'Pizza Party + Pizzeros en Acción'
        elif 'workshop' in services or 'pizzeros' in services:
            service_name = 'Pizzeros en Acción'
        else:
            service_name = 'Pizza Party'

        # Email configuration
        smtp_server = os.getenv('EMAIL_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('EMAIL_PORT', 587))
        email_username = os.getenv('EMAIL_USERNAME')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_from = os.getenv('EMAIL_FROM')

        if not all([email_username, email_password, email_from]):
            print("Email configuration not complete")
            return False

        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_from  # Send to yourself
        msg['Subject'] = f"🍕 NUEVO AGENDAMIENTO - {booking_data.get('client_name', 'Cliente')}"

        # HTML content
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #FFC107; text-align: center;">🍕 Pablo's Pizza</h2>
            <h3 style="color: #000;">¡NUEVO AGENDAMIENTO!</h3>

            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h4>👤 Información del Cliente:</h4>
                <p><strong>Nombre:</strong> {booking_data.get('client_name', 'No especificado')}</p>
                <p><strong>Teléfono:</strong> {booking_data.get('client_phone', 'No especificado')}</p>
                <p><strong>Email:</strong> {booking_data.get('client_email', 'No especificado')}</p>

                <h4>🍕 Detalles del Evento:</h4>
                <p><strong>Servicio:</strong> {service_name}</p>
                <p><strong>Fecha:</strong> {booking_data.get('event_date', 'No especificada')}</p>
                <p><strong>Hora:</strong> {booking_data.get('event_time', 'No especificada')}</p>
                <p><strong>Participantes:</strong> {booking_data.get('participants', 'No especificado')}</p>
                <p><strong>Ubicación:</strong> {booking_data.get('location', 'No especificada')}</p>
                <p><strong>Precio estimado:</strong> ${booking_data.get('estimated_price', 0):,.0f} CLP</p>

                <h4>📝 Solicitudes especiales:</h4>
                <p>{booking_data.get('special_requests', 'Ninguna')}</p>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://pablospizza.web.app/admin/agendamientos"
                   style="background-color: #FFC107; color: black; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                   Ver en Admin Panel
                </a>
            </div>

            <p style="color: #666; font-size: 12px; text-align: center;">
                ID de reserva: {booking_data.get('id', 'N/A')}<br>
                Favor confirmar el evento en la plataforma.
            </p>
        </div>
        """

        msg.attach(MIMEText(html_content, 'html'))

        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_username, email_password)
        server.send_message(msg)
        server.quit()

        print(f"Admin email notification sent successfully")
        return True

    except Exception as e:
        print(f"Error sending admin email notification: {e}")
        return False

def generate_calendar_invite(booking_data: dict) -> str:
    """Generate ICS calendar invitation content"""
    try:
        from datetime import datetime, timedelta
        import uuid

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

        service_name = 'Pizzeros en Acción' if booking_data.get('service_type') == 'workshop' else 'Pizza Party'

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

# CORS configuration - allow both Firebase hosting domains
allowed_origins = [
    'https://pablospizza.web.app',
    'https://pablospizza.firebaseapp.com',
    'https://pablospizza.cl',     # Custom domain
    'http://localhost:5173',      # For development
    'http://localhost:3000',      # Alternative dev port
    'http://localhost:3001',
    'http://localhost:3002',
    'http://localhost:3003',
    'http://localhost:3004'
]

# Add any additional origins from environment
cors_origins = os.getenv('CORS_ORIGINS', '')
if cors_origins:
    allowed_origins.extend(cors_origins.split(','))

CORS(app, origins=allowed_origins)

# Firebase initialization with lazy loading
_db = None

def get_db():
    """Get Firebase Firestore client with lazy initialization"""
    global _db
    if _db is None:
        if not firebase_admin._apps:
            try:
                # Check if running in local development
                service_account_path = os.path.join(os.path.dirname(__file__), 'ServiceAccount.json')
                is_local = os.path.exists(service_account_path)
                
                if is_local:
                    print("LOCAL: Using service account credentials")
                    from firebase_admin import credentials
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred)
                else:
                    # Production environment - use Application Default Credentials
                    print("☁️ PRODUCTION: Using default Firebase credentials")
                    firebase_admin.initialize_app()
            except Exception as e:
                print(f"ERROR Error initializing Firebase: {e}")
                return None
        _db = firestore.client()
    return _db

def send_confirmation_email(booking_data: dict) -> bool:
    """Send professional HTML confirmation email to client"""
    try:
        print(f"Enviando email de confirmación a: {booking_data.get('client_email')}")

        # Email configuration from environment variables
        smtp_server = os.getenv('EMAIL_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('EMAIL_PORT', 587))
        email_username = os.getenv('EMAIL_USERNAME')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_from = os.getenv('EMAIL_FROM')

        if not all([email_username, email_password, email_from]):
            print("Error: Configuración de email incompleta")
            return False

        # Determine service name
        service_name = 'Pizzeros en Acción' if booking_data['service_type'] == 'workshop' else 'Pizza Party'

        # Create professional branded HTML email with modern design
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Evento Confirmado - Pablo's Pizza</title>
            <style>
                /* Reset and base styles */
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #2c2c2c;
                    background-color: #f8f9fa;
                    margin: 0;
                    padding: 0;
                }}

                /* Email container */
                .email-container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
                }}

                /* Header with brand identity */
                .header {{
                    background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
                    padding: 40px 30px;
                    text-align: center;
                    position: relative;
                    overflow: hidden;
                }}

                .header::before {{
                    content: '';
                    position: absolute;
                    top: -50%;
                    left: -50%;
                    width: 200%;
                    height: 200%;
                    background: radial-gradient(circle, rgba(255, 193, 7, 0.1) 0%, transparent 70%);
                    animation: glow 3s ease-in-out infinite alternate;
                }}

                @keyframes glow {{
                    from {{ opacity: 0.5; }}
                    to {{ opacity: 0.8; }}
                }}

                .logo-container {{
                    position: relative;
                    z-index: 2;
                    margin-bottom: 20px;
                    text-align: center;
                }}

                .logo-image {{
                    width: 180px;
                    height: 180px;
                    border-radius: 50%;
                    box-shadow:
                        0 8px 24px rgba(255, 193, 7, 0.4),
                        0 4px 12px rgba(0, 0, 0, 0.3);
                    margin-bottom: 20px;
                    display: inline-block;
                    border: 3px solid #FFC107;
                }}

                .header h1 {{
                    color: #ffffff;
                    font-size: 28px;
                    font-weight: 700;
                    margin: 0;
                    position: relative;
                    z-index: 2;
                    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
                }}

                .status-badge {{
                    display: inline-block;
                    background: linear-gradient(135deg, #FFC107 0%, #FFD54F 100%);
                    color: #000000;
                    padding: 8px 20px;
                    border-radius: 25px;
                    font-weight: 700;
                    font-size: 14px;
                    margin-top: 15px;
                    box-shadow: 0 4px 12px rgba(255, 193, 7, 0.3);
                }}

                /* Content area */
                .content {{
                    padding: 40px 30px;
                    background-color: #ffffff;
                }}

                .greeting {{
                    font-size: 20px;
                    font-weight: 600;
                    color: #000000;
                    margin-bottom: 15px;
                }}

                .intro-text {{
                    font-size: 16px;
                    color: #4a4a4a;
                    margin-bottom: 30px;
                    line-height: 1.7;
                }}

                /* Event details card */
                .event-details {{
                    background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                    border: 2px solid #FFC107;
                    border-radius: 16px;
                    padding: 25px;
                    margin: 30px 0;
                    position: relative;
                    overflow: hidden;
                }}

                .event-details::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: linear-gradient(90deg, #FFC107 0%, #FFD54F 50%, #FFC107 100%);
                }}

                .event-details h3 {{
                    color: #000000;
                    font-size: 18px;
                    font-weight: 700;
                    margin-bottom: 20px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }}

                .detail-row {{
                    display: flex;
                    align-items: center;
                    margin-bottom: 12px;
                    padding: 8px 0;
                    border-bottom: 1px solid #f0f0f0;
                }}

                .detail-row:last-child {{
                    border-bottom: none;
                    margin-bottom: 0;
                }}

                .detail-icon {{
                    width: 24px;
                    font-size: 18px;
                    margin-right: 12px;
                }}

                .detail-label {{
                    font-weight: 600;
                    color: #2c2c2c;
                    min-width: 100px;
                }}

                .detail-value {{
                    color: #4a4a4a;
                    flex: 1;
                }}

                .price-highlight {{
                    color: #FFC107 !important;
                    font-weight: 700;
                    font-size: 18px;
                }}

                /* Expectations section */
                .expectations {{
                    margin: 30px 0;
                }}

                .expectations h3 {{
                    color: #000000;
                    font-size: 18px;
                    font-weight: 700;
                    margin-bottom: 20px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }}

                .expectations ul {{
                    list-style: none;
                    padding: 0;
                }}

                .expectations li {{
                    padding: 12px 0;
                    border-bottom: 1px solid #f0f0f0;
                    display: flex;
                    align-items: flex-start;
                    gap: 12px;
                }}

                .expectations li:last-child {{
                    border-bottom: none;
                }}

                .check-icon {{
                    color: #FFC107;
                    font-weight: bold;
                    font-size: 16px;
                    margin-top: 2px;
                }}

                /* Contact section */
                .contact-section {{
                    background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
                    border-radius: 16px;
                    padding: 25px;
                    margin: 30px 0;
                    text-align: center;
                }}

                .contact-section h3 {{
                    color: #FFC107;
                    font-size: 18px;
                    font-weight: 700;
                    margin-bottom: 15px;
                }}

                .contact-section p {{
                    color: #cccccc;
                    margin-bottom: 20px;
                }}

                .contact-buttons {{
                    display: flex;
                    gap: 15px;
                    justify-content: center;
                    flex-wrap: wrap;
                }}

                .contact-btn {{
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    padding: 12px 20px;
                    background: linear-gradient(135deg, #FFC107 0%, #FFD54F 100%);
                    color: #000000;
                    text-decoration: none;
                    border-radius: 25px;
                    font-weight: 600;
                    transition: transform 0.2s ease;
                    box-shadow: 0 4px 12px rgba(255, 193, 7, 0.3);
                }}

                .contact-btn:hover {{
                    transform: translateY(-2px);
                }}

                /* CTA section */
                .cta-section {{
                    text-align: center;
                    margin: 30px 0;
                    padding: 25px;
                    background: linear-gradient(135deg, #FFF3C4 0%, #FFECB3 100%);
                    border-radius: 16px;
                    border: 1px solid #FFC107;
                }}

                .cta-text {{
                    font-size: 18px;
                    font-weight: 700;
                    color: #000000;
                    margin: 0;
                }}

                /* Footer */
                .footer {{
                    background-color: #f8f9fa;
                    padding: 30px;
                    text-align: center;
                    border-top: 1px solid #e9ecef;
                }}

                .footer-brand {{
                    color: #000000;
                    font-weight: 700;
                    font-size: 16px;
                    margin-bottom: 8px;
                }}

                .footer-tagline {{
                    color: #6c757d;
                    font-size: 14px;
                    margin-bottom: 15px;
                }}

                .footer-disclaimer {{
                    color: #adb5bd;
                    font-size: 12px;
                    line-height: 1.5;
                }}

                /* Mobile responsiveness */
                @media only screen and (max-width: 600px) {{
                    .email-container {{ margin: 10px; }}
                    .header {{ padding: 30px 20px; }}
                    .content {{ padding: 25px 20px; }}
                    .header h1 {{ font-size: 24px; }}
                    .contact-buttons {{ flex-direction: column; align-items: center; }}
                    .detail-row {{ flex-direction: column; align-items: flex-start; gap: 5px; }}
                    .detail-label {{ min-width: auto; }}
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <!-- Header with branding -->
                <div class="header">
                    <div class="logo-container">
                        <img src="https://pablospizza.web.app/assets/logo-nqn6pSjR.png" alt="Pablo's Pizza" class="logo-image">
                    </div>
                    <h1>¡Tu evento ha sido confirmado!</h1>
                    <div class="status-badge">✅ CONFIRMADO</div>
                </div>

                <!-- Main content -->
                <div class="content">
                    <div class="greeting">¡Hola {booking_data.get('client_name', 'Cliente')}!</div>

                    <p class="intro-text">
                        ¡Excelente noticia! Tu evento ha sido <strong>confirmado oficialmente</strong> y estamos emocionados de ser parte de tu celebración especial. Nuestro equipo está preparado para brindarte una experiencia inolvidable.
                    </p>

                    <!-- Event details card -->
                    <div class="event-details">
                        <h3>📋 Detalles de tu evento</h3>

                        <div class="detail-row">
                            <span class="detail-icon">🍕</span>
                            <span class="detail-label">Servicio:</span>
                            <span class="detail-value"><strong>{service_name}</strong></span>
                        </div>

                        <div class="detail-row">
                            <span class="detail-icon">📅</span>
                            <span class="detail-label">Fecha:</span>
                            <span class="detail-value">{booking_data.get('event_date', 'No especificada')}</span>
                        </div>

                        <div class="detail-row">
                            <span class="detail-icon">⏰</span>
                            <span class="detail-label">Hora:</span>
                            <span class="detail-value">{booking_data.get('event_time', 'No especificada')}</span>
                        </div>

                        <div class="detail-row">
                            <span class="detail-icon">👥</span>
                            <span class="detail-label">Participantes:</span>
                            <span class="detail-value">{booking_data.get('participants', 'N/A')} personas</span>
                        </div>

                        <div class="detail-row">
                            <span class="detail-icon">📍</span>
                            <span class="detail-label">Ubicación:</span>
                            <span class="detail-value">{booking_data.get('location', 'No especificada')}</span>
                        </div>

                        <div class="detail-row">
                            <span class="detail-icon">💰</span>
                            <span class="detail-label">Precio:</span>
                            <span class="detail-value price-highlight">${booking_data.get('estimated_price', 0):,.0f} CLP</span>
                        </div>
                    </div>

                    <!-- Expectations section -->
                    <div class="expectations">
                        <h3>🔥 ¿Qué puedes esperar de nosotros?</h3>
                        <ul>
                            <li>
                                <span class="check-icon">✓</span>
                                <span>Nuestro equipo profesional llegará puntualmente con todo el equipamiento necesario</span>
                            </li>
                            <li>
                                <span class="check-icon">✓</span>
                                <span>Ingredientes frescos y de primera calidad, incluyendo opciones especiales</span>
                            </li>
                            <li>
                                <span class="check-icon">✓</span>
                                <span>Una experiencia interactiva, divertida y educativa para todas las edades</span>
                            </li>
                            <li>
                                <span class="check-icon">✓</span>
                                <span>Pizzas artesanales deliciosas hechas por los propios participantes</span>
                            </li>
                            <li>
                                <span class="check-icon">✓</span>
                                <span>Recuerdos fotográficos y momentos únicos que durarán para siempre</span>
                            </li>
                        </ul>
                    </div>

                    <!-- Contact section -->
                    <div class="contact-section">
                        <h3>📞 ¿Tienes alguna pregunta?</h3>
                        <p>Nuestro equipo está disponible para ayudarte con cualquier consulta o cambio de último momento.</p>
                        <div class="contact-buttons">
                            <a href="https://wa.me/56989424566" class="contact-btn">
                                📱 WhatsApp: +56 9 8942 4566
                            </a>
                            <a href="mailto:pablospizza.cl@gmail.com" class="contact-btn">
                                ✉️ pablospizza.cl@gmail.com
                            </a>
                        </div>
                    </div>

                    <!-- Calendar section -->
                    <div class="calendar-section" style="background-color: #f8f9fa; padding: 25px 20px; margin: 25px 0; border-radius: 8px; border: 2px dashed #FFC107;">
                        <h3 style="color: #000000; font-size: 20px; margin-bottom: 15px; text-align: center;">📅 Agregar a mi Calendario</h3>
                        <p style="text-align: center; margin-bottom: 15px;">Hemos incluido una invitación de calendario con este email. <strong>Revisa los archivos adjuntos</strong> y ábrelo para agregar automáticamente el evento a tu calendario personal.</p>
                        <div style="background-color: #FFF3CD; border-left: 4px solid #FFC107; padding: 12px; margin: 15px 0; border-radius: 4px;">
                            <p style="margin: 0; font-size: 14px; color: #856404;">
                                💡 <strong>Tip:</strong> El archivo "evento_pablos_pizza.ics" se puede abrir con Google Calendar, Outlook, Apple Calendar y la mayoría de aplicaciones de calendario.
                            </p>
                        </div>
                    </div>

                    <!-- CTA section -->
                    <div class="cta-section">
                        <p class="cta-text">¡Nos vemos pronto para una experiencia gastronómica increíble! 🎉🍕</p>
                    </div>
                </div>

                <!-- Footer -->
                <div class="footer">
                    <div class="footer-brand">Pablo's Pizza</div>
                    <div class="footer-tagline">Creando momentos deliciosos y memorables desde siempre</div>
                    <div class="footer-disclaimer">
                        Este es un email automático de confirmación. Para consultas o cambios, utiliza nuestros canales de contacto oficiales.
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = email_from
        msg['To'] = booking_data.get('client_email')
        msg['Subject'] = "¡Tu evento con Pablo's Pizza ha sido confirmado!"

        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        # Generate and attach calendar invitation
        calendar_content = generate_calendar_invite(booking_data)
        if calendar_content:
            cal_attachment = MIMEText(calendar_content, 'calendar')
            cal_attachment['Content-Disposition'] = f'attachment; filename="evento_pablos_pizza.ics"'
            cal_attachment.set_type('text/calendar')
            cal_attachment.set_param('method', 'REQUEST')
            msg.attach(cal_attachment)
            print("Invitación de calendario agregada al email")

        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_username, email_password)
        text = msg.as_string()
        server.sendmail(email_from, booking_data.get('client_email'), text)
        server.quit()

        # Save email record to Firestore
        try:
            email_data = {
                "recipient_email": booking_data.get('client_email'),
                "subject": "¡Tu evento con Pablo's Pizza ha sido confirmado!",
                "booking_id": booking_data.get('id'),
                "email_type": "confirmation",
                "sent_at": datetime.now(),
                "status": "sent"
            }
            db = get_db()
            db.collection("emails").add(email_data)
            print(f"Registro de email guardado en Firestore")
        except Exception as e:
            print(f"Error guardando registro de email: {e}")

        print(f"Email de confirmación enviado exitosamente a: {booking_data.get('client_email')}")
        return True

    except Exception as e:
        print(f"Error enviando email de confirmación: {e}")

        # Save error record
        try:
            error_email = {
                "recipient_email": booking_data.get('client_email'),
                "subject": "¡Tu evento con Pablo's Pizza ha sido confirmado!",
                "booking_id": booking_data.get('id'),
                "email_type": "confirmation",
                "sent_at": datetime.now(),
                "status": "failed",
                "error": str(e)
            }
            db = get_db()
            db.collection("emails").add(error_email)
        except:
            pass

        return False

def calculate_estimated_price(service_types: str, pizzeros_participants: int = 0, party_participants: int = 0, participants: int = 0) -> float:
    """
    Calculate estimated price based on service types and participants count per service

    Args:
        service_types: Comma-separated service types (e.g., "workshop", "pizza_party", or "workshop,pizza_party")
        pizzeros_participants: Number of participants for Pizzeros en Acción
        party_participants: Number of participants for Pizza Party
        participants: Legacy field for backward compatibility
    """
    print(f"[CALCULATE] Starting calculation:")
    print(f"  service_types='{service_types}'")
    print(f"  pizzeros_participants={pizzeros_participants}")
    print(f"  party_participants={party_participants}")
    print(f"  participants={participants} (legacy)")

    total_price = 0
    services = [s.strip() for s in service_types.split(',') if s.strip()]

    for service in services:
        if service == "workshop" or service == "pizzeros":
            # Pizzeros en Acción pricing with new tiered structure
            service_participants = pizzeros_participants if pizzeros_participants > 0 else participants
            if service_participants <= 0:
                print(f"  Skipping Pizzeros en Acción: no participants")
                continue

            if service_participants <= 10:
                # 0-10 children: $13,500 minimum charge
                service_total = 13500
                print(f"  Pizzeros en Acción (0-10): {service_participants} niños -> $13,500 (mínimo)")
            elif service_participants <= 14:
                # 11-14 children: $10,500 per child
                service_total = service_participants * 10500
                print(f"  Pizzeros en Acción (11-14): {service_participants} niños x $10,500 -> ${service_total}")
            elif service_participants <= 19:
                # 15-19 children: $9,500 per child
                service_total = service_participants * 9500
                print(f"  Pizzeros en Acción (15-19): {service_participants} niños x $9,500 -> ${service_total}")
            else:
                # 20+ children: $9,000 per child
                service_total = service_participants * 9000
                print(f"  Pizzeros en Acción (20+): {service_participants} niños x $9,000 -> ${service_total}")

            total_price += service_total

        elif service == "pizza_party" or service == "party":
            # Pizza Party pricing logic
            service_participants = party_participants if party_participants > 0 else participants
            if service_participants <= 0:
                print(f"  Skipping Pizza Party: no participants")
                continue

            unit_base = int(os.getenv('DEFAULT_PIZZA_PARTY_PRICE', 11990))
            if service_participants >= 20:
                unit_final = round(unit_base * 0.9)  # 10% discount for 20+
            else:
                unit_final = unit_base

            service_total = unit_final * service_participants
            print(f"  Pizza Party: {service_participants} personas x ${unit_final} -> ${service_total}")
            total_price += service_total

        else:
            print(f"  Unknown service type: {service}")

    result = round(total_price, 2)
    print(f"[CALCULATE] Final total: ${result}")
    return result

def create_event_from_booking(booking_data: dict) -> bool:
    """Create an event automatically when a booking is completed with costs"""
    try:
        print(f"Creando evento automáticamente para booking: {booking_data.get('id')}")
        
        # Generate event ID
        event_id = str(uuid.uuid4())
        
        # Determine service name for title
        service_types = booking_data.get('service_type', '')
        services = [s.strip() for s in service_types.split(',') if s.strip()]

        if len(services) > 1:
            service_name = 'Pizza Party + Pizzeros en Acción'
        elif 'workshop' in services or 'pizzeros' in services:
            service_name = 'Pizzeros en Acción'
        else:
            service_name = 'Pizza Party'

        event_title = f"{service_name} - {booking_data.get('client_name', 'Cliente')}"
        
        # Parse event date - keep as string for Firestore compatibility
        event_date = booking_data.get('event_date')
        if not isinstance(event_date, str):
            # If it's a datetime object, convert to string
            if hasattr(event_date, 'strftime'):
                event_date = event_date.strftime('%Y-%m-%d')
            else:
                # Fallback to current date as string
                event_date = datetime.now().strftime('%Y-%m-%d')
        
        # Calculate profit if we have both estimated price and cost
        estimated_price = booking_data.get('estimated_price', 0)
        event_cost = booking_data.get('event_cost', 0)
        calculated_profit = estimated_price - event_cost if estimated_price and event_cost else 0
        
        # Use provided profit or calculated profit
        final_profit = booking_data.get('event_profit', calculated_profit)
        
        # Create event data
        event_data = {
            "id": event_id,
            "booking_id": booking_data.get('id'),
            "title": event_title,
            "description": f"Evento realizado automáticamente desde agendamiento. Servicio: {service_name}",
            "event_date": event_date,
            "participants": booking_data.get('participants', 0),
            "final_price": estimated_price,
            "event_cost": event_cost,
            "profit": final_profit,
            "notes": f"Evento creado automáticamente. Cliente: {booking_data.get('client_name')}. Ubicación: {booking_data.get('location', 'No especificada')}",
            "status": "completed",
            "created_at": datetime.now(),
            "photos": [],  # Array vacío para fotos que se pueden agregar después
            "source": "auto_booking"  # Indicador de que fue creado automáticamente
        }
        
        # Save to Firestore events collection
        db = get_db()
        db.collection("events").document(event_id).set(event_data)
        
        print(f"Evento creado exitosamente: {event_id} para booking {booking_data.get('id')}")
        return True
        
    except Exception as e:
        print(f"Error creando evento automático: {e}")
        return False

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        # Test database connection
        db = get_db()
        db_status = "connected" if db else "disconnected"

        return jsonify({
            "status": "healthy",
            "service": "Pablo's Pizza API - Production Ready",
            "environment": os.getenv('ENVIRONMENT', 'production'),
            "version": "2.1.1",
            "database": db_status,
            "cors_origins": len(allowed_origins),
            "endpoints": [
                "/api/health",
                "/api/bookings/",
                "/api/events/",
                "/api/gallery/",
                "/api/contacts/"
            ]
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

# Root endpoint
@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        "message": "Pablo's Pizza API - ¡Funcionando!",
        "version": "2.0.0",
        "environment": os.getenv('ENVIRONMENT', 'production')
    })

# Bookings endpoint
@app.route('/api/bookings/', methods=['POST'])
def create_booking():
    """Create new booking"""
    try:
        print("CREATE_BOOKING INICIADO - PRODUCTION VERSION - TEST NUMBERS")
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['service_type', 'participants']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Generate booking ID
        booking_id = str(uuid.uuid4())

        # Calculate estimated price using new structure
        estimated_price = calculate_estimated_price(
            service_types=data.get('service_type', ''),
            pizzeros_participants=data.get('pizzeros_participants', 0),
            party_participants=data.get('party_participants', 0),
            participants=data.get('participants', 0)  # Legacy fallback
        )

        print(f"PRECIO CALCULADO: {data.get('service_type')} - {data.get('participants')} part = ${estimated_price} CLP")

        # Prepare booking data
        booking_data = {
            "id": booking_id,
            **data,
            "status": "pending",
            "created_at": datetime.now(),
            "estimated_price": estimated_price
        }

        # Save to Firestore
        db = get_db()
        db.collection("bookings").document(booking_id).set(booking_data)
        print(f"GUARDADO EN FIRESTORE: {booking_id} con precio ${estimated_price}")

        # Send EMAIL notification to admin about new booking
        try:
            print(f"Enviando email de notificación de nuevo agendamiento al admin")
            email_sent = send_admin_email_notification(booking_data)

            if email_sent:
                print(f"Email de notificación de nuevo agendamiento enviado exitosamente al admin")
            else:
                print(f"Error al enviar email de notificación de nuevo agendamiento al admin")

        except Exception as e:
            print(f"Error enviando email al admin: {e}")
            # No fallar la creación de la reserva si falla la notificación

        # Send WhatsApp notification to admin about new booking
        try:
            admin_phone = os.getenv('ADMIN_WHATSAPP_NUMBER', '+56998960858')

            # Handle multiple services properly
            service_types = booking_data.get('service_type', '')
            services = [s.strip() for s in service_types.split(',') if s.strip()]

            if len(services) > 1:
                service_name = 'Pizza Party + Pizzeros en Acción'
            elif 'workshop' in services or 'pizzeros' in services:
                service_name = 'Pizzeros en Acción'
            else:
                service_name = 'Pizza Party'

            # Format participants info based on new structure
            participants_info = ""
            if booking_data.get('pizzeros_participants') and booking_data.get('party_participants'):
                participants_info = f"Pizzeros: {booking_data['pizzeros_participants']} niños, Pizza Party: {booking_data['party_participants']} personas"
            elif booking_data.get('pizzeros_participants'):
                participants_info = f"{booking_data['pizzeros_participants']} niños"
            elif booking_data.get('party_participants'):
                participants_info = f"{booking_data['party_participants']} personas"
            else:
                participants_info = f"{booking_data.get('participants', 'No especificado')}"

            admin_whatsapp_message = f"""🍕 *Pablo's Pizza - NUEVO AGENDAMIENTO*

¡Te acaban de agendar un evento!

👤 *Cliente:* {booking_data.get('client_name', 'No especificado')}
📱 *Teléfono:* {booking_data.get('client_phone', 'No especificado')}
📧 *Email:* {booking_data.get('client_email', 'No especificado')}

🍕 *Servicio:* {service_name}
📅 *Fecha:* {booking_data.get('event_date', 'No especificada')}
⏰ *Hora:* {booking_data.get('event_time', 'No especificada')}
👥 *Participantes:* {participants_info}
📍 *Ubicación:* {booking_data.get('location', 'No especificada')}
💰 *Precio estimado:* ${booking_data.get('estimated_price', 0):,.0f} CLP

🔔 *Favor verificar en la plataforma para confirmar el evento.*

ID: {booking_data.get('id', 'N/A')}"""

            print(f"Enviando WhatsApp de nueva reserva al admin: {admin_phone}")
            admin_whatsapp_sent = asyncio.run(send_whatsapp_with_template_fallback(
                admin_phone,
                admin_whatsapp_message,
                "new_booking_admin_alert",
                booking_data
            ))

            if admin_whatsapp_sent:
                print(f"WhatsApp de nueva reserva enviado exitosamente al admin")
            else:
                print(f"Error al enviar WhatsApp de nueva reserva al admin")

        except Exception as e:
            print(f"Error enviando WhatsApp al admin: {e}")
            # No fallar la creación de la reserva si falla la notificación

        # Send WhatsApp notification to business partner about new booking
        try:
            partner_phone = os.getenv('PARTNER_WHATSAPP_NUMBER', '+56998960858')

            # Use same service logic as admin
            partner_message = f"""🍕 *Pablo's Pizza - NUEVO AGENDAMIENTO*

¡Hola! Te informo que acabamos de recibir una nueva reserva:

👤 *Cliente:* {booking_data.get('client_name', 'No especificado')}
📱 *Teléfono:* {booking_data.get('client_phone', 'No especificado')}

🍕 *Servicio:* {service_name}
📅 *Fecha:* {booking_data.get('event_date', 'No especificada')}
⏰ *Hora:* {booking_data.get('event_time', 'No especificada')}
👥 *Participantes:* {participants_info}
📍 *Ubicación:* {booking_data.get('location', 'No especificada')}
💰 *Precio estimado:* ${booking_data.get('estimated_price', 0):,.0f} CLP

¡Excelente! 🎉"""

            print(f"Enviando WhatsApp de nueva reserva al socio: {partner_phone}")
            whatsapp_sent = asyncio.run(send_whatsapp_with_template_fallback(
                partner_phone,
                partner_message,
                "new_booking_partner_alert",
                booking_data
            ))

            if whatsapp_sent:
                print(f"WhatsApp de nueva reserva enviado exitosamente al socio")
            else:
                print(f"Error al enviar WhatsApp de nueva reserva al socio")

        except Exception as e:
            print(f"Error enviando WhatsApp al socio: {e}")
            # No fallar la creación de la reserva si falla la notificación

        return jsonify(booking_data), 201

    except Exception as e:
        print(f"Error creating booking: {e}")
        return jsonify({"error": str(e)}), 500

# Get bookings endpoint
@app.route('/api/bookings/', methods=['GET'])
def get_bookings():
    """Get all bookings"""
    try:
        db = get_db()
        bookings_ref = db.collection("bookings")
        bookings = []

        for doc in bookings_ref.stream():
            booking = doc.to_dict()
            booking['id'] = doc.id
            bookings.append(booking)

        return jsonify(bookings), 200

    except Exception as e:
        print(f"Error getting bookings: {e}")
        return jsonify({"error": str(e)}), 500

# Get specific booking
@app.route('/api/bookings/<booking_id>', methods=['GET'])
def get_booking(booking_id):
    """Get specific booking by ID"""
    try:
        db = get_db()
        doc_ref = db.collection("bookings").document(booking_id)
        doc = doc_ref.get()

        if doc.exists:
            booking = doc.to_dict()
            booking['id'] = doc.id
            return jsonify(booking), 200
        else:
            return jsonify({"error": "Booking not found"}), 404

    except Exception as e:
        print(f"Error getting booking: {e}")
        return jsonify({"error": str(e)}), 500

# Events endpoints
@app.route('/api/events/', methods=['GET'])
def get_events():
    """Get all events"""
    try:
        db = get_db()
        events_ref = db.collection("events").order_by("created_at", direction=firestore.Query.DESCENDING)
        events = []

        for doc in events_ref.stream():
            event = doc.to_dict()
            event['id'] = doc.id
            events.append(event)

        return jsonify(events), 200

    except Exception as e:
        print(f"Error getting events: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/events/', methods=['POST'])
def create_event():
    """Create a new event"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Required fields
        required_fields = ['title', 'event_date']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        db = get_db()

        # Create event document
        event_data = {
            'title': data['title'],
            'description': data.get('description', ''),
            'event_date': data['event_date'],
            'participants': data.get('participants', 0),
            'final_price': data.get('final_price', 0),
            'event_cost': data.get('event_cost', 0),
            'profit': data.get('profit', 0),
            'notes': data.get('notes', ''),
            'status': data.get('status', 'pending'),
            'booking_id': data.get('booking_id'),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            # Gallery fields
            'is_published': data.get('is_published', False),
            'is_featured': data.get('is_featured', False),
            'category': data.get('category', 'workshop' if 'workshop' in data.get('title', '').lower() or 'pizzeros' in data.get('title', '').lower() else 'party'),
            'satisfaction': data.get('satisfaction', 5),
            'highlight': data.get('highlight', 'Experiencia única'),
            'age_group': data.get('age_group', 'Todas las edades')
        }

        # Add to database
        doc_ref = db.collection("events").add(event_data)
        event_id = doc_ref[1].id

        # Return created event
        event_data['id'] = event_id
        event_data['created_at'] = event_data['created_at'].isoformat()
        event_data['updated_at'] = event_data['updated_at'].isoformat()

        print(f"✅ Event created successfully: {event_id}")
        return jsonify(event_data), 201

    except Exception as e:
        print(f"❌ Error creating event: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/events/<event_id>', methods=['GET'])
def get_event(event_id):
    """Get specific event by ID"""
    try:
        db = get_db()
        doc_ref = db.collection("events").document(event_id)
        doc = doc_ref.get()

        if doc.exists:
            event = doc.to_dict()
            event['id'] = doc.id
            return jsonify(event), 200
        else:
            return jsonify({"error": "Event not found"}), 404

    except Exception as e:
        print(f"Error getting event: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    """Update event data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        db = get_db()
        doc_ref = db.collection("events").document(event_id)
        doc = doc_ref.get()

        if not doc.exists:
            return jsonify({"error": "Event not found"}), 404

        # Update fields
        update_data = {}
        updatable_fields = ['title', 'description', 'notes', 'photos', 'final_price', 'event_cost', 'profit']
        for field in updatable_fields:
            if field in data:
                update_data[field] = data[field]

        # Add update timestamp
        update_data['updated_at'] = datetime.now()

        # Update in Firestore
        doc_ref.update(update_data)

        # Get updated event data
        updated_doc = doc_ref.get()
        updated_event = updated_doc.to_dict()
        updated_event['id'] = updated_doc.id

        return jsonify(updated_event), 200

    except Exception as e:
        print(f"Error updating event: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/events/<event_id>/publish', methods=['PUT', 'OPTIONS'])
def publish_event(event_id):
    """Publish or unpublish an event"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
        return response

    try:
        data = request.get_json()
        if not data:
            response = jsonify({"error": "No data provided"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
            return response, 400

        db = get_db()
        doc_ref = db.collection("events").document(event_id)
        doc = doc_ref.get()

        if not doc.exists:
            response = jsonify({"error": "Event not found"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
            return response, 404

        # Update publication fields
        update_data = {
            'is_published': data.get('is_published', False),
            'updated_at': datetime.now()
        }

        if 'is_featured' in data:
            update_data['is_featured'] = data['is_featured']

        # Update in Firestore
        doc_ref.update(update_data)

        # Get updated event data
        updated_doc = doc_ref.get()
        updated_event = updated_doc.to_dict()
        updated_event['id'] = updated_doc.id

        print(f"✅ Event {event_id} publication status updated: published={update_data['is_published']}")

        response = jsonify(updated_event)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
        return response, 200

    except Exception as e:
        print(f"Error publishing event: {e}")
        response = jsonify({"error": str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
        return response, 500

@app.route('/api/gallery/<photo_id>/publish', methods=['PUT', 'OPTIONS'])
def publish_gallery_photo(photo_id):
    """Publish or unpublish a gallery photo"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
        return response

    try:
        data = request.get_json()
        if not data:
            response = jsonify({"error": "No data provided"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
            return response, 400

        db = get_db()
        doc_ref = db.collection("gallery").document(photo_id)
        doc = doc_ref.get()

        if not doc.exists:
            response = jsonify({"error": "Photo not found"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
            return response, 404

        # Update publication status
        update_data = {
            'is_published': data.get('is_published', False),
            'updated_at': datetime.now()
        }

        # Update in Firestore
        doc_ref.update(update_data)

        # Get updated photo data
        updated_doc = doc_ref.get()
        updated_photo = updated_doc.to_dict()
        updated_photo['id'] = updated_doc.id

        print(f"✅ Photo {photo_id} publication status updated: published={update_data['is_published']}")

        response = jsonify(updated_photo)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
        return response, 200

    except Exception as e:
        print(f"Error publishing photo: {e}")
        response = jsonify({"error": str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
        return response, 500

# Gallery endpoints (basic implementation)
@app.route('/api/gallery/', methods=['GET'])
def get_gallery_images():
    """Get gallery images for admin management only"""
    try:
        print("=== GALLERY ENDPOINT DEBUG ===")
        event_id = request.args.get('event_id')
        print(f"Event ID param: {event_id}")

        db = get_db()

        # Get gallery images, filtering by event_id if specified
        if event_id:
            images_ref = db.collection("gallery").where("event_id", "==", event_id).order_by("uploaded_at", direction=firestore.Query.DESCENDING)
        else:
            images_ref = db.collection("gallery").order_by("uploaded_at", direction=firestore.Query.DESCENDING)

        gallery_items = []
        for doc in images_ref.stream():
            image = doc.to_dict()
            print(f"Processing image: {doc.id}, event_id: {image.get('event_id')}, published: {image.get('is_published')}")

            gallery_item = {
                'id': doc.id,
                'title': image.get('title', 'Imagen'),
                'url': image.get('url', ''),
                'is_published': image.get('is_published', False),
                'uploaded_at': image.get('uploaded_at'),
                'event_id': image.get('event_id')
            }

            gallery_items.append(gallery_item)

        print(f"Returning {len(gallery_items)} gallery items")
        return jsonify(gallery_items), 200

    except Exception as e:
        print(f"Error getting gallery images: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/gallery/event/<event_id>', methods=['GET', 'OPTIONS'])
def get_gallery_by_event(event_id):
    """Get gallery images for a specific event"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response

    try:
        print(f"Getting gallery images for event: {event_id}")
        db = get_db()
        if db is None:
            response = jsonify({"error": "Database connection failed"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
            return response, 500

        # Query images by event_id
        images_ref = db.collection("gallery").where("event_id", "==", event_id)
        # Temporarily removing order_by to test if it causes the 500 error
        # images_ref = images_ref.order_by("uploaded_at", direction=firestore.Query.DESCENDING)

        images = []
        try:
            for doc in images_ref.stream():
                image = doc.to_dict()
                image['id'] = doc.id
                images.append(image)
            print(f"Found {len(images)} images for event {event_id}")
        except Exception as db_error:
            print(f"Database query error for event {event_id}: {db_error}")
            import traceback
            traceback.print_exc()
            response = jsonify({"error": "Database query failed", "details": str(db_error), "event_id": event_id})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
            return response, 500

        response = jsonify(images)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response, 200

    except Exception as e:
        print(f"Error getting gallery images for event {event_id}: {e}")
        import traceback
        traceback.print_exc()
        response = jsonify({"error": str(e), "event_id": event_id})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response, 500

@app.route('/api/gallery/public', methods=['GET', 'OPTIONS'])
def get_public_gallery_images():
    """Get public gallery images grouped by events for the website gallery page"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response

    try:
        print("📸 GALLERY PUBLIC - Starting request")
        db = get_db()
        if db is None:
            print("❌ Database connection failed")
            response = jsonify({"error": "Database connection failed"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 500

        gallery_events = []

        # Simplify by getting all published gallery images directly
        try:
            print("📸 Querying published gallery images directly...")
            gallery_ref = db.collection("gallery").where("is_published", "==", True)
            events_dict = {}

            # Group images by event_id
            for img_doc in gallery_ref.stream():
                img_data = img_doc.to_dict()
                event_id = img_data.get('event_id')
                if not event_id or not img_data.get('url'):
                    continue

                if event_id not in events_dict:
                    events_dict[event_id] = {
                        'images': [],
                        'event_data': None
                    }
                events_dict[event_id]['images'].append(img_data.get('url'))

            # Now get event details for each event that has images
            events_count = 0
            for event_id, data in events_dict.items():
                try:
                    event_doc = db.collection("events").document(event_id).get()
                    if event_doc.exists:
                        event = event_doc.to_dict()
                        if event.get("status") == "completed":
                            events_count += 1
                            event_images = data['images']

                            # Determine title based on available fields
                            event_title = event.get('title', 'Evento Pablo\'s Pizza')
                            if not event_title or event_title == 'Evento Pablo\'s Pizza':
                                # Try to construct from other fields
                                service_type = 'Taller' if 'workshop' in event.get('category', '').lower() or 'taller' in event.get('title', '').lower() else 'Fiesta'
                                event_title = f"{service_type} Pablo's Pizza"

                            gallery_event = {
                                'id': event_id,
                                'title': event_title,
                                'description': event.get('description', 'Una experiencia inolvidable con Pablo\'s Pizza'),
                                'category': event.get('category', 'party'),
                                'images': event_images,
                                'participants': event.get('participants', 15),
                                'date': event.get('event_date'),
                                'featured': len(event_images) >= 3,  # Featured if has 3+ images
                                'highlight': event.get('highlight', f"Evento para {event.get('participants', 15)} personas"),
                                'age_group': event.get('age_group', 'Todas las edades')
                            }
                            gallery_events.append(gallery_event)
                            print(f"📸 Added event {event_id} with {len(event_images)} images")

                except Exception as event_error:
                    print(f"❌ Error processing event {event_id}: {event_error}")
                    continue

            print(f"📸 Processed {events_count} events, added {len(gallery_events)} with images")

        except Exception as events_error:
            print(f"❌ Error querying events: {events_error}")

        # If no events with images, return individual published images
        if not gallery_events:
            print("📸 No events with images found, getting individual gallery images...")
            try:
                images_ref = db.collection("gallery").where("is_published", "==", True).limit(20)

                for doc in images_ref.stream():
                    image = doc.to_dict()
                    if image.get('url'):  # Only include images with valid URLs
                        gallery_event = {
                            'id': doc.id,
                            'title': image.get('title', 'Evento Pablo\'s Pizza'),
                            'description': image.get('description', 'Una experiencia única con Pablo\'s Pizza'),
                            'category': image.get('category', 'party'),
                            'images': [image.get('url')],
                            'participants': 15,
                            'date': image.get('uploaded_at'),
                            'featured': False,
                            'highlight': 'Experiencia única',
                            'age_group': 'Todas las edades'
                        }
                        gallery_events.append(gallery_event)

                print(f"📸 Added {len(gallery_events)} individual images")

            except Exception as images_error:
                print(f"❌ Error querying individual images: {images_error}")

        # If still no gallery events, create some sample data
        if not gallery_events:
            print("📸 No images found, creating sample gallery event")
            gallery_events = [{
                'id': 'sample-1',
                'title': 'Taller Pablo\'s Pizza - Experiencia Educativa',
                'description': 'Ven y aprende a hacer deliciosas pizzas artesanales en nuestro taller interactivo. Una experiencia perfecta para toda la familia.',
                'category': 'workshop',
                'images': ['https://pablospizza.web.app/assets/logo-nqn6pSjR.png'],
                'participants': 15,
                'date': '2024-01-15',
                'featured': True,
                'highlight': 'Experiencia educativa única',
                'age_group': 'Todas las edades'
            }]

        print(f"📸 Returning {len(gallery_events)} gallery events")
        response = jsonify(gallery_events)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200

    except Exception as e:
        print(f"❌ Error in gallery public endpoint: {e}")
        import traceback
        traceback.print_exc()

        # Return a safe fallback response
        fallback_data = [{
            'id': 'fallback-1',
            'title': 'Pablo\'s Pizza - Experiencias Únicas',
            'description': 'Próximamente podrás ver nuestra galería de eventos realizados. ¡Estamos preparando contenido increíble para ti!',
            'category': 'party',
            'images': ['https://pablospizza.web.app/assets/logo-nqn6pSjR.png'],
            'participants': 15,
            'date': '2024-01-01',
            'featured': false,
            'highlight': 'Próximamente',
            'age_group': 'Todas las edades'
        }]

        response = jsonify(fallback_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200

@app.route('/api/gallery/upload', methods=['POST', 'OPTIONS'])
def upload_gallery_image():
    """Upload image to Firebase Storage and save metadata to Firestore"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response

    try:
        print(f"📸 GALLERY UPLOAD - Headers: {dict(request.headers)}")
        print(f"📸 GALLERY UPLOAD - Form data: {dict(request.form)}")
        print(f"📸 GALLERY UPLOAD - Files: {list(request.files.keys())}")

        # Check if file is in the request
        if 'image' not in request.files:
            print("❌ No image file provided")
            response = jsonify({"error": "No image file provided", "received_files": list(request.files.keys())})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
            return response, 400

        file = request.files['image']
        if file.filename == '':
            print("❌ No file selected")
            response = jsonify({"error": "No file selected"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
            return response, 400

        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_extension not in allowed_extensions:
            print(f"❌ Invalid file type: {file_extension}")
            response = jsonify({"error": f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
            return response, 400

        # Get form data
        title = request.form.get('title', 'Nueva imagen')
        description = request.form.get('description', '')
        event_id = request.form.get('event_id')
        category = request.form.get('category', 'general')
        is_featured = request.form.get('is_featured', 'false').lower() == 'true'

        print(f"📸 Processing upload: {title}, event_id: {event_id}")

        # Generate unique filename
        image_id = str(uuid.uuid4())
        filename = f"{image_id}.{file_extension}"

        # Upload to Firebase Storage - using default bucket for the project
        bucket = storage.bucket()
        blob_path = f"gallery/{event_id}/{filename}" if event_id else f"gallery/{filename}"
        blob = bucket.blob(blob_path)

        # Reset file pointer to beginning
        file.seek(0)

        # Upload file with metadata
        content_type = file.content_type or f'image/{file_extension}'
        print(f"📸 Uploading to Firebase Storage: {blob_path}, content_type: {content_type}")

        blob.upload_from_file(
            file,
            content_type=content_type
        )

        # Make the file publicly readable
        blob.make_public()

        # Get the public URL
        public_url = blob.public_url
        print(f"📸 Upload successful, public URL: {public_url}")

        # Save metadata to Firestore
        image_data = {
            "id": image_id,
            "url": public_url,
            "title": title,
            "description": description,
            "event_id": event_id,
            "category": category,
            "uploaded_at": datetime.now(),
            "is_featured": is_featured,
            "storage_path": blob_path,
            "filename": filename,
            "content_type": content_type
        }

        db = get_db()
        if db is None:
            print("❌ Database connection failed")
            response = jsonify({"error": "Database connection failed"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
            return response, 500

        db.collection("gallery").document(image_id).set(image_data)
        print(f"📸 Metadata saved to Firestore: {image_id}")

        # Convert datetime for JSON serialization
        image_data['uploaded_at'] = image_data['uploaded_at'].isoformat()

        response = jsonify(image_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response, 201

    except Exception as e:
        print(f"❌ Error uploading image: {e}")
        import traceback
        traceback.print_exc()
        response = jsonify({"error": str(e), "details": "Check server logs for more information"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response, 500

# Contact System Endpoints
@app.route('/api/contacts', methods=['GET', 'POST', 'OPTIONS'])
def handle_contacts():
    """Handle contact messages - GET to retrieve, POST to create"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        return response

    if request.method == 'GET':
        try:
            print("🔍 Getting contact messages...")
            db = get_db()
            if db is None:
                return jsonify({"error": "Database connection failed"}), 500

            # Query parameters for filtering
            status = request.args.get('status')
            priority = request.args.get('priority')
            limit = int(request.args.get('limit', 50))

            contacts_ref = db.collection("contacts")

            # Apply filters
            if status:
                contacts_ref = contacts_ref.where("status", "==", status)
            if priority:
                contacts_ref = contacts_ref.where("priority", "==", priority)

            contacts_ref = contacts_ref.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)

            contacts = []
            for doc in contacts_ref.stream():
                contact = doc.to_dict()
                contact['id'] = doc.id
                contacts.append(contact)

            print(f"✅ Found {len(contacts)} contact messages")
            response = jsonify(contacts)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 200

        except Exception as e:
            print(f"❌ Error getting contacts: {e}")
            response = jsonify({"error": str(e)})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 500

    if request.method == 'POST':
        try:
            print("📝 Creating new contact message...")
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400

            # Required fields validation
            required_fields = ['name', 'email', 'subject', 'message']
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Missing required field: {field}"}), 400

            # Generate contact ID
            contact_id = str(uuid.uuid4())
            current_time = datetime.now()

            # Create contact data
            contact_data = {
                "id": contact_id,
                "name": data['name'],
                "email": data['email'],
                "phone": data.get('phone'),
                "subject": data['subject'],
                "message": data['message'],
                "priority": data.get('priority', 'normal'),
                "status": "pending",
                "created_at": current_time,
                "updated_at": current_time,
                "response_sent": False
            }

            # Save to Firestore
            db = get_db()
            db.collection("contacts").document(contact_id).set(contact_data)

            # Send WhatsApp notification to admin (if configured)
            try:
                admin_phone = "+5491167329628"  # Replace with actual admin WhatsApp number
                message_text = f"🔔 *Nuevo mensaje de contacto*\n\n" \
                              f"*De:* {data['name']}\n" \
                              f"*Email:* {data['email']}\n" \
                              f"*Asunto:* {data['subject']}\n" \
                              f"*Mensaje:* {data['message'][:100]}{'...' if len(data['message']) > 100 else ''}\n" \
                              f"*Prioridad:* {data.get('priority', 'normal').upper()}\n\n" \
                              f"Responde desde el panel de administración."

                # Note: WhatsApp integration would go here
                # For now, we'll just log it
                print(f"📱 WhatsApp notification would be sent to {admin_phone}")
                print(f"Message: {message_text}")

            except Exception as whatsapp_error:
                print(f"⚠️ WhatsApp notification failed: {whatsapp_error}")

            print(f"✅ Contact message created: {contact_id}")
            response = jsonify(contact_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 201

        except Exception as e:
            print(f"❌ Error creating contact: {e}")
            response = jsonify({"error": str(e)})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 500

@app.route('/api/contacts/<contact_id>', methods=['PUT', 'OPTIONS'])
def update_contact(contact_id):
    """Update contact message status, assignment, notes, etc."""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
        return response

    try:
        print(f"📝 Updating contact: {contact_id}")
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        db = get_db()
        contact_ref = db.collection("contacts").document(contact_id)
        contact_doc = contact_ref.get()

        if not contact_doc.exists:
            return jsonify({"error": "Contact not found"}), 404

        # Prepare update data
        update_data = {"updated_at": datetime.now()}

        # Update allowed fields
        allowed_fields = ['status', 'assigned_to', 'notes', 'response_method', 'response_sent']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]

        # Set resolved_at if status changes to resolved
        if data.get('status') == 'resolved':
            update_data['resolved_at'] = datetime.now()

        # Update in Firestore
        contact_ref.update(update_data)

        # Get updated contact
        updated_contact = contact_ref.get().to_dict()
        updated_contact['id'] = contact_id

        print(f"✅ Contact updated: {contact_id}")
        response = jsonify(updated_contact)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200

    except Exception as e:
        print(f"❌ Error updating contact: {e}")
        response = jsonify({"error": str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

def send_contact_response_email(contact_data: dict, response_message: str) -> bool:
    """Send email response to contact inquiry"""
    try:
        print(f"📧 Sending response email to: {contact_data['email']}")

        # Email configuration
        smtp_server = os.getenv('EMAIL_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('EMAIL_PORT', 587))
        email_username = os.getenv('EMAIL_USERNAME')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_from = os.getenv('EMAIL_FROM')

        if not all([email_username, email_password, email_from]):
            print("❌ Email configuration not complete")
            return False

        # Create professional HTML email response
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Respuesta - Pablo's Pizza</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #2c2c2c;
                    background-color: #f8f9fa;
                    margin: 0;
                    padding: 0;
                }}
                .email-container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
                }}
                .header {{
                    background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
                    padding: 40px 30px;
                    text-align: center;
                    position: relative;
                    overflow: hidden;
                }}
                .logo-container {{
                    position: relative;
                    z-index: 2;
                    margin-bottom: 20px;
                    text-align: center;
                }}
                .logo-image {{
                    width: 120px;
                    height: 120px;
                    border-radius: 50%;
                    box-shadow: 0 8px 24px rgba(255, 193, 7, 0.4), 0 4px 12px rgba(0, 0, 0, 0.3);
                    margin-bottom: 20px;
                    display: inline-block;
                    border: 3px solid #FFC107;
                }}
                .header h1 {{
                    color: #ffffff;
                    font-size: 24px;
                    font-weight: 700;
                    margin: 0;
                    position: relative;
                    z-index: 2;
                    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
                }}
                .content {{
                    padding: 40px 30px;
                    background-color: #ffffff;
                }}
                .greeting {{
                    font-size: 18px;
                    font-weight: 600;
                    color: #000000;
                    margin-bottom: 15px;
                }}
                .response-content {{
                    background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                    border: 2px solid #FFC107;
                    border-radius: 16px;
                    padding: 25px;
                    margin: 30px 0;
                    position: relative;
                    overflow: hidden;
                }}
                .response-content::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: linear-gradient(90deg, #FFC107 0%, #FFD54F 50%, #FFC107 100%);
                }}
                .response-content h3 {{
                    color: #000000;
                    font-size: 16px;
                    font-weight: 700;
                    margin-bottom: 15px;
                }}
                .contact-section {{
                    background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
                    border-radius: 16px;
                    padding: 25px;
                    margin: 30px 0;
                    text-align: center;
                }}
                .contact-section h3 {{
                    color: #FFC107;
                    font-size: 18px;
                    font-weight: 700;
                    margin-bottom: 15px;
                }}
                .contact-section p {{
                    color: #cccccc;
                    margin-bottom: 20px;
                }}
                .contact-buttons {{
                    display: flex;
                    gap: 15px;
                    justify-content: center;
                    flex-wrap: wrap;
                }}
                .contact-btn {{
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    padding: 12px 20px;
                    background: linear-gradient(135deg, #FFC107 0%, #FFD54F 100%);
                    color: #000000;
                    text-decoration: none;
                    border-radius: 25px;
                    font-weight: 600;
                    transition: transform 0.2s ease;
                    box-shadow: 0 4px 12px rgba(255, 193, 7, 0.3);
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 30px;
                    text-align: center;
                    border-top: 1px solid #e9ecef;
                }}
                .footer-brand {{
                    color: #000000;
                    font-weight: 700;
                    font-size: 16px;
                    margin-bottom: 8px;
                }}
                .footer-tagline {{
                    color: #6c757d;
                    font-size: 14px;
                    margin-bottom: 15px;
                }}
                .footer-disclaimer {{
                    color: #adb5bd;
                    font-size: 12px;
                    line-height: 1.5;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <div class="logo-container">
                        <img src="https://pablospizza.web.app/assets/logo-nqn6pSjR.png" alt="Pablo's Pizza" class="logo-image">
                    </div>
                    <h1>Respuesta a tu consulta</h1>
                </div>

                <div class="content">
                    <div class="greeting">¡Hola {contact_data.get('name', 'Cliente')}!</div>

                    <p>Gracias por contactarnos. Hemos recibido tu mensaje y queremos responderte personalmente:</p>

                    <div class="response-content">
                        <h3>📧 Nuestra respuesta:</h3>
                        <p style="line-height: 1.7; font-size: 16px; color: #2c2c2c;">{response_message}</p>
                    </div>

                    <div style="background-color: rgba(255, 215, 0, 0.1); border-radius: 12px; padding: 20px; margin: 20px 0;">
                        <h4 style="color: #000000; margin-bottom: 10px;">📝 Tu consulta original:</h4>
                        <p style="margin-bottom: 5px;"><strong>Asunto:</strong> {contact_data.get('subject', 'No especificado')}</p>
                        <p style="margin-bottom: 0;"><strong>Mensaje:</strong> {contact_data.get('message', 'No especificado')}</p>
                    </div>

                    <div class="contact-section">
                        <h3>📞 ¿Necesitas más información?</h3>
                        <p>Estamos aquí para ayudarte con cualquier consulta adicional.</p>
                        <div class="contact-buttons">
                            <a href="https://wa.me/56989424566" class="contact-btn">
                                📱 WhatsApp: +56 9 8942 4566
                            </a>
                            <a href="mailto:pablospizza.cl@gmail.com" class="contact-btn">
                                ✉️ pablospizza.cl@gmail.com
                            </a>
                        </div>
                    </div>

                    <div style="text-align: center; margin: 30px 0; padding: 25px; background: linear-gradient(135deg, #FFF3C4 0%, #FFECB3 100%); border-radius: 16px; border: 1px solid #FFC107;">
                        <h3 style="color: #000000; margin-bottom: 15px;">🍕 ¿Listo para agendar tu evento?</h3>
                        <p style="margin-bottom: 20px;">Contáctanos para obtener una cotización personalizada y crear recuerdos inolvidables.</p>
                        <a href="https://pablospizza.web.app/agendar" style="display: inline-block; background: linear-gradient(135deg, #FFD700 0%, #CBA900 100%); color: #000; padding: 12px 30px; text-decoration: none; border-radius: 25px; font-weight: 700; box-shadow: 0 4px 12px rgba(255, 193, 7, 0.3);">
                            Agendar Mi Evento
                        </a>
                    </div>
                </div>

                <div class="footer">
                    <div class="footer-brand">Pablo's Pizza</div>
                    <div class="footer-tagline">Creando momentos deliciosos y memorables</div>
                    <div class="footer-disclaimer">
                        Esta es una respuesta personalizada a tu consulta. Para más información, utiliza nuestros canales de contacto oficiales.
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = email_from
        msg['To'] = contact_data.get('email')
        msg['Subject'] = f"Re: {contact_data.get('subject', 'Tu consulta')} - Pablo's Pizza"

        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_username, email_password)
        text = msg.as_string()
        server.sendmail(email_from, contact_data.get('email'), text)
        server.quit()

        print(f"✅ Response email sent successfully to: {contact_data.get('email')}")
        return True

    except Exception as e:
        print(f"❌ Error sending response email: {e}")
        return False

@app.route('/api/contacts/<contact_id>/respond', methods=['POST', 'OPTIONS'])
def respond_to_contact(contact_id):
    """Send response to contact via email or WhatsApp"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response

    try:
        print(f"📧 Sending response to contact: {contact_id}")
        data = request.get_json()
        if not data:
            response = jsonify({"error": "No data provided"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400

        required_fields = ['response_message', 'response_method']
        for field in required_fields:
            if field not in data:
                response = jsonify({"error": f"Missing required field: {field}"})
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response, 400

        db = get_db()
        contact_ref = db.collection("contacts").document(contact_id)
        contact_doc = contact_ref.get()

        if not contact_doc.exists:
            response = jsonify({"error": "Contact not found"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 404

        contact_data = contact_doc.to_dict()
        response_method = data['response_method']
        response_message = data['response_message']
        response_success = False

        # Send response based on method
        if response_method == 'email':
            response_success = send_contact_response_email(contact_data, response_message)
            if not response_success:
                response = jsonify({"error": "Failed to send email response. Please check email configuration."})
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response, 500

        elif response_method == 'whatsapp':
            # WhatsApp response implementation
            phone = contact_data.get('phone')
            if not phone:
                response = jsonify({"error": "No phone number available for WhatsApp response"})
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response, 400

            try:
                # Format WhatsApp message
                whatsapp_message = f"""🍕 *Pablo's Pizza - Respuesta a tu consulta*

Hola {contact_data.get('name', 'Cliente')},

Gracias por tu mensaje sobre: *{contact_data.get('subject', 'Consulta general')}*

*Nuestra respuesta:*
{response_message}

Si tienes más preguntas, no dudes en contactarnos.

¡Saludos cordiales del equipo Pablo's Pizza! 🍕"""

                # Send WhatsApp using existing function
                whatsapp_sent = asyncio.run(send_whatsapp_notification(
                    phone,
                    whatsapp_message,
                    "contact_response"
                ))

                if whatsapp_sent:
                    print(f"✅ WhatsApp response sent successfully to: {phone}")
                    response_success = True
                else:
                    print(f"❌ Failed to send WhatsApp response to: {phone}")
                    response = jsonify({"error": "Failed to send WhatsApp response"})
                    response.headers.add('Access-Control-Allow-Origin', '*')
                    return response, 500

            except Exception as whatsapp_error:
                print(f"❌ WhatsApp error: {whatsapp_error}")
                response = jsonify({"error": f"WhatsApp error: {str(whatsapp_error)}"})
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response, 500

        else:
            response = jsonify({"error": "Invalid response method. Use 'email' or 'whatsapp'"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400

        # Update contact as resolved with response info
        update_data = {
            "status": "resolved",
            "response_sent": True,
            "response_message": response_message,
            "response_method": response_method,
            "resolved_at": datetime.now(),
            "updated_at": datetime.now(),
            "notes": data.get('notes', '')
        }

        contact_ref.update(update_data)

        # Save response record to database
        try:
            response_record = {
                "contact_id": contact_id,
                "response_message": response_message,
                "response_method": response_method,
                "sent_at": datetime.now(),
                "status": "sent" if response_success else "failed"
            }
            db.collection("contact_responses").add(response_record)
            print(f"📝 Response record saved to database")
        except Exception as record_error:
            print(f"⚠️ Failed to save response record: {record_error}")

        print(f"✅ Response sent via {response_method} to contact: {contact_id}")
        response_data = {
            "message": f"Response sent via {response_method}",
            "contact_id": contact_id,
            "response_method": response_method,
            "success": response_success
        }

        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200

    except Exception as e:
        print(f"❌ Error sending response: {e}")
        import traceback
        traceback.print_exc()
        response = jsonify({"error": str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500


# Update booking status
@app.route('/api/bookings/<booking_id>', methods=['PUT'])
def update_booking(booking_id):
    """Update booking status and other fields"""
    try:
        print(f"UPDATE_BOOKING INICIADO para ID: {booking_id}")
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        db = get_db()
        doc_ref = db.collection("bookings").document(booking_id)
        doc = doc_ref.get()

        if not doc.exists:
            return jsonify({"error": "Booking not found"}), 404

        # Get current booking data
        current_booking = doc.to_dict()
        print(f"Estado actual: {current_booking.get('status')} -> Nuevo estado: {data.get('status')}")

        # Update fields
        update_data = {}
        if 'status' in data:
            update_data['status'] = data['status']
            print(f"Actualizando status a: {data['status']}")

        # Add other updatable fields as needed
        updatable_fields = ['status', 'notes', 'confirmed_price', 'confirmed_date', 'confirmed_time', 'event_cost', 'event_profit', 'estimated_price', 'client_name', 'client_email', 'client_phone', 'participants', 'event_date', 'event_time', 'service_type', 'location', 'special_requests', 'expenses', 'pizzeros_participants', 'party_participants']
        for field in updatable_fields:
            if field in data:
                update_data[field] = data[field]
                print(f"Actualizando campo {field}: {data[field]}")

        # Add update timestamp
        update_data['updated_at'] = datetime.now()

        # Update in Firestore
        doc_ref.update(update_data)
        print(f"BOOKING ACTUALIZADO EN FIRESTORE: {booking_id}")

        # Get updated booking data
        updated_doc = doc_ref.get()
        updated_booking = updated_doc.to_dict()
        updated_booking['id'] = updated_doc.id

        # Send email notification ONLY if status CHANGED from something else to 'confirmed'
        if ('status' in data and
            data['status'] == 'confirmed' and
            current_booking.get('status') != 'confirmed'):

            client_email = updated_booking.get('client_email')
            if client_email:
                print(f"Estado cambió de '{current_booking.get('status')}' a 'confirmed' - enviando email profesional a: {client_email}")

                email_sent = send_confirmation_email(updated_booking)

                if email_sent:
                    print(f"Email de confirmación HTML enviado exitosamente a {client_email}")
                else:
                    print(f"Error al enviar email de confirmación a {client_email}")
            else:
                print("No se pudo enviar email: no hay email del cliente")

            # Send WhatsApp notification to admin about confirmation
            try:
                admin_phone = os.getenv('ADMIN_WHATSAPP_NUMBER', '+56998960858')
                service_name = 'Pizzeros en Acción' if updated_booking.get('service_type') == 'workshop' else 'Pizza Party'

                # Format participants info based on new structure
                participants_info = ""
                if updated_booking.get('pizzeros_participants') and updated_booking.get('party_participants'):
                    participants_info = f"Pizzeros: {updated_booking['pizzeros_participants']}, Pizza Party: {updated_booking['party_participants']}"
                elif updated_booking.get('pizzeros_participants'):
                    participants_info = f"{updated_booking['pizzeros_participants']} niños"
                elif updated_booking.get('party_participants'):
                    participants_info = f"{updated_booking['party_participants']} personas"
                else:
                    participants_info = f"{updated_booking.get('participants', 'No especificado')}"

                admin_whatsapp_message = f"""✅ *Pablo's Pizza - EVENTO CONFIRMADO*

¡El evento ha sido confirmado!

👤 *Cliente:* {updated_booking.get('client_name', 'No especificado')}
📱 *Teléfono:* {updated_booking.get('client_phone', 'No especificado')}
📧 *Email:* {updated_booking.get('client_email', 'No especificado')}

🍕 *Servicio:* {service_name}
📅 *Fecha:* {updated_booking.get('event_date', 'No especificada')}
⏰ *Hora:* {updated_booking.get('event_time', 'No especificada')}
👥 *Participantes:* {participants_info}
📍 *Ubicación:* {updated_booking.get('location', 'No especificada')}
💰 *Precio:* ${updated_booking.get('estimated_price', 0):,.0f} CLP

🎉 *El cliente ya ha sido notificado por email.*

ID: {updated_booking.get('id', 'N/A')}"""

                print(f"Enviando WhatsApp de confirmación al admin: {admin_phone}")
                admin_whatsapp_sent = asyncio.run(send_whatsapp_with_template_fallback(
                    admin_phone,
                    admin_whatsapp_message,
                    "booking_confirmed_admin_alert",
                    updated_booking
                ))

                if admin_whatsapp_sent:
                    print(f"WhatsApp de confirmación enviado exitosamente al admin")
                else:
                    print(f"Error al enviar WhatsApp de confirmación al admin")

            except Exception as e:
                print(f"Error enviando WhatsApp de confirmación al admin: {e}")
                # No fallar la actualización del booking si falla la notificación
        elif 'status' in data and data['status'] == 'confirmed' and current_booking.get('status') == 'confirmed':
            print(f"Status sigue siendo 'confirmed' - NO enviando notificación duplicada")

        # Create event automatically ONLY when booking CHANGES to 'completed' and has costs
        if ('status' in data and
            data['status'] == 'completed' and
            current_booking.get('status') != 'completed' and
            ('event_cost' in data or 'event_profit' in data)):
            try:
                create_event_from_booking(updated_booking)
                print(f"Evento creado automáticamente para booking {booking_id} - status cambió a 'completed'")
            except Exception as e:
                print(f"Error creando evento automático: {e}")
                # No fallar la actualización del booking si falla la creación del evento
        elif 'status' in data and data['status'] == 'completed' and current_booking.get('status') == 'completed':
            print(f"Status sigue siendo 'completed' - NO creando evento duplicado")

        return jsonify(updated_booking), 200

    except Exception as e:
        print(f"Error updating booking {booking_id}: {e}")
        return jsonify({"error": str(e)}), 500

# Delete booking endpoint
@app.route('/api/bookings/<booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    """Delete/Cancel booking"""
    try:
        print(f"DELETE_BOOKING INICIADO para ID: {booking_id}")

        db = get_db()
        doc_ref = db.collection("bookings").document(booking_id)
        doc = doc_ref.get()

        if not doc.exists:
            return jsonify({"error": "Booking not found"}), 404

        # Instead of actually deleting, update status to 'cancelled'
        update_data = {
            'status': 'cancelled',
            'cancelled_at': datetime.now(),
            'updated_at': datetime.now()
        }

        doc_ref.update(update_data)
        print(f"BOOKING CANCELADO EN FIRESTORE: {booking_id}")

        return jsonify({"message": "Booking cancelled successfully", "id": booking_id}), 200

    except Exception as e:
        print(f"Error deleting booking {booking_id}: {e}")
        return jsonify({"error": str(e)}), 500

# Firebase Functions entry point using new SDK
@https_fn.on_request()
def main(req: https_fn.Request) -> https_fn.Response:
    """Firebase Function entry point - Production ready"""
    from werkzeug.test import Client

    # Create a test client to handle the request properly
    client = Client(app)

    try:
        # Convert Firebase request to Flask-compatible format
        response = client.open(
            path=req.path,
            method=req.method,
            headers=list(req.headers.items()),
            data=req.get_data(),
            query_string=req.query_string
        )

        # Return properly formatted response
        return https_fn.Response(
            response.get_data(),
            status=response.status_code,
            headers=dict(response.headers)
        )

    except Exception as e:
        print(f"Error in main function: {e}")
        return https_fn.Response(
            '{"error": "Internal server error"}',
            status=500,
            headers={'Content-Type': 'application/json'}
        )

# ===================== INVENTORY ENDPOINTS =====================

@app.route('/api/inventory/', methods=['GET'])
def get_inventory():
    """Get all inventory items with optional filters"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        category = request.args.get('category')
        needs_restock = request.args.get('needs_restock')

        query = db.collection('inventory').order_by('name')

        if category:
            query = query.where('category', '==', category)

        if needs_restock is not None:
            query = query.where('needs_restock', '==', needs_restock.lower() == 'true')

        docs = query.stream()
        items = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            items.append(data)

        return jsonify(items)
    except Exception as e:
        print(f"Error getting inventory: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/', methods=['POST'])
def create_inventory_item():
    """Create new inventory item"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        data = request.get_json()

        # Generate unique ID
        item_id = str(uuid.uuid4())

        # Prepare item data
        item_data = {
            'id': item_id,
            'name': data['name'],
            'product_type': data.get('product_type', 'raw_material'),
            'category': data['category'],
            'current_stock': float(data['current_stock']),
            'min_stock': float(data['min_stock']),
            'max_stock': float(data['max_stock']),
            'unit': data['unit'],
            'cost_per_unit': float(data['cost_per_unit']),
            'supplier': data.get('supplier', ''),
            'notes': data.get('notes', ''),
            'batch_size': float(data['batch_size']) if data.get('batch_size') else None,
            'shelf_life_days': int(data['shelf_life_days']) if data.get('shelf_life_days') else None,
            'last_updated': datetime.now(),
            'needs_restock': float(data['current_stock']) <= float(data['min_stock'])
        }

        # Save to Firestore
        db.collection('inventory').document(item_id).set(item_data)

        return jsonify(item_data), 201
    except Exception as e:
        print(f"Error creating inventory item: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/<item_id>', methods=['GET'])
def get_inventory_item(item_id):
    """Get specific inventory item"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        doc = db.collection('inventory').document(item_id).get()

        if not doc.exists:
            return jsonify({'error': 'Item not found'}), 404

        data = doc.to_dict()
        data['id'] = doc.id
        return jsonify(data)
    except Exception as e:
        print(f"Error getting inventory item: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/<item_id>', methods=['PUT'])
def update_inventory_item(item_id):
    """Update inventory item"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        data = request.get_json()

        # Get current item
        item_ref = db.collection('inventory').document(item_id)
        doc = item_ref.get()

        if not doc.exists:
            return jsonify({'error': 'Item not found'}), 404

        # Prepare update data
        update_data = {}
        if 'name' in data:
            update_data['name'] = data['name']
        if 'product_type' in data:
            update_data['product_type'] = data['product_type']
        if 'category' in data:
            update_data['category'] = data['category']
        if 'current_stock' in data:
            update_data['current_stock'] = float(data['current_stock'])
        if 'min_stock' in data:
            update_data['min_stock'] = float(data['min_stock'])
        if 'max_stock' in data:
            update_data['max_stock'] = float(data['max_stock'])
        if 'unit' in data:
            update_data['unit'] = data['unit']
        if 'cost_per_unit' in data:
            update_data['cost_per_unit'] = float(data['cost_per_unit'])
        if 'supplier' in data:
            update_data['supplier'] = data['supplier']
        if 'notes' in data:
            update_data['notes'] = data['notes']
        if 'batch_size' in data:
            update_data['batch_size'] = float(data['batch_size']) if data['batch_size'] else None
        if 'shelf_life_days' in data:
            update_data['shelf_life_days'] = int(data['shelf_life_days']) if data['shelf_life_days'] else None

        update_data['last_updated'] = datetime.now()

        # Update needs_restock if stock values changed
        if 'current_stock' in update_data or 'min_stock' in update_data:
            current_data = doc.to_dict()
            new_current = update_data.get('current_stock', current_data['current_stock'])
            new_min = update_data.get('min_stock', current_data['min_stock'])
            update_data['needs_restock'] = new_current <= new_min

        # Update document
        item_ref.update(update_data)

        # Return updated data
        updated_doc = item_ref.get()
        result = updated_doc.to_dict()
        result['id'] = updated_doc.id
        return jsonify(result)
    except Exception as e:
        print(f"Error updating inventory item: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/<item_id>', methods=['DELETE'])
def delete_inventory_item(item_id):
    """Delete inventory item"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        item_ref = db.collection('inventory').document(item_id)
        doc = item_ref.get()

        if not doc.exists:
            return jsonify({'error': 'Item not found'}), 404

        item_ref.delete()
        return jsonify({'message': 'Item deleted successfully'})
    except Exception as e:
        print(f"Error deleting inventory item: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/categories', methods=['GET'])
def get_inventory_categories():
    """Get all inventory categories"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        docs = db.collection('inventory').stream()
        categories = set()

        for doc in docs:
            data = doc.to_dict()
            categories.add(data.get('category', ''))

        return jsonify({'categories': sorted(list(categories))})
    except Exception as e:
        print(f"Error getting categories: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/alerts', methods=['GET'])
def get_inventory_alerts():
    """Get items that need restocking"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        docs = db.collection('inventory').where('needs_restock', '==', True).order_by('current_stock').stream()

        alerts = []
        for doc in docs:
            data = doc.to_dict()
            alerts.append({
                'id': doc.id,
                'name': data['name'],
                'category': data['category'],
                'current_stock': data['current_stock'],
                'min_stock': data['min_stock'],
                'unit': data['unit'],
                'priority': 'high' if data['current_stock'] == 0 else 'medium'
            })

        return jsonify({'alerts': alerts, 'total': len(alerts)})
    except Exception as e:
        print(f"Error getting inventory alerts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/<item_id>/stock', methods=['PUT'])
def update_inventory_stock(item_id):
    """Update stock of an inventory item"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        data = request.get_json()
        new_stock = data.get('new_stock')
        operation = data.get('operation', 'set')  # 'set', 'add', 'subtract'

        item_ref = db.collection('inventory').document(item_id)
        doc = item_ref.get()

        if not doc.exists:
            return jsonify({'error': 'Item not found'}), 404

        current_data = doc.to_dict()
        current_stock = current_data['current_stock']
        min_stock = current_data['min_stock']

        if operation == 'set':
            final_stock = float(new_stock)
        elif operation == 'add':
            final_stock = current_stock + float(new_stock)
        elif operation == 'subtract':
            final_stock = max(0, current_stock - float(new_stock))
        else:
            return jsonify({'error': 'Invalid operation'}), 400

        needs_restock = final_stock <= min_stock

        item_ref.update({
            'current_stock': final_stock,
            'needs_restock': needs_restock,
            'last_updated': datetime.now()
        })

        return jsonify({
            'message': 'Stock updated successfully',
            'new_stock': final_stock,
            'needs_restock': needs_restock
        })
    except Exception as e:
        print(f"Error updating stock: {e}")
        return jsonify({'error': str(e)}), 500

# ===================== RECIPES ENDPOINTS =====================

@app.route('/api/recipes/', methods=['GET'])
def get_recipes():
    """Get all recipes"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        docs = db.collection('recipes').order_by('name').stream()
        recipes = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            recipes.append(data)

        return jsonify(recipes)
    except Exception as e:
        print(f"Error getting recipes: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes/', methods=['POST'])
def create_recipe():
    """Create new recipe with automatic cost calculation"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        data = request.get_json()
        recipe_id = str(uuid.uuid4())

        # Calculate recipe cost
        total_cost = 0.0
        for ingredient in data['ingredients']:
            # Get current cost from inventory
            inventory_doc = db.collection('inventory').document(ingredient['item_id']).get()
            if inventory_doc.exists:
                inventory_data = inventory_doc.to_dict()
                cost_per_unit = inventory_data.get('cost_per_unit', 0)
                ingredient['cost_per_unit'] = cost_per_unit
                total_cost += cost_per_unit * ingredient['quantity']

        cost_per_unit_output = total_cost / data['output_quantity'] if data['output_quantity'] > 0 else 0

        recipe_data = {
            'id': recipe_id,
            'name': data['name'],
            'description': data.get('description', ''),
            'output_product_type': data['output_product_type'],
            'output_category': data['output_category'],
            'output_quantity': float(data['output_quantity']),
            'output_unit': data['output_unit'],
            'prep_time_minutes': int(data['prep_time_minutes']) if data.get('prep_time_minutes') else None,
            'instructions': data.get('instructions', ''),
            'ingredients': data['ingredients'],
            'cost_per_batch': total_cost,
            'cost_per_unit': cost_per_unit_output,
            'created_at': datetime.now(),
            'last_updated': datetime.now()
        }

        db.collection('recipes').document(recipe_id).set(recipe_data)
        return jsonify(recipe_data), 201
    except Exception as e:
        print(f"Error creating recipe: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes/<recipe_id>', methods=['GET'])
def get_recipe(recipe_id):
    """Get specific recipe"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        doc = db.collection('recipes').document(recipe_id).get()
        if not doc.exists:
            return jsonify({'error': 'Recipe not found'}), 404

        data = doc.to_dict()
        data['id'] = doc.id
        return jsonify(data)
    except Exception as e:
        print(f"Error getting recipe: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes/<recipe_id>', methods=['PUT'])
def update_recipe(recipe_id):
    """Update recipe and recalculate costs"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        data = request.get_json()
        recipe_ref = db.collection('recipes').document(recipe_id)
        doc = recipe_ref.get()

        if not doc.exists:
            return jsonify({'error': 'Recipe not found'}), 404

        update_data = {}
        for field in ['name', 'description', 'output_product_type', 'output_category',
                     'output_quantity', 'output_unit', 'prep_time_minutes', 'instructions']:
            if field in data:
                update_data[field] = data[field]

        # Recalculate costs if ingredients changed
        if 'ingredients' in data:
            total_cost = 0.0
            for ingredient in data['ingredients']:
                inventory_doc = db.collection('inventory').document(ingredient['item_id']).get()
                if inventory_doc.exists:
                    inventory_data = inventory_doc.to_dict()
                    cost_per_unit = inventory_data.get('cost_per_unit', 0)
                    ingredient['cost_per_unit'] = cost_per_unit
                    total_cost += cost_per_unit * ingredient['quantity']

            output_quantity = data.get('output_quantity', doc.to_dict().get('output_quantity', 1))
            cost_per_unit_output = total_cost / output_quantity if output_quantity > 0 else 0

            update_data['ingredients'] = data['ingredients']
            update_data['cost_per_batch'] = total_cost
            update_data['cost_per_unit'] = cost_per_unit_output

        update_data['last_updated'] = datetime.now()
        recipe_ref.update(update_data)

        # Return updated recipe
        updated_doc = recipe_ref.get()
        result = updated_doc.to_dict()
        result['id'] = updated_doc.id
        return jsonify(result)
    except Exception as e:
        print(f"Error updating recipe: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes/<recipe_id>', methods=['DELETE'])
def delete_recipe(recipe_id):
    """Delete recipe"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        recipe_ref = db.collection('recipes').document(recipe_id)
        doc = recipe_ref.get()

        if not doc.exists:
            return jsonify({'error': 'Recipe not found'}), 404

        recipe_ref.delete()
        return jsonify({'message': 'Recipe deleted successfully'})
    except Exception as e:
        print(f"Error deleting recipe: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes/<recipe_id>/calculate-cost', methods=['POST'])
def recalculate_recipe_cost(recipe_id):
    """Recalculate recipe cost based on current inventory prices"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        recipe_ref = db.collection('recipes').document(recipe_id)
        doc = recipe_ref.get()

        if not doc.exists:
            return jsonify({'error': 'Recipe not found'}), 404

        recipe_data = doc.to_dict()
        total_cost = 0.0
        updated_ingredients = []

        for ingredient in recipe_data['ingredients']:
            inventory_doc = db.collection('inventory').document(ingredient['item_id']).get()
            if inventory_doc.exists:
                inventory_data = inventory_doc.to_dict()
                current_cost = inventory_data.get('cost_per_unit', 0)
                ingredient['cost_per_unit'] = current_cost
                total_cost += current_cost * ingredient['quantity']
            updated_ingredients.append(ingredient)

        cost_per_unit_output = total_cost / recipe_data['output_quantity'] if recipe_data['output_quantity'] > 0 else 0

        # Update recipe with new costs
        recipe_ref.update({
            'ingredients': updated_ingredients,
            'cost_per_batch': total_cost,
            'cost_per_unit': cost_per_unit_output,
            'last_updated': datetime.now()
        })

        return jsonify({
            'message': 'Recipe cost recalculated successfully',
            'cost_per_batch': total_cost,
            'cost_per_unit': cost_per_unit_output
        })
    except Exception as e:
        print(f"Error recalculating recipe cost: {e}")
        return jsonify({'error': str(e)}), 500

# ===================== PRODUCTION BATCHES ENDPOINTS =====================

@app.route('/api/production-batches/', methods=['GET'])
def get_production_batches():
    """Get all production batches"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        docs = db.collection('production_batches').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        batches = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            batches.append(data)

        return jsonify(batches)
    except Exception as e:
        print(f"Error getting production batches: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/production-batches/', methods=['POST'])
def create_production_batch():
    """Create new production batch"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        data = request.get_json()
        batch_id = str(uuid.uuid4())

        # Get recipe details
        recipe_doc = db.collection('recipes').document(data['recipe_id']).get()
        if not recipe_doc.exists:
            return jsonify({'error': 'Recipe not found'}), 404

        recipe_data = recipe_doc.to_dict()

        # Calculate batch details
        quantity_to_produce = float(data['quantity_to_produce'])
        total_cost = recipe_data['cost_per_batch'] * quantity_to_produce
        output_quantity = recipe_data['output_quantity'] * quantity_to_produce

        # Prepare ingredients list with quantities scaled
        ingredients_consumed = []
        for ingredient in recipe_data['ingredients']:
            scaled_ingredient = {
                'item_id': ingredient['item_id'],
                'item_name': ingredient.get('item_name', ''),
                'quantity': ingredient['quantity'] * quantity_to_produce,
                'unit': ingredient['unit'],
                'cost_per_unit': ingredient.get('cost_per_unit', 0),
                'total_cost': ingredient.get('cost_per_unit', 0) * ingredient['quantity'] * quantity_to_produce
            }
            ingredients_consumed.append(scaled_ingredient)

        batch_data = {
            'id': batch_id,
            'recipe_id': data['recipe_id'],
            'recipe_name': recipe_data['name'],
            'quantity_to_produce': quantity_to_produce,
            'total_cost': total_cost,
            'output_quantity': output_quantity,
            'output_unit': recipe_data['output_unit'],
            'status': 'pending',
            'notes': data.get('notes', ''),
            'created_at': datetime.now(),
            'completed_at': None,
            'ingredients_consumed': ingredients_consumed
        }

        db.collection('production_batches').document(batch_id).set(batch_data)
        return jsonify(batch_data), 201
    except Exception as e:
        print(f"Error creating production batch: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/production-batches/<batch_id>/complete', methods=['POST'])
def complete_production_batch(batch_id):
    """Complete production batch and update inventory"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        # Get batch details
        batch_ref = db.collection('production_batches').document(batch_id)
        batch_doc = batch_ref.get()

        if not batch_doc.exists:
            return jsonify({'error': 'Production batch not found'}), 404

        batch_data = batch_doc.to_dict()

        if batch_data['status'] == 'completed':
            return jsonify({'error': 'Batch already completed'}), 400

        # Get recipe to create output product
        recipe_doc = db.collection('recipes').document(batch_data['recipe_id']).get()
        if not recipe_doc.exists:
            return jsonify({'error': 'Recipe not found'}), 404

        recipe_data = recipe_doc.to_dict()

        # 1. Reduce raw materials from inventory
        for ingredient in batch_data['ingredients_consumed']:
            item_ref = db.collection('inventory').document(ingredient['item_id'])
            item_doc = item_ref.get()

            if item_doc.exists:
                item_data = item_doc.to_dict()
                new_stock = max(0, item_data['current_stock'] - ingredient['quantity'])
                needs_restock = new_stock <= item_data['min_stock']

                item_ref.update({
                    'current_stock': new_stock,
                    'needs_restock': needs_restock,
                    'last_updated': datetime.now()
                })

        # 2. Create or update intermediate product in inventory
        output_product_name = f"{recipe_data['name']} (Producido)"

        # Check if intermediate product already exists
        existing_products = db.collection('inventory').where('name', '==', output_product_name).where('product_type', '==', recipe_data['output_product_type']).stream()

        existing_product = None
        for doc in existing_products:
            existing_product = doc
            break

        if existing_product:
            # Update existing product
            existing_data = existing_product.to_dict()
            new_stock = existing_data['current_stock'] + batch_data['output_quantity']

            existing_product.reference.update({
                'current_stock': new_stock,
                'last_updated': datetime.now(),
                'needs_restock': new_stock <= existing_data['min_stock']
            })
        else:
            # Create new intermediate product
            product_id = str(uuid.uuid4())
            product_data = {
                'id': product_id,
                'name': output_product_name,
                'product_type': recipe_data['output_product_type'],
                'category': recipe_data['output_category'],
                'current_stock': batch_data['output_quantity'],
                'min_stock': batch_data['output_quantity'] * 0.2,  # 20% of production as minimum
                'max_stock': batch_data['output_quantity'] * 5,    # 5x production as maximum
                'unit': recipe_data['output_unit'],
                'cost_per_unit': recipe_data['cost_per_unit'],
                'supplier': 'Produccion Interna',
                'notes': f'Producto intermedio generado por receta: {recipe_data["name"]}',
                'batch_size': batch_data['output_quantity'],
                'shelf_life_days': 7,  # Default 7 days for intermediate products
                'last_updated': datetime.now(),
                'needs_restock': False
            }

            db.collection('inventory').document(product_id).set(product_data)

        # 3. Mark batch as completed
        batch_ref.update({
            'status': 'completed',
            'completed_at': datetime.now()
        })

        return jsonify({
            'message': 'Production batch completed successfully',
            'output_quantity': batch_data['output_quantity'],
            'output_unit': batch_data['output_unit']
        })

    except Exception as e:
        print(f"Error completing production batch: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/production-batches/<batch_id>/status', methods=['PUT'])
def update_production_batch_status(batch_id):
    """Update production batch status"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        data = request.get_json()
        new_status = data.get('status')

        if new_status not in ['pending', 'in_progress', 'completed', 'cancelled']:
            return jsonify({'error': 'Invalid status'}), 400

        batch_ref = db.collection('production_batches').document(batch_id)
        batch_doc = batch_ref.get()

        if not batch_doc.exists:
            return jsonify({'error': 'Production batch not found'}), 404

        # Update the status
        update_data = {
            'status': new_status,
            'updated_at': datetime.now()
        }

        # If completing, add completion time
        if new_status == 'completed':
            update_data['completed_at'] = datetime.now()

        batch_ref.update(update_data)

        return jsonify({'message': f'Batch status updated to {new_status}'})

    except Exception as e:
        print(f"Error updating production batch status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/production-batches/<batch_id>', methods=['DELETE'])
def cancel_production_batch(batch_id):
    """Cancel production batch"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        batch_ref = db.collection('production_batches').document(batch_id)
        batch_doc = batch_ref.get()

        if not batch_doc.exists:
            return jsonify({'error': 'Production batch not found'}), 404

        batch_data = batch_doc.to_dict()

        if batch_data['status'] == 'completed':
            return jsonify({'error': 'Cannot cancel completed batch'}), 400

        # Mark as cancelled or delete
        batch_ref.update({
            'status': 'cancelled',
            'completed_at': datetime.now()
        })

        return jsonify({'message': 'Production batch cancelled successfully'})
    except Exception as e:
        print(f"Error cancelling production batch: {e}")
        return jsonify({'error': str(e)}), 500

# Local development server
if __name__ == '__main__':
    print("Starting Pablo's Pizza Backend in LOCAL DEVELOPMENT mode...")
    print(f"Server will be available at: http://localhost:8000")
    print("Available endpoints:")
    print("   - GET /api/health - Health check")
    print("   - POST /api/bookings/ - Create booking")
    print("   - GET /api/bookings/ - List bookings")
    print("   - GET /api/events/ - List events")
    print("   - GET /api/gallery/ - Gallery images")
    print("Use Ctrl+C to stop the server")
    
    # Run Flask development server
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=True,
        threaded=True
    )