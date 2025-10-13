"""
Script to generate blueprint files from main.py
This extracts routes from main.py and creates modular blueprint files
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def generate_bookings_routes():
    """Generate bookings_routes.py blueprint"""
    content = '''"""
Bookings Routes Blueprint
Handles all booking-related endpoints
"""
from flask import Blueprint, request
import uuid
from datetime import datetime
import asyncio
from database import get_db
from utils.responses import json_response, error_response, created_response, not_found_response
from utils.pagination import paginate_query, create_pagination_response
from utils.financial_sync import compute_booking_costs
from services.whatsapp_service import send_whatsapp_template
import os

# Import pricing config
try:
    from config import PricingConfig
except:
    class PricingConfig:
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

# Create blueprint
bookings_bp = Blueprint('bookings', __name__, url_prefix='/api/bookings')


def calculate_estimated_price(service_types: str, pizzeros_participants: int = 0,
                             party_participants: int = 0, participants: int = 0,
                             pizza_quantity: int = 0) -> float:
    """Calculate estimated price based on service types and participants"""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[CALCULATE] Starting calculation: service_types='{service_types}', "
                f"pizzeros_participants={pizzeros_participants}, party_participants={party_participants}, "
                f"pizza_quantity={pizza_quantity}, participants={participants}")

    total_price = 0
    services = [s.strip() for s in service_types.split(',') if s.strip()]

    for service in services:
        if service == "workshop" or service == "pizzeros":
            service_participants = pizzeros_participants if pizzeros_participants > 0 else participants
            if service_participants <= 0:
                continue

            price_per_child = PricingConfig.get_pizzeros_price(service_participants)
            service_total = service_participants * price_per_child

            if service_participants <= 10:
                service_total = max(PricingConfig.PIZZEROS_MINIMUM, service_total)

            total_price += service_total

        elif service == "pizza_party" or service == "party":
            pizzas = pizza_quantity if pizza_quantity > 0 else (party_participants if party_participants > 0 else participants)
            if pizzas <= 0:
                continue

            price_per_pizza = PricingConfig.get_pizza_party_price(pizzas)
            service_total = pizzas * price_per_pizza
            total_price += service_total

    return round(total_price, 2)


@bookings_bp.route('/', methods=['POST'])
def create_booking():
    """Create new booking"""
    try:
        data = request.get_json()
        if not data:
            return error_response("No data provided", 400)

        # Validate required fields
        required_fields = ['service_type', 'participants']
        for field in required_fields:
            if field not in data:
                return error_response(f"Missing required field: {field}", 400)

        # Generate booking ID
        booking_id = str(uuid.uuid4())

        # Calculate estimated price
        estimated_price = calculate_estimated_price(
            service_types=data.get('service_type', ''),
            pizzeros_participants=data.get('pizzeros_participants', 0),
            party_participants=data.get('party_participants', 0),
            participants=data.get('participants', 0),
            pizza_quantity=data.get('pizza_quantity', 0)
        )

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

        # Send WhatsApp notifications (non-blocking)
        try:
            admin_phone = os.getenv('ADMIN_WHATSAPP_NUMBER', '+56998960858')
            partner_phone = os.getenv('PARTNER_WHATSAPP_NUMBER', '+56998960858')

            asyncio.run(send_whatsapp_template(admin_phone, 'new_booking', booking_data))
            asyncio.run(send_whatsapp_template(partner_phone, 'new_booking', booking_data))
        except Exception as e:
            print(f"Error sending WhatsApp: {e}")

        return created_response("booking", booking_id, booking_data)

    except Exception as e:
        print(f"Error creating booking: {e}")
        return error_response(str(e), 500)


@bookings_bp.route('/', methods=['GET'])
def get_bookings():
    """Get all bookings with pagination"""
    try:
        db = get_db()
        if not db:
            return error_response('Database connection failed', 500)

        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))

        bookings_ref = db.collection("bookings").order_by('created_at', direction='DESCENDING')
        paginated_bookings, has_more, total_showing = paginate_query(bookings_ref, page, limit)

        # Attach computed costs
        for booking in paginated_bookings:
            computed_costs = compute_booking_costs(booking.get('id'), booking)
            booking['computed_costs'] = computed_costs

        response = create_pagination_response(
            items=paginated_bookings,
            page=page,
            limit=limit,
            has_more=has_more,
            total_showing=total_showing
        )

        return json_response(response, 200)

    except Exception as e:
        print(f"Error getting bookings: {e}")
        return error_response(str(e), 500)


@bookings_bp.route('/<booking_id>', methods=['GET'])
def get_booking(booking_id):
    """Get specific booking by ID"""
    try:
        db = get_db()
        doc_ref = db.collection("bookings").document(booking_id)
        doc = doc_ref.get()

        if doc.exists:
            booking = doc.to_dict()
            booking['id'] = doc.id

            # Attach computed costs
            computed_costs = compute_booking_costs(booking_id, booking)
            booking['computed_costs'] = computed_costs

            return json_response(booking, 200)
        else:
            return not_found_response("booking", booking_id)

    except Exception as e:
        print(f"Error getting booking: {e}")
        return error_response(str(e), 500)


@bookings_bp.route('/<booking_id>', methods=['PUT'])
def update_booking(booking_id):
    """Update booking"""
    try:
        data = request.get_json()
        if not data:
            return error_response("No data provided", 400)

        db = get_db()
        doc_ref = db.collection("bookings").document(booking_id)
        doc = doc_ref.get()

        if not doc.exists:
            return not_found_response("booking", booking_id)

        # Update in Firestore
        doc_ref.update(data)

        # Get updated booking
        updated_doc = doc_ref.get()
        updated_booking = updated_doc.to_dict()
        updated_booking['id'] = updated_doc.id

        return json_response(updated_booking, 200)

    except Exception as e:
        print(f"Error updating booking: {e}")
        return error_response(str(e), 500)


@bookings_bp.route('/<booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    """Delete booking"""
    try:
        db = get_db()
        doc_ref = db.collection("bookings").document(booking_id)
        doc = doc_ref.get()

        if not doc.exists:
            return not_found_response("booking", booking_id)

        doc_ref.delete()

        return json_response({"message": "Booking deleted successfully"}, 200)

    except Exception as e:
        print(f"Error deleting booking: {e}")
        return error_response(str(e), 500)
'''

    with open('routes/bookings_routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Created bookings_routes.py")


def generate_events_routes():
    """Generate events_routes.py blueprint"""
    content = '''"""
Events Routes Blueprint
Handles all event-related endpoints
"""
from flask import Blueprint, request
from datetime import datetime
from database import get_db
from utils.responses import json_response, error_response, created_response, not_found_response
from utils.pagination import paginate_query, create_pagination_response

# Create blueprint
events_bp = Blueprint('events', __name__, url_prefix='/api/events')


@events_bp.route('/', methods=['GET'])
def get_events():
    """Get all events with pagination"""
    try:
        db = get_db()

        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))

        events_ref = db.collection("events").order_by("created_at", direction='DESCENDING')
        paginated_events, has_more, total_showing = paginate_query(events_ref, page, limit)

        response = create_pagination_response(
            items=paginated_events,
            page=page,
            limit=limit,
            has_more=has_more,
            total_showing=total_showing
        )

        return json_response(response, 200)

    except Exception as e:
        print(f"Error getting events: {e}")
        return error_response(str(e), 500)


@events_bp.route('/', methods=['POST'])
def create_event():
    """Create a new event"""
    try:
        data = request.get_json()
        if not data:
            return error_response("No data provided", 400)

        required_fields = ['title', 'event_date']
        for field in required_fields:
            if field not in data:
                return error_response(f"Missing required field: {field}", 400)

        db = get_db()

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
            'is_published': data.get('is_published', False),
            'is_featured': data.get('is_featured', False),
            'category': data.get('category', 'workshop'),
            'satisfaction': data.get('satisfaction', 5),
            'highlight': data.get('highlight', 'Experiencia única'),
            'age_group': data.get('age_group', 'Todas las edades')
        }

        doc_ref = db.collection("events").add(event_data)
        event_id = doc_ref[1].id

        event_data['id'] = event_id

        return created_response("event", event_id, event_data)

    except Exception as e:
        print(f"Error creating event: {e}")
        return error_response(str(e), 500)


@events_bp.route('/<event_id>', methods=['GET'])
def get_event(event_id):
    """Get specific event by ID"""
    try:
        db = get_db()
        doc_ref = db.collection("events").document(event_id)
        doc = doc_ref.get()

        if doc.exists:
            event = doc.to_dict()
            event['id'] = doc.id
            return json_response(event, 200)
        else:
            return not_found_response("event", event_id)

    except Exception as e:
        print(f"Error getting event: {e}")
        return error_response(str(e), 500)


@events_bp.route('/<event_id>', methods=['PUT'])
def update_event(event_id):
    """Update event data"""
    try:
        data = request.get_json()
        if not data:
            return error_response("No data provided", 400)

        db = get_db()
        doc_ref = db.collection("events").document(event_id)
        doc = doc_ref.get()

        if not doc.exists:
            return not_found_response("event", event_id)

        update_data = {}
        updatable_fields = ['title', 'description', 'notes', 'photos', 'final_price', 'event_cost', 'profit']
        for field in updatable_fields:
            if field in data:
                update_data[field] = data[field]

        update_data['updated_at'] = datetime.now()

        doc_ref.update(update_data)

        updated_doc = doc_ref.get()
        updated_event = updated_doc.to_dict()
        updated_event['id'] = updated_doc.id

        return json_response(updated_event, 200)

    except Exception as e:
        print(f"Error updating event: {e}")
        return error_response(str(e), 500)


@events_bp.route('/<event_id>/publish', methods=['PUT', 'OPTIONS'])
def publish_event(event_id):
    """Publish or unpublish an event"""
    if request.method == 'OPTIONS':
        return json_response({'status': 'OK'}, 200)

    try:
        data = request.get_json()
        if not data:
            return error_response("No data provided", 400)

        db = get_db()
        doc_ref = db.collection("events").document(event_id)
        doc = doc_ref.get()

        if not doc.exists:
            return not_found_response("event", event_id)

        update_data = {
            'is_published': data.get('is_published', False),
            'updated_at': datetime.now()
        }

        if 'is_featured' in data:
            update_data['is_featured'] = data['is_featured']

        doc_ref.update(update_data)

        updated_doc = doc_ref.get()
        updated_event = updated_doc.to_dict()
        updated_event['id'] = updated_doc.id

        return json_response(updated_event, 200)

    except Exception as e:
        print(f"Error publishing event: {e}")
        return error_response(str(e), 500)
'''

    with open('routes/events_routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Created events_routes.py")


def generate_gallery_routes():
    """Generate gallery_routes.py blueprint"""
    content = '''"""
Gallery Routes Blueprint
Handles all gallery-related endpoints
"""
from flask import Blueprint, request
from datetime import datetime
from database import get_db
from utils.responses import json_response, error_response, not_found_response
from utils.pagination import paginate_query, create_pagination_response

# Create blueprint
gallery_bp = Blueprint('gallery', __name__, url_prefix='/api/gallery')


@gallery_bp.route('/', methods=['GET'])
def get_gallery_images():
    """Get gallery images with pagination"""
    try:
        event_id = request.args.get('event_id')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 30))

        db = get_db()

        if event_id:
            images_ref = db.collection("gallery").where("event_id", "==", event_id).order_by("uploaded_at", direction='DESCENDING')
        else:
            images_ref = db.collection("gallery").order_by("uploaded_at", direction='DESCENDING')

        paginated_images, has_more, total_showing = paginate_query(images_ref, page, limit)

        gallery_items = []
        for image in paginated_images:
            gallery_item = {
                'id': image.get('id'),
                'title': image.get('title', 'Imagen'),
                'url': image.get('url', ''),
                'is_published': image.get('is_published', False),
                'uploaded_at': image.get('uploaded_at'),
                'event_id': image.get('event_id')
            }
            gallery_items.append(gallery_item)

        response = create_pagination_response(
            items=gallery_items,
            page=page,
            limit=limit,
            has_more=has_more,
            total_showing=total_showing
        )

        return json_response(response, 200)

    except Exception as e:
        print(f"Error getting gallery images: {e}")
        return error_response(str(e), 500)


@gallery_bp.route('/event/<event_id>', methods=['GET', 'OPTIONS'])
def get_gallery_by_event(event_id):
    """Get gallery images for a specific event"""
    if request.method == 'OPTIONS':
        return json_response({'status': 'OK'}, 200)

    try:
        db = get_db()
        if not db:
            return error_response("Database connection failed", 500)

        images_ref = db.collection("gallery").where("event_id", "==", event_id)

        images = []
        for doc in images_ref.stream():
            image = doc.to_dict()
            image['id'] = doc.id
            images.append(image)

        return json_response(images, 200)

    except Exception as e:
        print(f"Error getting gallery by event: {e}")
        return error_response(str(e), 500)


@gallery_bp.route('/<photo_id>/publish', methods=['PUT', 'OPTIONS'])
def publish_gallery_photo(photo_id):
    """Publish or unpublish a gallery photo"""
    if request.method == 'OPTIONS':
        return json_response({'status': 'OK'}, 200)

    try:
        data = request.get_json()
        if not data:
            return error_response("No data provided", 400)

        db = get_db()
        doc_ref = db.collection("gallery").document(photo_id)
        doc = doc_ref.get()

        if not doc.exists:
            return not_found_response("photo", photo_id)

        update_data = {
            'is_published': data.get('is_published', False),
            'updated_at': datetime.now()
        }

        doc_ref.update(update_data)

        updated_doc = doc_ref.get()
        updated_photo = updated_doc.to_dict()
        updated_photo['id'] = updated_doc.id

        return json_response(updated_photo, 200)

    except Exception as e:
        print(f"Error publishing photo: {e}")
        return error_response(str(e), 500)


@gallery_bp.route('/<photo_id>', methods=['DELETE'])
def delete_photo(photo_id):
    """Delete a photo"""
    try:
        db = get_db()
        doc_ref = db.collection("gallery").document(photo_id)
        doc = doc_ref.get()

        if not doc.exists:
            return not_found_response("photo", photo_id)

        doc_ref.delete()

        return json_response({"message": "Photo deleted successfully"}, 200)

    except Exception as e:
        print(f"Error deleting photo: {e}")
        return error_response(str(e), 500)
'''

    with open('routes/gallery_routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Created gallery_routes.py")


def generate_contacts_routes():
    """Generate contacts_routes.py blueprint"""
    content = '''"""
