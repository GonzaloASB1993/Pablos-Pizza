from firebase_functions import https_fn
import os
from dotenv import load_dotenv

# Load environment variables (only if .env exists)
if os.path.exists('.env'):
    load_dotenv('.env')
# Force deployment update - event-inventory integration - fix event_doc error - add null checks

# Import after loading env variables
import firebase_admin
from firebase_admin import firestore, storage
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# WhatsApp service imports
import asyncio
from twilio.rest import Client

# Reports service imports
import pandas as pd
from io import BytesIO
import calendar

# Image processing imports
from PIL import Image
import io

# Config imports - MUST BE BEFORE UTILS IMPORTS
import sys
from pathlib import Path

# Ensure this module can import sibling files when served by Firebase Functions analyzer
CURRENT_DIR = Path(__file__).parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Utils imports - AFTER sys.path configuration
from utils.pagination import paginate_query, create_pagination_response
from utils.audit import log_audit, audit_log

# ==================== BLUEPRINTS IMPORTS ====================
from routes.bookings_routes import bookings_bp
from routes.events_routes import events_bp
from routes.gallery_routes import gallery_bp
from routes.contacts_routes import contacts_bp


try:
    from config import PricingConfig  # local module next to this file
except ModuleNotFoundError:
    try:
        from .config import PricingConfig  # package-style import if backend is a package
    except Exception:
        # Safe fallback with sensible defaults so analysis doesn't fail
        class PricingConfig:  # type: ignore
            PIZZEROS_MINIMUM = 135000
            PIZZA_PARTY_BASE_PRICE = 11990

            @staticmethod
            def get_pizzeros_price(participants: int) -> int:
                if participants <= 10:
                    return 13500
                if participants <= 14:
                    return 10500
                if participants <= 19:
                    return 9500
                return 9000

            @staticmethod
            def get_pizza_party_price(pizzas: int) -> int:
                base = PricingConfig.PIZZA_PARTY_BASE_PRICE
                return round(base * 0.9) if pizzas >= 20 else base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

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

# ==================== WhatsApp Template Helper Functions ====================

# ==================== End of Helper Functions ====================

# ==================== REGISTER BLUEPRINTS ====================
print(">> Registering blueprints...")
app.register_blueprint(bookings_bp)
print("  [OK] Bookings routes registered")
app.register_blueprint(events_bp)
print("  [OK] Events routes registered")
app.register_blueprint(gallery_bp)
print("  [OK] Gallery routes registered")
app.register_blueprint(contacts_bp)
print("  [OK] Contacts routes registered")
print("[SUCCESS] All blueprints registered successfully!")


# Flask-Limiter configuration for rate limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["10000 per day", "1000 per hour"],  # More reasonable limits for admin operations
    storage_uri="memory://",  # In-memory storage (sufficient for single instance)
)

# Rate limit error handler
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "error": "Rate limit exceeded",
        "message": str(e.description)
    }), 429

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
                logger.error(f"CRITICAL: Firebase initialization failed: {e}", exc_info=True)
                import traceback
                traceback.print_exc()
                return None
        _db = firestore.client()
    return _db

def calculate_estimated_price(service_types: str, pizzeros_participants: int = 0, party_participants: int = 0, participants: int = 0, pizza_quantity: int = 0) -> float:
    """
    Calculate estimated price based on service types and participants count per service

    Args:
        service_types: Comma-separated service types (e.g., "workshop", "pizza_party", or "workshop,pizza_party")
        pizzeros_participants: Number of participants for Pizzeros en Acción
        party_participants: Number of PIZZAS for Pizza Party (for pricing)
        pizza_quantity: Number of pizzas for Pizza Party (new field)
        participants: Legacy field for backward compatibility
    """
    logger.info(f"[CALCULATE] Starting calculation: service_types='{service_types}', "
                f"pizzeros_participants={pizzeros_participants}, party_participants={party_participants}, "
                f"pizza_quantity={pizza_quantity}, participants={participants}")

    total_price = 0
    services = [s.strip() for s in service_types.split(',') if s.strip()]

    for service in services:
        if service == "workshop" or service == "pizzeros":
            # Pizzeros en Acción pricing with tiered structure
            service_participants = pizzeros_participants if pizzeros_participants > 0 else participants
            if service_participants <= 0:
                logger.debug(f"Skipping Pizzeros en Acción: no participants")
                continue

            price_per_child = PricingConfig.get_pizzeros_price(service_participants)
            service_total = service_participants * price_per_child

            # Apply minimum for 0-10 range
            if service_participants <= 10:
                service_total = max(PricingConfig.PIZZEROS_MINIMUM, service_total)
                logger.info(f"Pizzeros en Acción (0-10): {service_participants} niños x ${price_per_child} = ${service_total} (mínimo ${PricingConfig.PIZZEROS_MINIMUM})")
            else:
                logger.info(f"Pizzeros en Acción: {service_participants} niños x ${price_per_child} = ${service_total}")

            total_price += service_total

        elif service == "pizza_party" or service == "party":
            # Pizza Party pricing logic - usa PIZZAS, no personas
            pizzas = pizza_quantity if pizza_quantity > 0 else (party_participants if party_participants > 0 else participants)
            if pizzas <= 0:
                logger.debug(f"Skipping Pizza Party: no pizzas specified")
                continue

            price_per_pizza = PricingConfig.get_pizza_party_price(pizzas)
            service_total = pizzas * price_per_pizza

            logger.info(f"Pizza Party: {pizzas} pizzas x ${price_per_pizza} = ${service_total}")
            total_price += service_total

        else:
            logger.warning(f"Unknown service type: {service}")

    result = round(total_price, 2)
    logger.info(f"[CALCULATE] Final total: ${result}")
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
        
        # Get costs from consumption data (new integrated system)
        db = get_db()
        consumption_docs = list(db.collection('event_consumption').where('booking_id', '==', booking_data.get('id')).limit(1).stream())

        if consumption_docs:
            consumption_data = consumption_docs[0].to_dict()
            event_cost = consumption_data.get('total_cost', 0)
            supply_cost = consumption_data.get('total_supply_cost', 0)
            other_expenses = consumption_data.get('total_other_expenses', 0)
            print(f"Using consumption data - Total cost: {event_cost}, Supply cost: {supply_cost}, Other expenses: {other_expenses}")
        else:
            # Fallback to old method if no consumption data
            event_cost = booking_data.get('event_cost', 0)
            supply_cost = 0
            other_expenses = event_cost
            print(f"Using fallback cost data - Total cost: {event_cost}")

        # Calculate profit
        estimated_price = booking_data.get('estimated_price', 0)
        calculated_profit = estimated_price - event_cost if estimated_price and event_cost else 0

        # Use provided profit or calculated profit
        final_profit = booking_data.get('event_profit', calculated_profit)
        
        # Create event data with integrated financials
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
            "source": "auto_booking",  # Indicador de que fue creado automáticamente
            # Enhanced financials with breakdown
            "financials": {
                "income": estimated_price,
                "total_expenses": event_cost,
                "supply_cost": supply_cost,
                "other_expenses": other_expenses,
                "profit": final_profit,
                "profit_margin": round((final_profit / estimated_price * 100), 2) if estimated_price > 0 else 0
            }
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

