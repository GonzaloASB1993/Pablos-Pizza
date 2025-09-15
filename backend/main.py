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

# Initialize Flask app
app = Flask(__name__)

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

        # Create professional HTML email
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
                <h2>Hola {booking_data.get('client_name', 'Cliente')},</h2>

                <p>¡Excelente noticia! Tu evento ha sido <strong>confirmado</strong> y estamos emocionados de ser parte de tu celebración.</p>

                <div class="event-details">
                    <h3>📋 Detalles de tu evento:</h3>
                    <p><strong>🍕 Servicio:</strong> {service_name}</p>
                    <p><strong>📅 Fecha:</strong> {booking_data.get('event_date', 'No especificada')}</p>
                    <p><strong>⏰ Hora:</strong> {booking_data.get('event_time', 'No especificada')}</p>
                    <p><strong>👥 Participantes:</strong> {booking_data.get('participants', 'N/A')}</p>
                    <p><strong>📍 Ubicación:</strong> {booking_data.get('location', 'No especificada')}</p>
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
    """Get gallery images"""
    try:
        db = get_db()
        images_ref = db.collection("gallery").order_by("uploaded_at", direction=firestore.Query.DESCENDING)
        
        # Apply filters if provided
        event_id = request.args.get('event_id')
        if event_id:
            images_ref = images_ref.where("event_id", "==", event_id)
        
        images = []
        for doc in images_ref.stream():
            image = doc.to_dict()
            image['id'] = doc.id
            images.append(image)

        return jsonify(images), 200

    except Exception as e:
        print(f"Error getting gallery images: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/gallery/upload', methods=['POST'])
def upload_gallery_image():
    """Upload image to gallery - placeholder endpoint"""
    try:
        # Para ahora, retornamos un placeholder
        # En producción deberían integrarse con Firebase Storage
        data = request.get_json() or {}
        
        image_id = str(uuid.uuid4())
        image_data = {
            "id": image_id,
            "url": "https://via.placeholder.com/400x300",  # Placeholder
            "title": data.get('title', 'Nueva imagen'),
            "description": data.get('description', ''),
            "event_id": data.get('event_id'),
            "uploaded_at": datetime.now(),
            "is_featured": data.get('is_featured', False)
        }
        
        db = get_db()
        db.collection("gallery").document(image_id).set(image_data)
        
        return jsonify(image_data), 201

    except Exception as e:
        print(f"Error uploading image: {e}")
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