Contacts Routes Blueprint
Handles all contact-related endpoints
"""
from flask import Blueprint, request
import uuid
from datetime import datetime
from database import get_db
from utils.responses import json_response, error_response, created_response, not_found_response
from utils.pagination import paginate_query, create_pagination_response

# Create blueprint
contacts_bp = Blueprint('contacts', __name__, url_prefix='/api/contacts')


@contacts_bp.route('/', methods=['POST'])
def create_contact():
    """Create new contact"""
    try:
        data = request.get_json()
        if not data:
            return error_response("No data provided", 400)

        required_fields = ['name', 'email', 'message']
        for field in required_fields:
            if field not in data:
                return error_response(f"Missing required field: {field}", 400)

        contact_id = str(uuid.uuid4())

        contact_data = {
            "id": contact_id,
            **data,
            "status": "pending",
            "created_at": datetime.now()
        }

        db = get_db()
        db.collection("contacts").document(contact_id).set(contact_data)

        return created_response("contact", contact_id, contact_data)

    except Exception as e:
        print(f"Error creating contact: {e}")
        return error_response(str(e), 500)


@contacts_bp.route('/', methods=['GET'])
def get_contacts():
    """Get all contacts with pagination"""
    try:
        db = get_db()

        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))

        contacts_ref = db.collection("contacts").order_by("created_at", direction='DESCENDING')
        paginated_contacts, has_more, total_showing = paginate_query(contacts_ref, page, limit)

        response = create_pagination_response(
            items=paginated_contacts,
            page=page,
            limit=limit,
            has_more=has_more,
            total_showing=total_showing
        )

        return json_response(response, 200)

    except Exception as e:
        print(f"Error getting contacts: {e}")
        return error_response(str(e), 500)


@contacts_bp.route('/<contact_id>', methods=['GET'])
def get_contact(contact_id):
    """Get specific contact by ID"""
    try:
        db = get_db()
        doc_ref = db.collection("contacts").document(contact_id)
        doc = doc_ref.get()

        if doc.exists:
            contact = doc.to_dict()
            contact['id'] = doc.id
            return json_response(contact, 200)
        else:
            return not_found_response("contact", contact_id)

    except Exception as e:
        print(f"Error getting contact: {e}")
        return error_response(str(e), 500)


@contacts_bp.route('/<contact_id>/respond', methods=['PUT'])
def respond_to_contact(contact_id):
    """Respond to a contact"""
    try:
        data = request.get_json()
        if not data or 'response' not in data:
            return error_response("Response text is required", 400)

        db = get_db()
        doc_ref = db.collection("contacts").document(contact_id)
        doc = doc_ref.get()

        if not doc.exists:
            return not_found_response("contact", contact_id)

        update_data = {
            'status': 'responded',
            'response': data['response'],
            'responded_at': datetime.now()
        }

        doc_ref.update(update_data)

        updated_doc = doc_ref.get()
        updated_contact = updated_doc.to_dict()
        updated_contact['id'] = updated_doc.id

        return json_response(updated_contact, 200)

    except Exception as e:
        print(f"Error responding to contact: {e}")
        return error_response(str(e), 500)


@contacts_bp.route('/<contact_id>', methods=['DELETE'])
def delete_contact(contact_id):
    """Delete contact"""
    try:
        db = get_db()
        doc_ref = db.collection("contacts").document(contact_id)
        doc = doc_ref.get()

        if not doc.exists:
            return not_found_response("contact", contact_id)

        doc_ref.delete()

        return json_response({"message": "Contact deleted successfully"}, 200)

    except Exception as e:
        print(f"Error deleting contact: {e}")
        return error_response(str(e), 500)
'''

    with open('routes/contacts_routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Created contacts_routes.py")


if __name__ == '__main__':
    print("🚀 Generating blueprint files...")
    print()

    # Change to backend directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    generate_bookings_routes()
    generate_events_routes()
    generate_gallery_routes()
    generate_contacts_routes()

    print()
    print("✅ All blueprint files generated successfully!")
    print("📁 Files created in routes/ directory")