@app.route('/api/bookings/', methods=['GET'])
@limiter.limit("100 per minute")
def get_bookings():
    """Get all bookings with pagination support"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        # Get pagination parameters from query string
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))

        # Base query ordered by creation date (newest first)
        bookings_ref = db.collection("bookings").order_by('created_at', direction=firestore.Query.DESCENDING)

        # Apply pagination
        paginated_bookings, has_more, total_showing = paginate_query(bookings_ref, page, limit)

        # Add document IDs
        for booking in paginated_bookings:
            if 'id' not in booking:
                # ID should already be in dict from paginate_query, but ensure it's there
                pass

        # Attach computed costs based on financials to avoid frontend miscalculation
        try:
            for booking in paginated_bookings:
                fin = (booking or {}).get('financials') or {}
                est_supply = float(fin.get('estimated_supply_cost', 0) or 0)
                real_supply = float(fin.get('supply_cost', 0) or 0)
                other_exp = float(fin.get('other_expenses', 0) or 0)
                current_supply = real_supply if real_supply > 0 else est_supply
                total_cost = current_supply + other_exp
                booking['computed_costs'] = {
                    'estimated_supply_cost': est_supply,
                    'real_supply_cost': real_supply,
                    'other_expenses_total': other_exp,
                    'current_supply_cost': current_supply,
                    'total_cost': total_cost,
                    'source': 'real' if real_supply > 0 else 'estimated'
                }
        except Exception as e_attach:
            print(f"⚠️ Failed attaching computed costs to bookings page: {e_attach}")

        # Create paginated response
        response = create_pagination_response(
            items=paginated_bookings,
            page=page,
            limit=limit,
            has_more=has_more,
            total_showing=total_showing
        )

        return jsonify(response), 200

    except Exception as e:
        print(f"❌ Error getting bookings: {e}")
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
            'featured': False,
            'highlight': 'Próximamente',
            'age_group': 'Todas las edades'
        }]

        response = jsonify(fallback_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200

def compress_image(image_file, max_width=1920, quality=85):
    """
    Compress image to reduce file size while maintaining quality
    Args:
        image_file: File object from request.files
        max_width: Maximum width in pixels (default 1920px)
        quality: JPEG quality 1-100 (default 85)
    Returns:
        BytesIO object with compressed image
    """
    try:
        # Open image
        img = Image.open(image_file)

        # Convert RGBA to RGB if necessary (for JPEG compatibility)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        # Resize if image is too wide
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # Save to BytesIO with compression
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)

        return output
    except Exception as e:
        print(f"❌ Error compressing image: {e}")
        # Return original file if compression fails
        image_file.seek(0)
        return image_file

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

        # Generate unique filename (always use .jpg for compressed images)
        image_id = str(uuid.uuid4())
        filename = f"{image_id}.jpg"

        # Compress image before upload
        print(f"📸 Compressing image...")
        compressed_file = compress_image(file, max_width=1920, quality=85)
        print(f"📸 Image compressed successfully")

        # Upload to Firebase Storage - using default bucket for the project
        bucket = storage.bucket()
        blob_path = f"gallery/{event_id}/{filename}" if event_id else f"gallery/{filename}"
        blob = bucket.blob(blob_path)

        # Upload compressed file with metadata
        content_type = 'image/jpeg'
        print(f"📸 Uploading to Firebase Storage: {blob_path}, content_type: {content_type}")

        blob.upload_from_file(
            compressed_file,
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

        # Block any modification when booking is already completed
        if current_booking.get('status') == 'completed':
            return jsonify({
                "error": "Cannot modify a completed booking"
            }), 409

        # Update fields
        update_data = {}
        if 'status' in data:
            update_data['status'] = data['status']
            print(f"Actualizando status a: {data['status']}")

        # Add other updatable fields as needed
        updatable_fields = [
            'status', 'notes', 'confirmed_price', 'confirmed_date', 'confirmed_time',
            'event_cost', 'event_profit', 'estimated_price',
            'client_name', 'client_email', 'client_phone',
            'participants', 'event_date', 'event_time', 'service_type', 'location', 'special_requests', 'expenses',
            'pizzeros_participants', 'party_participants', 'party_guests', 'pizza_quantity'
        ]
        for field in updatable_fields:
            if field in data:
                update_data[field] = data[field]
                print(f"Actualizando campo {field}: {data[field]}")

        # Backwards-compat: if pizza_quantity is provided, mirror to party_participants
        # so cualquier código antiguo que lea party_participants se mantenga consistente
        if 'pizza_quantity' in data and 'party_participants' not in update_data:
            try:
                update_data['party_participants'] = int(data['pizza_quantity'])
                print(f"Back-compat: party_participants <- pizza_quantity ({update_data['party_participants']})")
            except Exception:
                pass

        # Sincronizar financials.other_expenses cuando se actualizan expenses[]
        if 'expenses' in data:
            try:
                expenses_array = data['expenses']
                if isinstance(expenses_array, list):
                    # Calcular suma total de gastos adicionales
                    other_expenses_sum = sum(
                        float(expense.get('amount', 0))
                        for expense in expenses_array
                        if isinstance(expense, dict)
                    )

                    # Obtener financials actuales o crear nuevo dict
                    current_financials = current_booking.get('financials', {})
                    if not isinstance(current_financials, dict):
                        current_financials = {}

                    # Actualizar other_expenses en financials
                    current_financials['other_expenses'] = other_expenses_sum
                    update_data['financials'] = current_financials

                    print(f"Sincronizando financials.other_expenses = {other_expenses_sum} (desde {len(expenses_array)} gastos)")
            except Exception as e:
                print(f"Error sincronizando financials.other_expenses: {e}")
                # No fallar la actualización por este error

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

            # Send WhatsApp notification to CLIENT about confirmation
            try:
                client_phone = updated_booking.get('client_phone')
                if client_phone:
                    print(f"📱 Enviando WhatsApp de confirmación al cliente: {client_phone}")

                    client_whatsapp_sent = asyncio.run(send_whatsapp_template(
                        client_phone,
                        'booking_confirmed',
                        updated_booking
                    ))

                    if client_whatsapp_sent:
                        print(f"✅ WhatsApp de confirmación enviado al cliente {client_phone}")
                    else:
                        print(f"❌ Error al enviar WhatsApp al cliente {client_phone}")
                else:
                    print("⚠️ No se pudo enviar WhatsApp al cliente: no hay teléfono")

            except Exception as e:
                print(f"❌ Error enviando WhatsApp al cliente: {e}")
                import traceback
                traceback.print_exc()
                # No fallar la confirmación si falla el WhatsApp

        elif 'status' in data and data['status'] == 'confirmed' and current_booking.get('status') == 'confirmed':
            print(f"Status sigue siendo 'confirmed' - NO enviando notificación duplicada")

        # Create event automatically ONLY when booking CHANGES to 'completed'
        # BUT FIRST validate that supplies and consumption are registered
        if ('status' in data and
            data['status'] == 'completed' and
            current_booking.get('status') != 'completed'):

            # Check if supplies and consumption are registered
            try:
                # Verificar supplies
                supplies_docs = list(db.collection('event_supplies').where('booking_id', '==', booking_id).limit(1).stream())
                has_supplies = len(supplies_docs) > 0

                # Verificar consumption
                consumption_docs = list(db.collection('event_consumption').where('booking_id', '==', booking_id).limit(1).stream())
                has_consumption = len(consumption_docs) > 0

                if not has_supplies:
                    return jsonify({
                        'error': 'Cannot complete event without supplies estimation. Please add supplies first.',
                        'missing': 'supplies'
                    }), 400

                if not has_consumption:
                    return jsonify({
                        'error': 'Cannot complete event without consumption tracking. Please register actual consumption first.',
                        'missing': 'consumption'
                    }), 400

                # If both exist, create the event
                create_event_from_booking(updated_booking)
                print(f"Evento creado automáticamente para booking {booking_id} - status cambió a 'completed'")

            except Exception as e:
                print(f"Error creando evento automático: {e}")
                return jsonify({'error': f'Error creating event: {str(e)}'}), 500

        elif 'status' in data and data['status'] == 'completed' and current_booking.get('status') == 'completed':
            print(f"Status sigue siendo 'completed' - NO creando evento duplicado")

        # Audit log critical actions
        if 'status' in data:
            action_type = f"update_booking_status_to_{data['status']}"
            log_audit(
                user_email=request.headers.get('X-User-Email', 'admin'),
                action=action_type,
                resource_type='booking',
                resource_id=booking_id,
                changes={'old_status': current_booking.get('status'), 'new_status': data['status']},
                metadata={'booking_name': updated_booking.get('name')}
            )

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

        # Audit log cancellation
        booking_data = doc.to_dict()
        log_audit(
            user_email=request.headers.get('X-User-Email', 'admin'),
            action='cancel_booking',
            resource_type='booking',
            resource_id=booking_id,
            changes={'status': 'cancelled'},
            metadata={'booking_name': booking_data.get('name')}
        )

        return jsonify({"message": "Booking cancelled successfully", "id": booking_id}), 200

    except Exception as e:
        print(f"Error deleting booking {booking_id}: {e}")
        return jsonify({"error": str(e)}), 500

# Firebase Functions entry point using new SDK
@https_fn.on_request()
def main(req: https_fn.Request) -> https_fn.Response:
    """Firebase Function entry point - Production ready with inventory endpoints v2.4 - Fixed query args"""

    try:
        # Handle query string properly for Firebase Functions v2
        query_string = ''

        # Firebase Functions v2 provides query parameters via .args
        if hasattr(req, 'args') and req.args:
            # Build query string from args dict
            from urllib.parse import urlencode
            query_string = urlencode(req.args)
        elif hasattr(req, 'query_string') and req.query_string:
            # Fallback to direct query_string if available
            if isinstance(req.query_string, (str, bytes)):
                query_string = req.query_string

        print(f"Request path: {req.path}, method: {req.method}, query_string: {query_string}")

        # Create a simple WSGI app context to handle the request directly
        with app.test_request_context(
            path=req.path,
            method=req.method,
            query_string=query_string,
            data=req.get_data() if hasattr(req, 'get_data') else b'',
            headers=dict(req.headers) if req.headers else {}
        ):
            # Process the request through Flask app
            response = app.full_dispatch_request()

            # Get response data
            response_data = response.get_data()
            status_code = response.status_code

            # Use Flask response headers directly (flask-cors already handles CORS)
            headers = dict(response.headers)

            return https_fn.Response(
                response_data,
                status=status_code,
                headers=headers
            )

    except Exception as e:
        print(f"Error in main function: {e}")
        import traceback
        traceback.print_exc()

        return https_fn.Response(
            '{"error": "Internal server error"}',
            status=500,
            headers={
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
            }
        )

# ===================== INVENTORY ENDPOINTS =====================

@app.route('/api/inventory/', methods=['GET'])
@limiter.limit("100 per minute")
def get_inventory():
    """Get all inventory items with optional filters and pagination"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        # Get filter parameters
        category = request.args.get('category')
        needs_restock = request.args.get('needs_restock')

        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))  # Higher limit for inventory

        # Build query with filters
        query = db.collection('inventory').order_by('name')

        if category:
            query = query.where('category', '==', category)

        if needs_restock is not None:
            query = query.where('needs_restock', '==', needs_restock.lower() == 'true')

        # Apply pagination
        paginated_items, has_more, total_showing = paginate_query(query, page, limit)

        # Create paginated response
        response = create_pagination_response(
            items=paginated_items,
            page=page,
            limit=limit,
            has_more=has_more,
            total_showing=total_showing
        )

        return jsonify(response), 200

    except Exception as e:
        print(f"❌ Error getting inventory: {e}")
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

# ===================== INVENTORY MOVEMENTS ENDPOINTS =====================

@app.route('/api/inventory/movements/', methods=['POST'])
def update_stock_with_movement():
    """Update stock with weighted average cost and create movement record"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        data = request.get_json()
        item_id = data.get('item_id')
        movement_type = data.get('movement_type')
        quantity = float(data.get('quantity', 0))
        cost_per_unit = float(data.get('cost_per_unit', 0))
        reference_id = data.get('reference_id')
        reference_type = data.get('reference_type')
        notes = data.get('notes')
        supplier = data.get('supplier')

        # Get current item data
        item_ref = db.collection('inventory').document(item_id)
        doc = item_ref.get()

        if not doc.exists:
            return jsonify({'error': 'Item not found'}), 404

        current_data = doc.to_dict()
        stock_before = current_data.get('current_stock', 0)
        avg_cost_before = current_data.get('weighted_avg_cost', current_data.get('cost_per_unit', 0))

        # Determine if it's inbound or outbound movement
        inbound_types = ['purchase', 'production', 'return', 'adjustment']
        is_inbound = movement_type in inbound_types

        if is_inbound and quantity > 0:
            # Inbound movement - calculate new weighted average cost
            if stock_before <= 0:
                new_avg_cost = cost_per_unit
                new_total_value = quantity * cost_per_unit
            else:
                current_total_value = stock_before * avg_cost_before
                new_total_value = current_total_value + (quantity * cost_per_unit)
                new_total_stock = stock_before + quantity
                new_avg_cost = new_total_value / new_total_stock if new_total_stock > 0 else avg_cost_before

            new_stock = stock_before + quantity
            actual_quantity = quantity

        elif not is_inbound and quantity > 0:
            # Outbound movement - use current average cost
            new_stock = max(0, stock_before - quantity)
            new_avg_cost = avg_cost_before
            new_total_value = new_stock * new_avg_cost
            actual_quantity = -(min(quantity, stock_before))

        elif movement_type == 'adjustment':
            # Adjustment - can be positive or negative
            new_stock = max(0, stock_before + quantity)
            if quantity > 0:
                # Positive adjustment - calculate new average
                if stock_before <= 0:
                    new_avg_cost = cost_per_unit
                    new_total_value = quantity * cost_per_unit
                else:
                    current_total_value = stock_before * avg_cost_before
                    new_total_value = current_total_value + (quantity * cost_per_unit)
                    new_total_stock = stock_before + quantity
                    new_avg_cost = new_total_value / new_total_stock if new_total_stock > 0 else avg_cost_before
            else:
                # Negative adjustment - use current cost
                new_avg_cost = avg_cost_before
                new_total_value = new_stock * new_avg_cost
            actual_quantity = quantity
        else:
            return jsonify({'error': 'Invalid movement type or quantity'}), 400

        # Update inventory item
        needs_restock = new_stock <= current_data.get('min_stock', 0)

        update_data = {
            'current_stock': new_stock,
            'weighted_avg_cost': new_avg_cost,
            'total_value': new_total_value,
            'cost_per_unit': new_avg_cost,  # Maintain compatibility
            'needs_restock': needs_restock,
            'last_updated': datetime.now()
        }

        item_ref.update(update_data)

        # Create movement record
        movement_id = str(uuid.uuid4())
        movement_data = {
            'id': movement_id,
            'item_id': item_id,
            'item_name': current_data.get('name'),
            'movement_type': movement_type,
            'quantity': actual_quantity,
            'unit': current_data.get('unit'),
            'cost_per_unit': cost_per_unit,
            'total_cost': abs(actual_quantity) * cost_per_unit,
            'reference_id': reference_id,
            'reference_type': reference_type,
            'notes': notes,
            'supplier': supplier,
            'stock_before': stock_before,
            'stock_after': new_stock,
            'avg_cost_before': avg_cost_before,
            'avg_cost_after': new_avg_cost,
            'created_at': datetime.now()
        }

        db.collection('inventory_movements').document(movement_id).set(movement_data)

        return jsonify({
            'message': 'Stock updated successfully with movement',
            'movement_id': movement_id,
            'stock_before': stock_before,
            'stock_after': new_stock,
            'avg_cost_before': avg_cost_before,
            'avg_cost_after': new_avg_cost,
            'needs_restock': needs_restock
        })

    except Exception as e:
        print(f"Error updating stock with movement: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/test-movements', methods=['GET'])
def test_movements():
    """Test endpoint for movements"""
    return jsonify([{"test": "working"}])

def safe_datetime_to_iso(dt_value):
    """Safely convert datetime to ISO string"""
    if dt_value is None:
        return None

    # Handle datetime objects
    if hasattr(dt_value, 'isoformat'):
        try:
            return dt_value.isoformat()
        except Exception:
            return None

    # Handle string datetime (already serialized)
    if isinstance(dt_value, str):
        return dt_value

    # Handle timestamp (if any)
    if isinstance(dt_value, (int, float)):
        try:
            from datetime import datetime
            return datetime.fromtimestamp(dt_value).isoformat()
        except Exception:
            return None

    return None

@app.route('/api/inventory-movements/', methods=['GET'])
def get_inventory_movements():
    """Get inventory movements with optional filters"""
    try:
        # Get query parameters
        item_id = request.args.get('item_id')
        limit = request.args.get('limit', 50, type=int)

        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        print(f"Getting inventory movements for item_id: {item_id}, limit: {limit}")

        # Build query for inventory movements
        movements_ref = db.collection('inventory_movements')

        # Filter by item_id if provided
        if item_id:
            movements_ref = movements_ref.where('item_id', '==', item_id)

        # Try multiple query strategies for robustness
        movements = None
        query_strategy_used = "unknown"

        try:
            # Strategy 1: Try with full ordering (requires composite index)
            if item_id:
                # When filtering by item_id, we need composite index
                print("Attempting query with item_id filter and ordering...")
                movements = movements_ref.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit).get()
                query_strategy_used = "composite_index"
            else:
                # When no filter, simple ordering should work
                print("Attempting query with ordering only...")
                movements = movements_ref.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit).get()
                query_strategy_used = "simple_ordering"

        except Exception as idx_error:
            print(f"Primary query failed: {idx_error}")

            try:
                # Strategy 2: Try without ordering if composite index fails
                print("Fallback: Querying without ordering...")
                movements = movements_ref.limit(limit).get()
                query_strategy_used = "no_ordering"

            except Exception as fallback_error:
                print(f"Fallback query also failed: {fallback_error}")

                try:
                    # Strategy 3: Most basic query possible
                    print("Emergency fallback: Basic collection scan...")
                    movements = db.collection('inventory_movements').limit(min(limit, 20)).get()  # Smaller limit for safety
                    query_strategy_used = "basic_scan"

                except Exception as emergency_error:
                    print(f"All query strategies failed: {emergency_error}")
                    return jsonify({'error': 'Unable to query movements collection', 'details': str(emergency_error)}), 500

        if movements is None:
            return jsonify({'error': 'No query strategy succeeded'}), 500

        # Convert to list with safe serialization
        movements_data = []
        for movement in movements:
            try:
                movement_data = movement.to_dict()
                movement_data['id'] = movement.id

                # Safe datetime conversion
                movement_data['created_at'] = safe_datetime_to_iso(movement_data.get('created_at'))

                # Ensure all required fields exist with defaults
                movement_data.setdefault('item_name', 'Unknown Item')
                movement_data.setdefault('movement_type', 'unknown')
                movement_data.setdefault('quantity', 0)
                movement_data.setdefault('unit', '')
                movement_data.setdefault('cost_per_unit', 0)

                movements_data.append(movement_data)

            except Exception as serialize_error:
                print(f"Error serializing movement {movement.id}: {serialize_error}")
                # Continue with other movements instead of failing completely
                continue

        print(f"Successfully retrieved {len(movements_data)} movements using strategy: {query_strategy_used}")

        # Sort in Python if database ordering failed
        if query_strategy_used in ["no_ordering", "basic_scan"]:
            movements_data.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return jsonify(movements_data)

    except Exception as e:
        print(f"Error getting inventory movements: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/movements/<movement_id>', methods=['GET'])
def get_inventory_movement(movement_id):
    """Get specific inventory movement"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        doc = db.collection('inventory_movements').document(movement_id).get()

        if not doc.exists:
            return jsonify({'error': 'Movement not found'}), 404

        data = doc.to_dict()
        data['id'] = movement_id

        # Safe datetime conversion
        data['created_at'] = safe_datetime_to_iso(data.get('created_at'))

        # Ensure all required fields exist with defaults
        data.setdefault('item_name', 'Unknown Item')
        data.setdefault('movement_type', 'unknown')
        data.setdefault('quantity', 0)
        data.setdefault('unit', '')
        data.setdefault('cost_per_unit', 0)

        return jsonify(data)

    except Exception as e:
        print(f"Error getting inventory movement: {e}")
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

