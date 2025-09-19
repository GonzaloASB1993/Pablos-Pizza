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

def send_admin_email_notification(booking_data: dict) -> bool:
    """Send email notification to admin about new booking"""
    try:
        service_name = 'Pizzeros en Acción' if booking_data.get('service_type') == 'workshop' else 'Pizza Party'

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
                is_local = os.path.exists(service_account_path) and os.getenv('ENVIRONMENT') != 'production'
                
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

def calculate_estimated_price(service_type: str, participants: int) -> float:
    """Calculate estimated price based on service type and participants"""
    print(f"[CALCULATE] Starting calculation: service_type='{service_type}', participants={participants}")

    # Get pricing from environment variables
    default_workshop_price = int(os.getenv('DEFAULT_WORKSHOP_PRICE', 13500))
    default_pizza_party_price = int(os.getenv('DEFAULT_PIZZA_PARTY_PRICE', 11990))

    if service_type == "workshop":
        # Pizzeros en Acción pricing logic
        if participants <= 15:
            unit_final = default_workshop_price
        elif participants <= 25:
            unit_final = round(default_workshop_price * 0.9)  # 10% discount
        else:
            unit_final = round(default_workshop_price * 0.85)  # 15% discount
        total = unit_final * participants

    elif service_type == "pizza_party":
        # Pizza Party pricing logic
        unit_base = default_pizza_party_price
        if participants >= 20:
            unit_final = round(unit_base * 0.9)  # 10% discount for 20+
        else:
            unit_final = unit_base
        total = unit_final * participants

    else:
        # Fallback for other service types
        total = 10000 * participants

    result = round(total, 2)
    print(f"[CALCULATE] Final result: {result}")
    return result

def create_event_from_booking(booking_data: dict) -> bool:
    """Create an event automatically when a booking is completed with costs"""
    try:
        print(f"Creando evento automáticamente para booking: {booking_data.get('id')}")
        
        # Generate event ID
        event_id = str(uuid.uuid4())
        
        # Determine service name for title
        service_name = 'Pizzeros en Acción' if booking_data.get('service_type') == 'workshop' else 'Pizza Party'
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
        print("CREATE_BOOKING INICIADO - PRODUCTION VERSION")
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

        # Calculate estimated price
        estimated_price = calculate_estimated_price(
            data.get('service_type'),
            data.get('participants', 0)
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
            admin_phone = os.getenv('ADMIN_WHATSAPP_NUMBER', '+56989424566')
            service_name = 'Pizzeros en Acción' if booking_data.get('service_type') == 'workshop' else 'Pizza Party'

            admin_whatsapp_message = f"""🍕 *Pablo's Pizza - NUEVO AGENDAMIENTO*

¡Te acaban de agendar un evento!

👤 *Cliente:* {booking_data.get('client_name', 'No especificado')}
📱 *Teléfono:* {booking_data.get('client_phone', 'No especificado')}
📧 *Email:* {booking_data.get('client_email', 'No especificado')}

🍕 *Servicio:* {service_name}
📅 *Fecha:* {booking_data.get('event_date', 'No especificada')}
⏰ *Hora:* {booking_data.get('event_time', 'No especificada')}
👥 *Participantes:* {booking_data.get('participants', 'No especificado')}
📍 *Ubicación:* {booking_data.get('location', 'No especificada')}
💰 *Precio estimado:* ${booking_data.get('estimated_price', 0):,.0f} CLP

🔔 *Favor verificar en la plataforma para confirmar el evento.*

ID: {booking_data.get('id', 'N/A')}"""

            print(f"Enviando WhatsApp de nueva reserva al admin: {admin_phone}")
            admin_whatsapp_sent = asyncio.run(send_whatsapp_notification(
                admin_phone,
                admin_whatsapp_message,
                "new_booking_admin_alert"
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
            partner_phone = os.getenv('PARTNER_WHATSAPP_NUMBER', '+56961093818')
            service_name = 'Pizzeros en Acción' if booking_data.get('service_type') == 'workshop' else 'Pizza Party'

            partner_message = f"""🍕 *Pablo's Pizza - NUEVO AGENDAMIENTO*

¡Hola! Te informo que acabamos de recibir una nueva reserva:

👤 *Cliente:* {booking_data.get('client_name', 'No especificado')}
📱 *Teléfono:* {booking_data.get('client_phone', 'No especificado')}

🍕 *Servicio:* {service_name}
📅 *Fecha:* {booking_data.get('event_date', 'No especificada')}
⏰ *Hora:* {booking_data.get('event_time', 'No especificada')}
👥 *Participantes:* {booking_data.get('participants', 'No especificado')}
📍 *Ubicación:* {booking_data.get('location', 'No especificada')}
💰 *Precio estimado:* ${booking_data.get('estimated_price', 0):,.0f} CLP

¡Excelente! 🎉"""

            print(f"Enviando WhatsApp de nueva reserva al socio: {partner_phone}")
            whatsapp_sent = asyncio.run(send_whatsapp_notification(
                partner_phone,
                partner_message,
                "new_booking_partner_alert"
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
        updatable_fields = ['status', 'notes', 'confirmed_price', 'confirmed_date', 'confirmed_time', 'event_cost', 'event_profit']
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

        # Send email notification if status changed to confirmed
        if 'status' in data and data['status'] == 'confirmed':
            client_email = updated_booking.get('client_email')
            if client_email:
                print(f"Estado cambió a 'confirmed' - enviando email profesional a: {client_email}")

                email_sent = send_confirmation_email(updated_booking)

                if email_sent:
                    print(f"Email de confirmación HTML enviado exitosamente a {client_email}")
                else:
                    print(f"Error al enviar email de confirmación a {client_email}")
            else:
                print("No se pudo enviar email: no hay email del cliente")

        # Create event automatically when booking is completed with costs
        if ('status' in data and data['status'] == 'completed' and 
            ('event_cost' in data or 'event_profit' in data)):
            try:
                create_event_from_booking(updated_booking)
                print(f"Evento creado automáticamente para booking {booking_id}")
            except Exception as e:
                print(f"Error creando evento automático: {e}")
                # No fallar la actualización del booking si falla la creación del evento

        return jsonify(updated_booking), 200

    except Exception as e:
        print(f"Error updating booking {booking_id}: {e}")
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