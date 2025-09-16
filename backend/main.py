from firebase_functions import https_fn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Import after loading env variables
import firebase_admin
from firebase_admin import firestore
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
from decouple import config
import logging

# Initialize Flask app
app = Flask(__name__)

# Twilio WhatsApp Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_FROM = os.getenv('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None

def format_phone_number(phone: str) -> str:
    """Format phone number for WhatsApp"""
    phone = phone.strip()
    if not phone.startswith('+'):
        if phone.startswith('9'):
            phone = '+56' + phone
        else:
            phone = '+56' + phone
    return f"whatsapp:{phone}"

async def send_whatsapp_confirmation(booking_data: dict) -> bool:
    """Send WhatsApp confirmation when event is confirmed"""
    if not twilio_client:
        print("WhatsApp service not configured")
        return False

    try:
        service_name = 'Pizzeros en Acción' if booking_data['service_type'] == 'workshop' else 'Pizza Party'

        message_content = f"""🍕 *Pablo's Pizza*

¡Hola {booking_data['client_name']}!

✅ *Tu evento ha sido CONFIRMADO*

📋 *Detalles:*
🍕 Servicio: {service_name}
📅 Fecha: {booking_data['event_date'].strftime('%d/%m/%Y') if hasattr(booking_data['event_date'], 'strftime') else booking_data['event_date']}
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

        to_whatsapp = format_phone_number(booking_data['client_phone'])

        message = twilio_client.messages.create(
            body=message_content,
            from_=TWILIO_WHATSAPP_FROM,
            to=to_whatsapp
        )

        print(f"WhatsApp confirmation sent successfully to {booking_data['client_phone']}")
        return True

    except Exception as e:
        print(f"Error sending WhatsApp confirmation to {booking_data['client_phone']}: {str(e)}")
        return False

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

# CORS configuration - allow both Firebase hosting domains
allowed_origins = [
    'https://pablospizza.web.app',
    'https://pablospizza.firebaseapp.com',
    'http://localhost:5173',  # For development
    'http://localhost:3000'   # Alternative dev port
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
            # Initialize Firebase (will use service account in production)
            firebase_admin.initialize_app()
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
        msg['Subject'] = "✅ ¡Tu evento con Pablo's Pizza ha sido confirmado!"

        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

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
                "subject": "✅ ¡Tu evento con Pablo's Pizza ha sido confirmado!",
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
                "subject": "✅ ¡Tu evento con Pablo's Pizza ha sido confirmado!",
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
        
        # Parse event date if it's a string
        event_date = booking_data.get('event_date')
        if isinstance(event_date, str):
            try:
                from datetime import datetime
                event_date = datetime.strptime(event_date, '%Y-%m-%d').date()
            except:
                event_date = datetime.now().date()
        elif hasattr(event_date, 'date'):
            event_date = event_date.date()
        
        # Calculate profit if we have both estimated price and cost
        estimated_price = booking_data.get('estimated_price', 0)
        event_cost = booking_data.get('event_cost', 0)
        calculated_profit = estimated_price - event_cost if estimated_price and event_cost else 0
        
        # Use provided profit or calculated profit
        final_profit = booking_data.get('event_profit', calculated_profit)
        
        # Create event data (compatible with POST endpoint)
        event_data = {
            "title": event_title,
            "description": f"Evento realizado automáticamente desde agendamiento. Servicio: {service_name}",
            "event_date": booking_data.get('event_date'),  # Use the original event_date format
            "participants": booking_data.get('participants', 0),
            "final_price": estimated_price,
            "event_cost": event_cost,
            "profit": final_profit,
            "notes": f"Evento creado automáticamente. Cliente: {booking_data.get('client_name')}. Ubicación: {booking_data.get('location', 'No especificada')}. Costo: {event_cost}, Ganancia: {final_profit}",
            "status": "completed",
            "booking_id": booking_data.get('id')
        }
        
        # Use the internal POST endpoint to create the event
        # This ensures all validation and formatting is consistent
        from flask import current_app
        with current_app.test_request_context('/api/events/', json=event_data, method='POST'):
            try:
                # Import the create_event function and call it directly
                response = create_event()
                if response[1] == 201:  # Check if created successfully
                    print(f"Evento creado exitosamente via endpoint para booking {booking_data.get('id')}")
                    return True
                else:
                    print(f"Error en endpoint de eventos: {response}")
                    return False
            except Exception as e:
                print(f"Error llamando endpoint interno de eventos: {e}")
                return False
        
    except Exception as e:
        print(f"Error creando evento automático: {e}")
        return False

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Pablo's Pizza API - Production Ready",
        "environment": os.getenv('ENVIRONMENT', 'production'),
        "version": "2.0.0"
    })

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

        # Send WhatsApp notification to admin about new booking
        try:
            admin_phone = os.getenv('ADMIN_WHATSAPP_NUMBER', '+56989424566')
            service_name = 'Pizzeros en Acción' if booking_data.get('service_type') == 'workshop' else 'Pizza Party'

            admin_message = f"""🍕 *Pablo's Pizza - NUEVO AGENDAMIENTO*

¡Te acaban de agendar un evento!

👤 *Cliente:* {booking_data.get('client_name', 'No especificado')}
📱 *Teléfono:* {booking_data.get('client_phone', 'No especificado')}
📧 *Email:* {booking_data.get('client_email', 'No especificado')}

🍕 *Servicio:* {service_name}
📅 *Fecha:* {booking_data.get('event_date', 'No especificada')}
⏰ *Hora:* {booking_data.get('event_time', 'No especificada')}
👥 *Participantes:* {booking_data.get('participants', 'No especificado')}
📍 *Ubicación:* {booking_data.get('location', 'No especificada')}
💰 *Precio estimado:* ${estimated_price:,.0f} CLP

🔔 *Favor verificar en la plataforma para confirmar el evento.*

ID: {booking_id}"""

            print(f"Enviando notificación de nuevo agendamiento al admin: {admin_phone}")
            whatsapp_sent = asyncio.run(send_whatsapp_notification(
                admin_phone,
                admin_message,
                "new_booking_alert"
            ))

            if whatsapp_sent:
                print(f"Notificación de nuevo agendamiento enviada exitosamente al admin")
            else:
                print(f"Error al enviar notificación de nuevo agendamiento al admin")

        except Exception as e:
            print(f"Error enviando notificación al admin: {e}")
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
            'updated_at': datetime.now()
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

# Gallery endpoints (basic implementation)
@app.route('/api/gallery/', methods=['GET'])
def get_gallery_images():
    """Get gallery images for public gallery or admin management"""
    try:
        print("=== GALLERY ENDPOINT DEBUG ===")
        event_id = request.args.get('event_id')
        print(f"Event ID param: {event_id}")
        
        db = get_db()
        
        # Simple approach: get all gallery images first
        images_ref = db.collection("gallery").order_by("uploaded_at", direction=firestore.Query.DESCENDING)
        
        gallery_items = []
        for doc in images_ref.stream():
            image = doc.to_dict()
            image['id'] = doc.id
            print(f"Processing image: {doc.id}, event_id: {image.get('event_id')}, published: {image.get('is_published')}")
            
            # Apply event_id filter if specified (admin view)
            if event_id and image.get('event_id') != event_id:
                print(f"  Skipping - wrong event_id")
                continue
                
            # For public gallery (no event_id), filter only published images
            if not event_id and not image.get('is_published', False):
                print(f"  Skipping - not published")
                continue
            
            print(f"  Including image in results")
            
            # Simple format for admin, complex for public
            if event_id:
                # Admin format - simpler
                gallery_item = {
                    'id': doc.id,
                    'title': image.get('title', 'Imagen'),
                    'url': image.get('url', ''),
                    'is_published': image.get('is_published', False),
                    'uploaded_at': image.get('uploaded_at'),
                    'event_id': image.get('event_id')
                }
            else:
                # Public format - more complex
                gallery_item = {
                    'id': doc.id,
                    'title': image.get('title', 'Evento'),
                    'category': 'party',
                    'description': image.get('description', ''),
                    'images': [image.get('url', '')],
                    'participants': 10,
                    'featured': image.get('is_featured', False),
                    'satisfaction': 5,
                    'highlight': 'Experiencia única',
                    'age_group': 'Todas las edades'
                }
            
            gallery_items.append(gallery_item)

        print(f"Returning {len(gallery_items)} items")
        return jsonify(gallery_items), 200

    except Exception as e:
        print(f"❌ Error getting gallery images: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/gallery/upload', methods=['POST'])
def upload_gallery_image():
    """Upload images to gallery"""
    try:
        print("=== GALLERY UPLOAD DEBUG ===")
        print("Request method:", request.method)
        print("Content type:", request.content_type)
        print("Files in request:", list(request.files.keys()) if request.files else "No files")
        print("Form data:", dict(request.form) if request.form else "No form data")
        
        if not request.files:
            print("❌ No files in request")
            return jsonify({"error": "No files provided"}), 400
            
        event_id = request.form.get('event_id')
        if not event_id:
            print("❌ No event_id provided")
            return jsonify({"error": "event_id is required"}), 400
            
        uploaded_files = []
        
        for file_key in request.files:
            file = request.files[file_key]
            print(f"Processing file: {file.filename}, type: {file.content_type}")
            
            if file and file.filename:
                # Validate file type
                if not file.content_type.startswith('image/'):
                    print(f"❌ Invalid file type: {file.content_type}")
                    continue
                    
                # For now, create placeholder entry in Firestore
                # TODO: Upload to Firebase Storage in production
                image_id = str(uuid.uuid4())
                image_data = {
                    "id": image_id,
                    "url": f"https://via.placeholder.com/400x300?text={file.filename}",
                    "title": file.filename,
                    "description": request.form.get('description', ''),
                    "event_id": event_id,
                    "uploaded_at": datetime.now(),
                    "is_featured": False,
                    "is_published": False,  # Por defecto no publicado
                    "filename": file.filename,
                    "content_type": file.content_type
                }
                
                db = get_db()
                db.collection("gallery").document(image_id).set(image_data)
                uploaded_files.append(image_data)
                print(f"✅ File processed: {image_id}")
        
        if not uploaded_files:
            print("❌ No valid images processed")
            return jsonify({"error": "No valid images were processed"}), 400
            
        print(f"✅ Successfully uploaded {len(uploaded_files)} files")
        return jsonify({
            "message": f"Successfully uploaded {len(uploaded_files)} image(s)",
            "files": uploaded_files
        }), 201

    except Exception as e:
        print(f"❌ Error uploading images: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/gallery/<image_id>/publish', methods=['PUT'])
def publish_gallery_image(image_id):
    """Publish or unpublish a gallery image"""
    try:
        data = request.get_json() or {}
        is_published = data.get('is_published', True)
        
        print(f"=== PUBLISH IMAGE DEBUG ===")
        print(f"Image ID: {image_id}")
        print(f"Setting published to: {is_published}")
        
        db = get_db()
        doc_ref = db.collection("gallery").document(image_id)
        
        # Verificar que la imagen existe
        doc = doc_ref.get()
        if not doc.exists:
            print(f"❌ Image not found: {image_id}")
            return jsonify({"error": "Image not found"}), 404
        
        # Actualizar estado de publicación
        doc_ref.update({
            "is_published": is_published,
            "published_at": datetime.now() if is_published else None
        })
        
        action = "publicada" if is_published else "despublicada"
        print(f"✅ Image {action}: {image_id}")
        
        return jsonify({
            "message": f"Imagen {action} exitosamente",
            "image_id": image_id,
            "is_published": is_published
        }), 200

    except Exception as e:
        print(f"❌ Error publishing image: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

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

            # Send WhatsApp confirmation to client
            client_phone = updated_booking.get('client_phone')
            if client_phone:
                print(f"Enviando WhatsApp de confirmación a: {client_phone}")
                try:
                    # Convert datetime strings to datetime objects if needed
                    booking_for_whatsapp = updated_booking.copy()
                    if isinstance(booking_for_whatsapp.get('event_date'), str):
                        booking_for_whatsapp['event_date'] = datetime.fromisoformat(booking_for_whatsapp['event_date'].replace('Z', '+00:00'))

                    # Run async function
                    whatsapp_sent = asyncio.run(send_whatsapp_confirmation(booking_for_whatsapp))

                    if whatsapp_sent:
                        print(f"WhatsApp de confirmación enviado exitosamente a {client_phone}")
                    else:
                        print(f"Error al enviar WhatsApp de confirmación a {client_phone}")
                except Exception as e:
                    print(f"Error enviando WhatsApp de confirmación: {e}")
            else:
                print("No se pudo enviar WhatsApp: no hay teléfono del cliente")

        # Create event automatically when booking is completed with costs
        print(f"Checking event creation conditions:")
        print(f"- status in data: {'status' in data}")
        print(f"- status value: {data.get('status')}")
        print(f"- event_cost in data: {'event_cost' in data}")
        print(f"- event_profit in data: {'event_profit' in data}")
        
        if ('status' in data and data['status'] == 'completed' and 
            ('event_cost' in data or 'event_profit' in data)):
            print(f"Condiciones cumplidas, creando evento para booking {booking_id}")
            try:
                create_event_from_booking(updated_booking)
                print(f"Evento creado automáticamente para booking {booking_id}")
            except Exception as e:
                print(f"Error creando evento automático: {e}")
                # No fallar la actualización del booking si falla la creación del evento
        else:
            print(f"Condiciones no cumplidas para crear evento automático")

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