@app.route('/api/production-batches/<batch_id>/simple-complete', methods=['POST'])
def simple_complete_production_batch(batch_id):
    """Simple complete production batch - just mark as completed"""
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

        # Just mark as completed for now
        batch_ref.update({
            'status': 'completed',
            'completed_at': datetime.now()
        })

        return jsonify({
            'message': 'Production batch completed successfully',
            'batch_id': batch_id,
            'status': 'completed'
        })

    except Exception as e:
        print(f"Error completing production batch: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/production-batches/<batch_id>/status', methods=['PUT'])
def update_production_batch_status(batch_id):
    """Update production batch status with weighted average cost movements"""
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

        # If completing, execute full completion logic
        if new_status == 'completed':
            batch_data = batch_doc.to_dict()

            if batch_data['status'] == 'completed':
                return jsonify({'error': 'Batch already completed'}), 400

            # Get recipe to create output product
            recipe_doc = db.collection('recipes').document(batch_data['recipe_id']).get()
            if not recipe_doc.exists:
                return jsonify({'error': 'Recipe not found'}), 404

            recipe_data = recipe_doc.to_dict()

            # 1. Create outbound movements for consumed raw materials
            movements_created = []
            for ingredient in batch_data['ingredients_consumed']:
                # Create movement data
                movement_data = {
                    'item_id': ingredient['item_id'],
                    'movement_type': 'production',
                    'quantity': ingredient['quantity'],
                    'cost_per_unit': ingredient.get('cost_per_unit', 0),
                    'reference_id': batch_id,
                    'reference_type': 'production_batch',
                    'notes': f'Consumo para producción: {recipe_data["name"]}',
                    'supplier': None
                }

                # Update stock using internal function call instead of HTTP request
                try:
                    # Create inventory movement directly
                    movement_id = str(uuid.uuid4())
                    movement_data_full = {
                        **movement_data,
                        'id': movement_id,
                        'created_at': datetime.now()
                    }

                    # Get current item data for calculations
                    item_ref = db.collection("inventory").document(ingredient['item_id'])
                    item_doc = item_ref.get()

                    if item_doc.exists:
                        current_data = item_doc.to_dict()
                        stock_before = current_data.get("current_stock", 0)

                        # For production consumption, reduce stock
                        new_stock = max(0, stock_before - movement_data['quantity'])

                        # Update inventory item
                        item_ref.update({
                            "current_stock": new_stock,
                            "last_updated": datetime.now(),
                            "needs_restock": new_stock <= current_data.get("min_stock", 0)
                        })

                        # Add stock tracking to movement
                        movement_data_full.update({
                            'stock_before': stock_before,
                            'stock_after': new_stock,
                            'item_name': current_data.get('name', 'Unknown'),
                            'unit': current_data.get('unit', ''),
                            'total_cost': movement_data['quantity'] * movement_data['cost_per_unit'],
                            'quantity': -movement_data['quantity']  # Negative for consumption
                        })

                        # Save movement
                        db.collection("inventory_movements").document(movement_id).set(movement_data_full)
                        movements_created.append(movement_id)
                        print(f"✅ Movement created for ingredient {ingredient['item_id']}: {movement_id}")
                    else:
                        print(f"❌ Item not found: {ingredient['item_id']}")

                except Exception as movement_error:
                    print(f"❌ Error creating movement for ingredient {ingredient['item_id']}: {movement_error}")

            # 2. Create or update intermediate product in inventory using weighted average
            output_product_name = f"{recipe_data['name']} (Producido)"

            # Check if intermediate product already exists
            existing_products = db.collection('inventory').where('name', '==', output_product_name).where('product_type', '==', recipe_data['output_product_type']).stream()

            existing_product = None
            output_product_id = None
            for doc in existing_products:
                existing_product = doc
                output_product_id = doc.id
                break

            if existing_product:
                # Update existing product using weighted average movement
                movement_data = {
                    'item_id': output_product_id,
                    'movement_type': 'production',
                    'quantity': batch_data['output_quantity'],
                    'cost_per_unit': recipe_data['cost_per_unit'],
                    'reference_id': batch_id,
                    'reference_type': 'production_batch',
                    'notes': f'Producción completada: {recipe_data["name"]}',
                    'supplier': 'Producción Interna'
                }

                # Create production output movement directly
                try:
                    movement_id = str(uuid.uuid4())
                    movement_data_full = {
                        **movement_data,
                        'id': movement_id,
                        'created_at': datetime.now()
                    }

                    # Get current item data
                    item_ref = db.collection("inventory").document(output_product_id)
                    item_doc = item_ref.get()

                    if item_doc.exists:
                        current_data = item_doc.to_dict()
                        stock_before = current_data.get("current_stock", 0)

                        # Calculate weighted average cost for production output
                        current_avg_cost = current_data.get("weighted_avg_cost", movement_data['cost_per_unit'])

                        if stock_before <= 0:
                            new_avg_cost = movement_data['cost_per_unit']
                        else:
                            current_total_value = stock_before * current_avg_cost
                            new_total_value = current_total_value + (movement_data['quantity'] * movement_data['cost_per_unit'])
                            new_total_stock = stock_before + movement_data['quantity']
                            new_avg_cost = new_total_value / new_total_stock if new_total_stock > 0 else current_avg_cost

                        new_stock = stock_before + movement_data['quantity']
                        new_total_value = new_stock * new_avg_cost

                        # Update inventory item
                        item_ref.update({
                            "current_stock": new_stock,
                            "weighted_avg_cost": new_avg_cost,
                            "cost_per_unit": new_avg_cost,
                            "total_value": new_total_value,
                            "last_updated": datetime.now(),
                            "needs_restock": new_stock <= current_data.get("min_stock", 0)
                        })

                        # Add tracking to movement
                        movement_data_full.update({
                            'stock_before': stock_before,
                            'stock_after': new_stock,
                            'avg_cost_before': current_avg_cost,
                            'avg_cost_after': new_avg_cost,
                            'item_name': current_data.get('name', 'Unknown'),
                            'unit': current_data.get('unit', ''),
                            'total_cost': movement_data['quantity'] * movement_data['cost_per_unit']
                        })

                        # Save movement
                        db.collection("inventory_movements").document(movement_id).set(movement_data_full)
                        movements_created.append(movement_id)
                        print(f"✅ Production output movement created: {movement_id}")
                    else:
                        print(f"❌ Output product not found: {output_product_id}")

                except Exception as movement_error:
                    print(f"❌ Error creating production output movement: {movement_error}")

            else:
                # Create new intermediate product first
                output_product_id = str(uuid.uuid4())
                product_data = {
                    'id': output_product_id,
                    'name': output_product_name,
                    'product_type': recipe_data['output_product_type'],
                    'category': recipe_data['output_category'],
                    'current_stock': 0,  # Start with 0, will be updated by movement
                    'min_stock': batch_data['output_quantity'] * 0.2,  # 20% of production as minimum
                    'max_stock': batch_data['output_quantity'] * 5,    # 5x production as maximum
                    'unit': recipe_data['output_unit'],
                    'cost_per_unit': recipe_data['cost_per_unit'],
                    'weighted_avg_cost': recipe_data['cost_per_unit'],
                    'total_value': 0,
                    'supplier': 'Producción Interna',
                    'notes': f'Producto intermedio generado por receta: {recipe_data["name"]}',
                    'batch_size': batch_data['output_quantity'],
                    'shelf_life_days': 7,  # Default 7 days for intermediate products
                    'last_updated': datetime.now(),
                    'needs_restock': False
                }

                db.collection('inventory').document(output_product_id).set(product_data)
                print(f"✅ New intermediate product created: {output_product_id}")

                # Now create the production movement for the new product
                movement_data = {
                    'item_id': output_product_id,
                    'movement_type': 'production',
                    'quantity': batch_data['output_quantity'],
                    'cost_per_unit': recipe_data['cost_per_unit'],
                    'reference_id': batch_id,
                    'reference_type': 'production_batch',
                    'notes': f'Producción inicial: {recipe_data["name"]}',
                    'supplier': 'Producción Interna'
                }

                # Create initial production movement directly
                try:
                    movement_id = str(uuid.uuid4())
                    movement_data_full = {
                        **movement_data,
                        'id': movement_id,
                        'created_at': datetime.now(),
                        'stock_before': 0,  # New product starts with 0
                        'stock_after': batch_data['output_quantity'],
                        'item_name': output_product_name,
                        'unit': product_data['unit'],
                        'total_cost': movement_data['quantity'] * movement_data['cost_per_unit']
                    }

                    # Update the newly created product with initial stock
                    db.collection('inventory').document(output_product_id).update({
                        'current_stock': batch_data['output_quantity'],
                        'total_value': batch_data['output_quantity'] * movement_data['cost_per_unit']
                    })

                    # Save movement
                    db.collection("inventory_movements").document(movement_id).set(movement_data_full)
                    movements_created.append(movement_id)
                    print(f"✅ Initial production movement created: {movement_id}")

                except Exception as movement_error:
                    print(f"❌ Error creating initial production movement: {movement_error}")

            update_data['completed_at'] = datetime.now()
            update_data['movements_created'] = movements_created

        batch_ref.update(update_data)

        return jsonify({
            'message': f'Batch status updated to {new_status}',
            'inventory_updated': new_status == 'completed',
            'movements_created': update_data.get('movements_created', [])
        })

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

# ==========================================
# EVENT SUPPLIES (STOCK ESTIMADO) ENDPOINTS
# ==========================================

@app.route('/api/event-supplies/', methods=['POST', 'OPTIONS'])
def create_event_supplies():
    """Crear estimación de insumos para un evento (Stock Estimado)"""
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    try:
        data = request.get_json()
        supplies_id = str(uuid.uuid4())

        # Validar datos requeridos
        if not data or 'booking_id' not in data or 'items' not in data:
            return jsonify({'error': 'booking_id and items are required'}), 400

        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        # Verificar que el booking existe y está confirmado
        booking_ref = db.collection('bookings').document(data['booking_id'])
        booking_doc = booking_ref.get()

        if not booking_doc.exists:
            return jsonify({'error': 'Booking not found'}), 404

        booking_data = booking_doc.to_dict()
        if booking_data.get('status') != 'confirmed':
            return jsonify({'error': 'Booking must be confirmed to add supplies'}), 400

        # Verificar disponibilidad de stock para todos los items
        total_estimated_cost = 0
        processed_items = []

        for item in data['items']:
            if not all(k in item for k in ['item_id', 'estimated_quantity']):
                return jsonify({'error': 'Each item must have item_id and estimated_quantity'}), 400

            inventory_ref = db.collection('inventory').document(item['item_id'])
            inventory_doc = inventory_ref.get()

            if not inventory_doc.exists:
                return jsonify({'error': f'Inventory item {item["item_id"]} not found'}), 404

            inventory_data = inventory_doc.to_dict()

            if inventory_data['current_stock'] < item['estimated_quantity']:
                return jsonify({
                    'error': f'Insufficient stock for {inventory_data["name"]}. '
                             f'Available: {inventory_data["current_stock"]}, '
                             f'Required: {item["estimated_quantity"]}'
                }), 400

            # Calcular costo usando el costo promedio ponderado
            cost_per_unit = inventory_data.get('weighted_avg_cost', inventory_data.get('cost_per_unit', 0))
            estimated_total_cost = item['estimated_quantity'] * cost_per_unit
            total_estimated_cost += estimated_total_cost

            processed_item = {
                'item_id': item['item_id'],
                'item_name': inventory_data['name'],
                'estimated_quantity': item['estimated_quantity'],
                'unit': inventory_data['unit'],
                'cost_per_unit': cost_per_unit,
                'estimated_total_cost': estimated_total_cost,
                'batch_id': item.get('batch_id'),
                'notes': item.get('notes')
            }
            processed_items.append(processed_item)

        # Crear registro de supplies
        supplies_data = {
            'id': supplies_id,
            'booking_id': data['booking_id'],
            'items': processed_items,
            'estimated_total_cost': total_estimated_cost,
            'notes': data.get('notes'),
            'created_at': datetime.now()
        }

        db.collection('event_supplies').document(supplies_id).set(supplies_data)

        # Sync booking financials with estimated supply cost for easier frontend consumption
        try:
            existing_financials = booking_data.get('financials') or {}
            existing_financials.update({
                'estimated_supply_cost': float(total_estimated_cost)
            })
            booking_ref.update({
                'financials': existing_financials,
                'updated_at': datetime.now()
            })
        except Exception as fin_err:
            print(f"⚠️ Failed to update booking financials with estimated supply cost: {fin_err}")

        return jsonify({
            'message': 'Event supplies created successfully',
            'supplies_id': supplies_id,
            'supplies': supplies_data
        }), 201

    except Exception as e:
        print(f"Error creating event supplies: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/event-supplies/booking/<booking_id>', methods=['GET', 'OPTIONS'])
def get_event_supplies_by_booking(booking_id):
    """Obtener supplies de un booking específico"""
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        # Buscar supplies para el booking
        docs = list(db.collection('event_supplies').where('booking_id', '==', booking_id).limit(1).stream())

        if not docs:
            return jsonify({'error': 'Supplies not found for this booking'}), 404

        supplies_data = docs[0].to_dict()

        # Serializar fechas
        if 'created_at' in supplies_data:
            supplies_data['created_at'] = safe_datetime_to_iso(supplies_data['created_at'])
        if 'updated_at' in supplies_data:
            supplies_data['updated_at'] = safe_datetime_to_iso(supplies_data['updated_at'])

        return jsonify(supplies_data), 200

    except Exception as e:
        print(f"Error getting event supplies: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/event-supplies/<supplies_id>', methods=['PUT', 'OPTIONS'])
def update_event_supplies(supplies_id):
    """Actualizar supplies estimadas"""
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    try:
        data = request.get_json()
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        supplies_ref = db.collection('event_supplies').document(supplies_id)
        doc = supplies_ref.get()

        if not doc.exists:
            return jsonify({'error': 'Supplies not found'}), 404

        # Nota: Permitimos actualizar insumos aunque exista consumo registrado.
        # La variación se recalculará cuando se re-registre el consumo.

        # Procesar items si se proporcionan
        update_data = {}
        if 'items' in data:
            total_estimated_cost = 0
            processed_items = []

            for item in data['items']:
                inventory_ref = db.collection('inventory').document(item['item_id'])
                inventory_doc = inventory_ref.get()

                if not inventory_doc.exists:
                    return jsonify({'error': f'Inventory item {item["item_id"]} not found'}), 404

                inventory_data = inventory_doc.to_dict()

                if inventory_data['current_stock'] < item['estimated_quantity']:
                    return jsonify({
                        'error': f'Insufficient stock for {inventory_data["name"]}'
                    }), 400

                cost_per_unit = inventory_data.get('weighted_avg_cost', inventory_data.get('cost_per_unit', 0))
                estimated_total_cost = item['estimated_quantity'] * cost_per_unit
                total_estimated_cost += estimated_total_cost

                processed_item = {
                    'item_id': item['item_id'],
                    'item_name': inventory_data['name'],
                    'estimated_quantity': item['estimated_quantity'],
                    'unit': inventory_data['unit'],
                    'cost_per_unit': cost_per_unit,
                    'estimated_total_cost': estimated_total_cost,
                    'batch_id': item.get('batch_id'),
                    'notes': item.get('notes')
                }
                processed_items.append(processed_item)

            update_data['items'] = processed_items
            update_data['estimated_total_cost'] = total_estimated_cost

        if 'notes' in data:
            update_data['notes'] = data['notes']

        update_data['updated_at'] = datetime.now()

        supplies_ref.update(update_data)

        # Also sync booking financials with the refreshed estimated supply cost
        try:
            updated_supplies = supplies_ref.get().to_dict()
            booking_id = updated_supplies.get('booking_id')
            if booking_id:
                booking_ref = db.collection('bookings').document(booking_id)
                booking_doc = booking_ref.get()
                if booking_doc.exists:
                    booking_data = booking_doc.to_dict()
                    financials = booking_data.get('financials') or {}
                    if 'estimated_total_cost' in update_data:
                        financials['estimated_supply_cost'] = float(update_data['estimated_total_cost'])
                    else:
                        financials['estimated_supply_cost'] = float(updated_supplies.get('estimated_total_cost', 0))
                    booking_ref.update({
                        'financials': financials,
                        'updated_at': datetime.now()
                    })
        except Exception as sync_err:
            print(f"⚠️ Failed syncing booking financials after supplies update: {sync_err}")

        # Obtener datos actualizados
        updated_doc = supplies_ref.get()
        updated_data = updated_doc.to_dict()

        # Serializar fechas
        if 'created_at' in updated_data:
            updated_data['created_at'] = safe_datetime_to_iso(updated_data['created_at'])
        if 'updated_at' in updated_data:
            updated_data['updated_at'] = safe_datetime_to_iso(updated_data['updated_at'])

        return jsonify({
            'message': 'Supplies updated successfully',
            'supplies': updated_data
        }), 200

    except Exception as e:
        print(f"Error updating event supplies: {e}")
        return jsonify({'error': str(e)}), 500

# ==========================================
# EVENT CONSUMPTION (STOCK CONFIRMADO) ENDPOINTS
# ==========================================

@app.route('/api/event-consumption/', methods=['POST', 'OPTIONS'])
def create_event_consumption():
    """Registrar consumo real de insumos y descontar del stock (Stock Confirmado)"""
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    try:
        data = request.get_json()
        consumption_id = str(uuid.uuid4())

        # Validar datos requeridos
        required_fields = ['booking_id', 'items_consumed', 'total_other_expenses']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': f'Required fields: {", ".join(required_fields)}'}), 400

        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        # Verificar que el booking existe
        booking_ref = db.collection('bookings').document(data['booking_id'])
        booking_doc = booking_ref.get()
        if not booking_doc.exists:
            return jsonify({'error': 'Booking not found'}), 404

        # Verificar si existe un consumption para este booking
        # Si existe, lo actualizaremos en lugar de crear uno nuevo
        existing_docs = list(db.collection('event_consumption').where('booking_id', '==', data['booking_id']).limit(1).stream())
        existing_consumption = None
        if existing_docs:
            existing_consumption = existing_docs[0]
            existing_consumption_data = existing_consumption.to_dict()

            # Revertir movimientos de inventario anteriores antes de aplicar nuevos
            for old_item in existing_consumption_data.get('items_consumed', []):
                # Buscar y revertir el movimiento de inventario
                old_movements = list(db.collection('inventory_movements')
                    .where('reference_id', '==', data['booking_id'])
                    .where('reference_type', '==', 'event_consumption')
                    .where('item_id', '==', old_item['item_id'])
                    .stream())

                for mov_doc in old_movements:
                    # Restaurar el stock (revertir la salida)
                    inventory_ref = db.collection('inventory').document(old_item['item_id'])
                    inventory_doc = inventory_ref.get()
                    if inventory_doc.exists:
                        inventory_data = inventory_doc.to_dict()
                        restored_stock = inventory_data['current_stock'] + abs(old_item['actual_quantity_consumed'])
                        inventory_ref.update({
                            'current_stock': restored_stock,
                            'needs_restock': restored_stock <= inventory_data.get('min_stock', 0),
                            'last_updated': datetime.now()
                        })
                    # Eliminar movimiento anterior
                    mov_doc.reference.delete()

        # Obtener supplies estimadas si existen (se usa para variación y para calcular consumo desde 'lo que volvió')
        supplies_data = None
        supplies_docs = list(db.collection('event_supplies').where('booking_id', '==', data['booking_id']).limit(1).stream())
        if supplies_docs:
            supplies_data = supplies_docs[0].to_dict()

        # Procesar cada item consumido y crear movimientos de inventario
        processed_items = []
        total_supply_cost = 0

        # Asegurar que total_other_expenses sea numérico
        total_other_expenses_input = data.get('total_other_expenses')
        try:
            total_other_expenses_input = float(total_other_expenses_input) if total_other_expenses_input is not None else 0.0
        except Exception:
            total_other_expenses_input = 0.0

        for item in data['items_consumed']:
            # Soportar nuevo flujo: quantity_returned (lo que volvió) o actual_quantity_consumed (legacy)
            if 'item_id' not in item:
                logger.error(f"Item missing item_id: {item}")
                return jsonify({'error': 'Each item must have item_id'}), 400

            # Calcular actual_quantity_consumed según el flujo
            calculated_from_return = False
            estimated_quantity = 0.0
            estimated_item = None
            if supplies_data:
                estimated_item = next((s for s in supplies_data.get('items', []) if s['item_id'] == item['item_id']), None)
                if estimated_item:
                    estimated_quantity = float(estimated_item.get('estimated_quantity', 0) or 0)

            if 'quantity_returned' in item:
                # Calcular consumo = estimado - lo que volvió (si hay estimación); si no, usar actual si viene provisto
                try:
                    returned_qty = float(item.get('quantity_returned') or 0)
                except Exception:
                    returned_qty = 0.0

                if estimated_item is not None:
                    # Validar que no vuelva más de lo llevado
                    if returned_qty > estimated_quantity:
                        logger.error(f"Quantity returned ({returned_qty}) exceeds estimated ({estimated_quantity})")
                        return jsonify({
                            'error': f'La cantidad que volvió ({returned_qty}) no puede ser mayor que lo llevado ({estimated_quantity})'
                        }), 400
                    actual_qty = max(0.0, estimated_quantity - returned_qty)
                    calculated_from_return = True
                else:
                    # Sin item estimado: permitir si nos dan actual directamente; si no, consumo=0
                    try:
                        actual_qty = float(item.get('actual_quantity_consumed') or 0)
                    except Exception:
                        actual_qty = 0.0
            else:
                # Legacy: usar actual_quantity_consumed
                try:
                    actual_qty = float(item.get('actual_quantity_consumed') or 0)
                except Exception:
                    logger.error(f"Item missing both quantity_returned and actual_quantity_consumed: {item}")
                    return jsonify({'error': 'Each item must have quantity_returned or actual_quantity_consumed'}), 400

            # Normalizar a no-negativo
            actual_qty = max(0.0, actual_qty)
            item['actual_quantity_consumed'] = actual_qty

            # Verificar item de inventario
            inventory_ref = db.collection('inventory').document(item['item_id'])
            inventory_doc = inventory_ref.get()

            if not inventory_doc.exists:
                return jsonify({'error': f'Inventory item {item["item_id"]} not found'}), 404

            inventory_data = inventory_doc.to_dict()

            # Verificar stock suficiente
            if inventory_data['current_stock'] < item['actual_quantity_consumed']:
                return jsonify({
                    'error': f'Insufficient stock for {inventory_data["name"]}. '
                             f'Available: {inventory_data["current_stock"]}, '
                             f'Required: {item["actual_quantity_consumed"]}'
                }), 400

            # Calcular variance si hay datos estimados
            variance = None
            # Variación solo si hay estimación para ese item
            if estimated_item is not None:
                variance = item['actual_quantity_consumed'] - estimated_quantity

            # Usar costo promedio ponderado actual
            cost_per_unit = inventory_data.get('weighted_avg_cost', inventory_data.get('cost_per_unit', 0))
            total_cost = item['actual_quantity_consumed'] * cost_per_unit
            total_supply_cost += total_cost

            # Crear item procesado
            processed_item = {
                'item_id': item['item_id'],
                'item_name': inventory_data['name'],
                'estimated_quantity': estimated_quantity,
                'quantity_returned': item.get('quantity_returned', 0),  # Lo que volvió
                'actual_quantity_consumed': item['actual_quantity_consumed'],  # Consumo real calculado
                'unit': inventory_data['unit'],
                'cost_per_unit': cost_per_unit,
                'total_cost': total_cost,
                'batch_id': item.get('batch_id'),
                'variance': variance
            }
            processed_items.append(processed_item)

            # Crear movimiento de inventario (salida por consumo en evento)
            movement_id = str(uuid.uuid4())
            movement_data = {
                'id': movement_id,
                'item_id': item['item_id'],
                'item_name': inventory_data['name'],
                'movement_type': 'sale',  # Salida por consumo
                'quantity': -item['actual_quantity_consumed'],  # Negativo para salida
                'unit': inventory_data['unit'],
                'cost_per_unit': cost_per_unit,
                'total_cost': total_cost,
                'reference_id': data['booking_id'],
                'reference_type': 'event_consumption',
                'notes': f"Consumo en evento - {data.get('notes', '')}",
                'stock_before': inventory_data['current_stock'],
                'stock_after': inventory_data['current_stock'] - item['actual_quantity_consumed'],
                'avg_cost_before': cost_per_unit,
                'avg_cost_after': cost_per_unit,
                'created_at': datetime.now()
            }

            db.collection('inventory_movements').document(movement_id).set(movement_data)

            # Actualizar stock en inventario
            new_stock = inventory_data['current_stock'] - item['actual_quantity_consumed']
            needs_restock = new_stock <= inventory_data.get('min_stock', 0)

            inventory_ref.update({
                'current_stock': new_stock,
                'needs_restock': needs_restock,
                'last_updated': datetime.now()
            })

        # Calcular costo total
        total_cost = total_supply_cost + total_other_expenses_input

        # Crear o actualizar registro de consumption
        if existing_consumption:
            # Actualizar consumo existente
            consumption_id = existing_consumption.id
            consumption_data = {
                'items_consumed': processed_items,
                'total_supply_cost': total_supply_cost,
                'total_other_expenses': total_other_expenses_input,
                'total_cost': total_cost,
                'notes': data.get('notes'),
                'updated_at': datetime.now()
            }
            db.collection('event_consumption').document(consumption_id).update(consumption_data)
            # Leer documento actualizado para responder con datos consistentes
            saved_doc = db.collection('event_consumption').document(consumption_id).get()
            saved_consumption = saved_doc.to_dict()
        else:
            # Crear nuevo registro de consumption
            consumption_data = {
                'id': consumption_id,
                'event_id': data.get('event_id'),  # Puede ser None si es solo booking
                'booking_id': data['booking_id'],
                'items_consumed': processed_items,
                'total_supply_cost': total_supply_cost,
                'total_other_expenses': total_other_expenses_input,
                'total_cost': total_cost,
                'notes': data.get('notes'),
                'supplies_id': supplies_data['id'] if supplies_data else None,
                'created_at': datetime.now()
            }
            db.collection('event_consumption').document(consumption_id).set(consumption_data)
            saved_consumption = consumption_data

        # Actualizar el booking con el costo total calculado
        print(f"DEBUG: About to update booking {data['booking_id']} with financials")
        booking_data = booking_doc.to_dict()
        financials = booking_data.get('financials', {})

        # Actualizar financials con los nuevos costos
        financials.update({
            'total_expenses': total_cost,
            'supply_cost': total_supply_cost,
            'other_expenses': total_other_expenses_input
        })

        print(f"DEBUG: Calculated financials: {financials}")

        # Recalcular profit si hay income
        if 'income' in financials:
            financials['profit'] = financials['income'] - total_cost

        update_data = {
            'financials': financials,
            'updated_at': datetime.now()
        }

        print(f"DEBUG: Updating booking with: {update_data}")
        booking_ref.update(update_data)
        print(f"DEBUG: Booking update completed successfully")

        # Serializar fecha para respuesta
        if 'created_at' in saved_consumption:
            saved_consumption['created_at'] = safe_datetime_to_iso(saved_consumption.get('created_at'))

        return jsonify({
            'message': 'Event consumption registered successfully',
            'consumption_id': consumption_id,
            'consumption': saved_consumption
        }), 201

    except Exception as e:
        print(f"Error creating event consumption: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/event-consumption/event/<event_id>', methods=['GET', 'OPTIONS'])
def get_event_consumption(event_id):
    """Obtener registro de consumo de un evento"""
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        docs = list(db.collection('event_consumption').where('event_id', '==', event_id).limit(1).stream())

        if not docs:
            return jsonify({'error': 'Consumption not found for this event'}), 404

        consumption_data = docs[0].to_dict()

        # Serializar fecha
        if 'created_at' in consumption_data:
            consumption_data['created_at'] = safe_datetime_to_iso(consumption_data['created_at'])

        return jsonify(consumption_data), 200

    except Exception as e:
        print(f"Error getting event consumption: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/event-supplies/status/<booking_id>', methods=['GET', 'OPTIONS'])
def get_consumption_status(booking_id):
    """Verificar si un booking tiene supplies y consumption registrados"""
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        # Verificar supplies
        supplies_docs = list(db.collection('event_supplies').where('booking_id', '==', booking_id).limit(1).stream())
        has_supplies = len(supplies_docs) > 0
        supplies_data = supplies_docs[0].to_dict() if has_supplies else None

        # Verificar consumption
        consumption_docs = list(db.collection('event_consumption').where('booking_id', '==', booking_id).limit(1).stream())
        has_consumption = len(consumption_docs) > 0
        consumption_data = consumption_docs[0].to_dict() if has_consumption else None

        # Serializar fechas si existen
        if supplies_data and 'created_at' in supplies_data:
            supplies_data['created_at'] = safe_datetime_to_iso(supplies_data['created_at'])
        if consumption_data and 'created_at' in consumption_data:
            consumption_data['created_at'] = safe_datetime_to_iso(consumption_data['created_at'])

        # Compute canonical cost metrics for the UI to avoid double counting and parsing issues
        estimated_supply_cost = float((supplies_data or {}).get('estimated_total_cost', 0) or 0)
        real_supply_cost = float((consumption_data or {}).get('total_supply_cost', 0) or 0)
        other_expenses = float((consumption_data or {}).get('total_other_expenses', 0) or 0)

        # Prefer real supply cost when available; otherwise fall back to estimated
        current_supply_cost = real_supply_cost if real_supply_cost > 0 else estimated_supply_cost
        total_cost_correct = real_supply_cost + other_expenses if real_supply_cost > 0 else estimated_supply_cost + other_expenses

        computed = {
            'estimated_supply_cost': estimated_supply_cost,
            'real_supply_cost': real_supply_cost,
            'other_expenses_total': other_expenses,
            'current_supply_cost': current_supply_cost,
            'total_cost': total_cost_correct,
            'source': 'real' if real_supply_cost > 0 else 'estimated'
        }

        return jsonify({
            'booking_id': booking_id,
            'has_supplies': has_supplies,
            'has_consumption': has_consumption,
            'can_complete_event': has_supplies and has_consumption,
            'supplies': supplies_data,
            'consumption': consumption_data,
            'computed': computed
        }), 200

    except Exception as e:
        print(f"Error checking consumption status: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== REPORTS API ROUTES ====================

def calculate_client_retention_rate(year: int, month: int) -> float:
    """Calcular tasa de retención de clientes para el mes"""
    try:
        db = get_db()
        if not db:
            logger.warning("Database unavailable for retention rate calculation")
            return 0.0

        # Obtener clientes del mes actual - usar strings para comparar
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        all_current_bookings = list(db.collection("bookings").where(
            "event_date", ">=", start_date
        ).where(
            "event_date", "<", end_date
        ).stream())

        # Filtrar solo confirmados/completados
        current_bookings = [b for b in all_current_bookings if b.to_dict().get("status") in ["confirmed", "completed"]]

        if not current_bookings:
            return 0.0

        current_clients = set()
        for booking_doc in current_bookings:
            booking_data = booking_doc.to_dict()
            client_email = booking_data.get("client_email")
            if client_email:
                current_clients.add(client_email)

        # Obtener clientes de meses anteriores
        all_previous_bookings = list(db.collection("bookings").where(
            "event_date", "<", start_date
        ).stream())

        # Filtrar solo confirmados/completados
        previous_bookings = [b for b in all_previous_bookings if b.to_dict().get("status") in ["confirmed", "completed"]]

        previous_clients = set()
        for booking_doc in previous_bookings:
            booking_data = booking_doc.to_dict()
            client_email = booking_data.get("client_email")
            if client_email:
                previous_clients.add(client_email)

        # Calcular retención
        returning_clients = current_clients.intersection(previous_clients)
        retention_rate = (len(returning_clients) / len(current_clients)) * 100

        return retention_rate

    except:
        return 0.0

def get_monthly_report_data(year: int, month: int):
    """Generar datos de reporte mensual (función auxiliar)"""
    db = get_db()
    if not db:
        logger.error("Database connection failed in get_monthly_report_data")
        raise Exception("Database connection unavailable")

    # Rango de fechas del mes - usar strings para comparar con event_date guardado como string
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    # Obtener agendamientos del mes (confirmed y completed)
    bookings_query = db.collection("bookings").where(
        "event_date", ">=", start_date
    ).where(
        "event_date", "<", end_date
    )

    all_bookings = list(bookings_query.stream())
    # Filtrar solo agendamientos confirmados o completados
    bookings = [b for b in all_bookings if b.to_dict().get("status") in ["confirmed", "completed"]]
    total_events = len(bookings)

    if total_events == 0:
        return {
            "month": month,
            "year": year,
            "total_events": 0,
            "total_income": 0.0,
            "total_expenses": 0.0,
            "total_profit": 0.0,
            "avg_participants": 0.0,
            "most_popular_service": "N/A",
            "client_retention_rate": 0.0,
            "events_by_service": {}
        }

    # Helper: costo total consistente con la UI (insumos + gastos), evitando doble conteo
    def _calc_total_cost(b: dict) -> float:
        try:
            # Calcular suma de gastos adicionales del array expenses[]
            expenses_sum = 0.0
            try:
                expenses_sum = sum((float((e or {}).get('amount') or 0) for e in (b.get('expenses') or [])))
            except Exception:
                expenses_sum = 0.0

            # Obtener costos de insumos desde financials
            fin = (b.get('financials') or {})
            supply_real = float(fin.get('supply_cost') or 0)
            est_supply = float(fin.get('estimated_supply_cost') or 0)

            # Usar costo real de insumos si existe, si no usar estimado
            supply_cost = supply_real if supply_real > 0 else est_supply

            # SIEMPRE sumar: costo de insumos + gastos adicionales del array expenses[]
            total_cost = supply_cost + expenses_sum

            if total_cost > 0:
                return float(total_cost)

            # Último recurso: event_cost si existe (compatibilidad con datos antiguos)
            return float(b.get('event_cost') or 0)
        except Exception:
            try:
                return float(b.get('event_cost') or 0)
            except Exception:
                return 0.0

    # Calcular métricas financieras desde los agendamientos
    total_income = 0.0
    total_expenses = 0.0
    total_participants = 0
    service_counts = {}
    service_incomes = {}  # Agregar income por servicio

    for booking_doc in bookings:
        booking_data = booking_doc.to_dict()

        # Ingresos: precio estimado o final
        estimated_price = booking_data.get("estimated_price", 0.0)
        final_price = booking_data.get("final_price", estimated_price)
        total_income += final_price

        # Gastos: usar financials.total_expenses + expenses, con fallback a event_cost
        event_cost = _calc_total_cost(booking_data)
        total_expenses += event_cost

        # Obtener participantes
        participants = booking_data.get("participants", 0)
        total_participants += participants

        # Contar servicios directamente del booking
        service_type = booking_data.get("service_type", "unknown")
        service_counts[service_type] = service_counts.get(service_type, 0) + 1
        # Acumular ingresos por servicio
        service_incomes[service_type] = service_incomes.get(service_type, 0.0) + final_price

    total_profit = total_income - total_expenses
    avg_participants = total_participants / total_events if total_events > 0 else 0

    # Servicio más popular
    most_popular_service = max(service_counts.items(), key=lambda x: x[1])[0] if service_counts else "N/A"

    # Calcular tasa de retención (clientes que volvieron)
    client_retention_rate = calculate_client_retention_rate(year, month)

    # Construir events_by_service para el frontend
    events_by_service = {}
    for service_type, count in service_counts.items():
        events_by_service[service_type] = {
            "count": count,
            "total_income": round(service_incomes.get(service_type, 0.0), 2)
        }

    return {
        "month": month,
        "year": year,
        "total_events": total_events,
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "total_profit": round(total_profit, 2),
        "avg_participants": round(avg_participants, 1),
        "most_popular_service": most_popular_service,
        "client_retention_rate": round(client_retention_rate, 2),
        "events_by_service": events_by_service
    }

@app.route('/api/reports/monthly/<int:year>/<int:month>', methods=['GET'])
def get_monthly_report(year: int, month: int):
    """Generar reporte mensual"""
    try:
        report_data = get_monthly_report_data(year, month)
        return jsonify(report_data)
    except Exception as e:
        return jsonify({"error": f"Error al generar reporte mensual: {str(e)}"}), 500

@app.route('/api/reports/annual/<int:year>', methods=['GET'])
def get_annual_summary(year: int):
    """Resumen anual por meses"""
    try:
        monthly_reports = []

        for month in range(1, 13):
            try:
                # Llamar a la función auxiliar get_monthly_report_data
                report_data = get_monthly_report_data(year, month)
                monthly_reports.append(report_data)
            except:
                # Si hay error en un mes, usar valores por defecto
                monthly_reports.append({
                    "month": month,
                    "year": year,
                    "total_events": 0,
                    "total_income": 0.0,
                    "total_expenses": 0.0,
                    "total_profit": 0.0,
                    "avg_participants": 0.0,
                    "most_popular_service": "N/A",
                    "client_retention_rate": 0.0
                })

        # Calcular totales anuales
        annual_summary = {
            "year": year,
            "monthly_reports": monthly_reports,
            "annual_totals": {
                "total_events": sum(r["total_events"] for r in monthly_reports),
                "total_income": sum(r["total_income"] for r in monthly_reports),
                "total_expenses": sum(r["total_expenses"] for r in monthly_reports),
                "total_profit": sum(r["total_profit"] for r in monthly_reports),
                "avg_participants": sum(r["avg_participants"] for r in monthly_reports) / 12
            }
        }

        return jsonify(annual_summary)

    except Exception as e:
        return jsonify({"error": f"Error al generar resumen anual: {str(e)}"}), 500

@app.route('/api/reports/dashboard', methods=['GET'])
def get_dashboard_stats():
    """Estadísticas para el dashboard principal"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        now = datetime.now()
        today = now.date()
        current_month = now.month
        current_year = now.year

        # Estadísticas de hoy
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        today_bookings = len(list(db.collection("bookings").where(
            "created_at", ">=", today_start
        ).where(
            "created_at", "<=", today_end
        ).stream()))

        # Estadísticas del mes actual - usar misma lógica de costos que en reportes
        try:
            monthly_report = get_monthly_report_data(current_year, current_month)
        except:
            monthly_report = {
                "total_events": 0,
                "total_income": 0.0,
                "total_profit": 0.0
            }

        # Próximos eventos (próximos 7 días) - usar strings para comparar
        today_str = today.strftime('%Y-%m-%d')
        next_week = today + timedelta(days=7)
        next_week_str = next_week.strftime('%Y-%m-%d')

        upcoming_events = list(db.collection("bookings").where(
            "event_date", ">=", today_str
        ).where(
            "event_date", "<=", next_week_str
        ).where(
            "status", "==", "confirmed"
        ).stream())

        # Estadísticas de inventario
        low_stock_items = len(list(db.collection("inventory").where(
            "needs_restock", "==", True
        ).stream()))

        # Reseñas pendientes
        pending_reviews = len(list(db.collection("reviews").where(
            "is_approved", "==", False
        ).stream()))

        return jsonify({
            "today": {
                "new_bookings": today_bookings,
                "date": today.isoformat()
            },
            "current_month": {
                "month_name": calendar.month_name[current_month],
                "events": monthly_report["total_events"],
                "income": monthly_report["total_income"],
                "profit": monthly_report["total_profit"]
            },
            "upcoming_events": len(upcoming_events),
            "alerts": {
                "low_stock_items": low_stock_items,
                "pending_reviews": pending_reviews
            }
        })

    except Exception as e:
        return jsonify({"error": f"Error al obtener estadísticas del dashboard: {str(e)}"}), 500

@app.route('/api/reports/clients/top', methods=['GET'])
def get_top_clients():
    """Obtener clientes más frecuentes"""
    try:
        db = get_db()
        limit = request.args.get('limit', 10, type=int)

        # Obtener todos los bookings confirmados y completados
        all_bookings = list(db.collection("bookings").stream())
        bookings = [b for b in all_bookings if b.to_dict().get("status") in ["confirmed", "completed"]]

        client_stats = {}
        for booking_doc in bookings:
            booking_data = booking_doc.to_dict()
            client_email = booking_data.get("client_email")
            client_name = booking_data.get("client_name")

            if client_email and client_email not in client_stats:
                client_stats[client_email] = {
                    "name": client_name,
                    "email": client_email,
                    "total_bookings": 0,
                    "total_spent": 0.0
                }

            if client_email:
                client_stats[client_email]["total_bookings"] += 1

                # Obtener ingresos directamente del booking
                estimated_price = booking_data.get("estimated_price", 0.0)
                final_price = booking_data.get("final_price", estimated_price)
                client_stats[client_email]["total_spent"] += final_price

        # Ordenar por número de bookings
        top_clients = sorted(
            client_stats.values(),
            key=lambda x: x["total_bookings"],
            reverse=True
        )[:limit]

        return jsonify({"clients": top_clients})

    except Exception as e:
        return jsonify({"error": f"Error al obtener clientes top: {str(e)}"}), 500

@app.route('/api/reports/export/monthly/<int:year>/<int:month>', methods=['GET'])
def export_monthly_report(year: int, month: int):
    """Exportar reporte mensual a Excel"""
    try:
        from flask import Response

        # Obtener reporte
        report = get_monthly_report_data(year, month)

        # Crear Excel con pandas
        data = {
            "Métrica": [
                "Total Eventos",
                "Ingresos Totales",
                "Gastos Totales",
                "Utilidad Total",
                "Promedio Participantes",
                "Servicio Más Popular",
                "Tasa Retención Clientes"
            ],
            "Valor": [
                report["total_events"],
                f"${report['total_income']:,.2f}",
                f"${report['total_expenses']:,.2f}",
                f"${report['total_profit']:,.2f}",
                f"{report['avg_participants']:.1f}",
                report["most_popular_service"],
                f"{report['client_retention_rate']}%"
            ]
        }

        df = pd.DataFrame(data)

        # Crear archivo Excel en memoria
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=f'{calendar.month_name[month]} {year}', index=False)

        excel_buffer.seek(0)

        filename = f"reporte_mensual_{year}_{month:02d}.xlsx"

        return Response(
            excel_buffer.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        return jsonify({"error": f"Error al exportar reporte: {str(e)}"}), 500

# ==================== END REPORTS API ROUTES ====================

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
    print("   - POST /api/event-supplies/ - Create supplies estimation")
    print("   - GET /api/event-supplies/booking/<id> - Get supplies by booking")
    print("   - POST /api/event-consumption/ - Register consumption")
    print("   - GET /api/event-supplies/status/<id> - Check supplies & consumption status")
    print("Use Ctrl+C to stop the server")
    
    # Run Flask development server
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=True,
        threaded=True
    )
