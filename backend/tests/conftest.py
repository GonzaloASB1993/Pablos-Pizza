"""
Test configuration and fixtures for Pablo's Pizza Backend Tests
"""
import pytest
import os
from unittest.mock import MagicMock, patch
from datetime import datetime, date
import sys

# Add the parent directory to Python path so we can import main
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture
def mock_firestore():
    """Mock Firestore client with common test data"""
    mock_db = MagicMock()

    # Mock collections
    mock_bookings = MagicMock()
    mock_events = MagicMock()
    mock_chat_rooms = MagicMock()
    mock_chat_messages = MagicMock()

    # Configure collection returns
    def collection_side_effect(collection_name):
        if collection_name == "bookings":
            return mock_bookings
        elif collection_name == "events":
            return mock_events
        elif collection_name == "chat_rooms":
            return mock_chat_rooms
        elif collection_name == "chat_messages":
            return mock_chat_messages
        else:
            return MagicMock()

    mock_db.collection.side_effect = collection_side_effect

    return {
        'db': mock_db,
        'bookings': mock_bookings,
        'events': mock_events,
        'chat_rooms': mock_chat_rooms,
        'chat_messages': mock_chat_messages
    }

@pytest.fixture
def sample_booking_data():
    """Sample booking data for testing"""
    return {
        "id": "booking-123",
        "client_name": "Test Client",
        "client_email": "test@example.com",
        "client_phone": "+56912345678",
        "service_type": "workshop",
        "participants": 25,
        "event_date": "2025-10-15",
        "event_time": "14:00",
        "location": "Test Location",
        "estimated_price": 193000,
        "status": "confirmed",
        "created_at": datetime(2025, 9, 1),
        "special_requests": "Test special request"
    }

@pytest.fixture
def sample_confirmed_booking_193k():
    """Sample confirmed booking worth $193,000 for October 2025"""
    return {
        "id": "booking-193k",
        "client_name": "Large Corporate Event",
        "client_email": "corporate@bigcompany.com",
        "client_phone": "+56987654321",
        "service_type": "workshop",
        "participants": 143,  # Large group that would justify $193k
        "event_date": "2025-10-20",
        "event_time": "10:00",
        "location": "Corporate Headquarters",
        "estimated_price": 193000,
        "status": "confirmed",
        "created_at": datetime(2025, 8, 15),
        "special_requests": "Large corporate team building event"
    }

@pytest.fixture
def sample_future_bookings():
    """Sample future bookings with various statuses for testing revenue calculation"""
    return [
        {
            "id": "future-confirmed-1",
            "client_name": "Future Client 1",
            "client_email": "future1@example.com",
            "service_type": "pizza_party",
            "participants": 15,
            "event_date": "2025-11-10",
            "estimated_price": 85000,
            "status": "confirmed",
            "created_at": datetime(2025, 9, 1)
        },
        {
            "id": "future-confirmed-2",
            "client_name": "Future Client 2",
            "client_email": "future2@example.com",
            "service_type": "workshop",
            "participants": 20,
            "event_date": "2025-12-05",
            "estimated_price": 120000,
            "status": "confirmed",
            "created_at": datetime(2025, 9, 1)
        },
        {
            "id": "future-pending",
            "client_name": "Pending Client",
            "client_email": "pending@example.com",
            "service_type": "workshop",
            "participants": 30,
            "event_date": "2025-11-20",
            "estimated_price": 150000,
            "status": "pending",  # Should NOT be included in revenue
            "created_at": datetime(2025, 9, 1)
        }
    ]

@pytest.fixture
def sample_chat_rooms():
    """Sample chat room data for testing"""
    return [
        {
            "id": "room-1",
            "client_name": "Test Client 1",
            "client_email": "client1@example.com",
            "status": "open",
            "created_at": datetime(2025, 9, 1),
            "updated_at": datetime(2025, 9, 1),
            "messages_count": 3
        },
        {
            "id": "room-2",
            "client_name": "Test Client 2",
            "client_email": "client2@example.com",
            "status": "open",
            "created_at": datetime(2025, 9, 2),
            "updated_at": datetime(2025, 9, 2),
            "messages_count": 1
        },
        {
            "id": "room-3",
            "client_name": "Closed Client",
            "client_email": "closed@example.com",
            "status": "closed",
            "created_at": datetime(2025, 8, 15),
            "updated_at": datetime(2025, 8, 20),
            "messages_count": 5
        }
    ]

@pytest.fixture
def flask_app():
    """Create Flask app instance for testing"""
    with patch('main.get_db') as mock_get_db:
        mock_get_db.return_value = None  # Mock database connection

        # Import main after mocking get_db to avoid Firebase initialization
        import main
        app = main.app
        app.config['TESTING'] = True

        return app

@pytest.fixture
def client(flask_app):
    """Create test client"""
    return flask_app.test_client()

@pytest.fixture
def mock_firebase_admin():
    """Mock Firebase Admin SDK"""
    with patch('firebase_admin._apps', [MagicMock()]):
        with patch('firebase_admin.firestore.client') as mock_client:
            yield mock_client

# Environment variable fixtures
@pytest.fixture
def mock_environment_variables():
    """Mock environment variables"""
    env_vars = {
        'DEFAULT_WORKSHOP_PRICE': '13500',
        'DEFAULT_PIZZA_PARTY_PRICE': '11990',
        'ENVIRONMENT': 'test',
        'EMAIL_USERNAME': 'test@example.com',
        'EMAIL_PASSWORD': 'test_password',
        'EMAIL_FROM': 'test@example.com',
        'ADMIN_WHATSAPP_NUMBER': '+56989424566',
        'PARTNER_WHATSAPP_NUMBER': '+56961093818'
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars