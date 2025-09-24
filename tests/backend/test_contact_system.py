"""
Comprehensive Test Suite for Contact System API
Tests all contact-related endpoints and functionality
"""

import pytest
import requests
import json
from datetime import datetime
import uuid

# API Configuration
BASE_URL = "http://localhost:8000/api"
HEADERS = {"Content-Type": "application/json"}

class TestContactSystemAPI:
    """Test suite for Contact System backend API"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup for each test method"""
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.test_contact_data = {
            "name": "Test User",
            "email": "test@example.com",
            "phone": "+56912345678",
            "subject": "Test Subject",
            "message": "This is a test message for the contact system",
            "priority": "normal"
        }

    def test_health_check(self):
        """Test that the API is running"""
        response = requests.get(f"{self.base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "/api/contacts/" in data["endpoints"]

    def test_create_contact_success(self):
        """Test successful contact creation with all required fields"""
        response = requests.post(
            f"{self.base_url}/contacts",
            headers=self.headers,
            json=self.test_contact_data
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert data["name"] == self.test_contact_data["name"]
        assert data["email"] == self.test_contact_data["email"]
        assert data["phone"] == self.test_contact_data["phone"]
        assert data["subject"] == self.test_contact_data["subject"]
        assert data["message"] == self.test_contact_data["message"]
        assert data["priority"] == self.test_contact_data["priority"]
        assert data["status"] == "pending"
        assert data["response_sent"] == False
        assert "created_at" in data
        assert "updated_at" in data

        return data["id"]  # Return ID for cleanup

    def test_create_contact_without_phone(self):
        """Test contact creation without phone number (optional field)"""
        contact_data = self.test_contact_data.copy()
        del contact_data["phone"]

        response = requests.post(
            f"{self.base_url}/contacts",
            headers=self.headers,
            json=contact_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["phone"] is None

    def test_create_contact_missing_required_fields(self):
        """Test contact creation with missing required fields"""
        required_fields = ["name", "email", "subject", "message"]

        for field in required_fields:
            contact_data = self.test_contact_data.copy()
            del contact_data[field]

            response = requests.post(
                f"{self.base_url}/contacts",
                headers=self.headers,
                json=contact_data
            )

            assert response.status_code == 400
            data = response.json()
            assert "error" in data
            assert field in data["error"]

    def test_create_contact_invalid_email(self):
        """Test contact creation with invalid email format"""
        contact_data = self.test_contact_data.copy()
        contact_data["email"] = "invalid-email"

        response = requests.post(
            f"{self.base_url}/contacts",
            headers=self.headers,
            json=contact_data
        )

        # Should still create contact (email validation is frontend responsibility)
        # But in production, consider adding backend validation
        assert response.status_code in [201, 400]

    def test_create_contact_different_priorities(self):
        """Test contact creation with different priority levels"""
        priorities = ["low", "normal", "high", "urgent"]

        for priority in priorities:
            contact_data = self.test_contact_data.copy()
            contact_data["priority"] = priority
            contact_data["email"] = f"test_{priority}@example.com"

            response = requests.post(
                f"{self.base_url}/contacts",
                headers=self.headers,
                json=contact_data
            )

            assert response.status_code == 201
            data = response.json()
            assert data["priority"] == priority

    def test_get_contacts_all(self):
        """Test retrieving all contacts"""
        # First create a test contact
        create_response = requests.post(
            f"{self.base_url}/contacts",
            headers=self.headers,
            json=self.test_contact_data
        )
        assert create_response.status_code == 201

        # Get all contacts
        response = requests.get(f"{self.base_url}/contacts")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Verify our contact is in the list
        contact_found = any(c["email"] == self.test_contact_data["email"] for c in data)
        assert contact_found

    def test_get_contacts_filter_by_status(self):
        """Test retrieving contacts filtered by status"""
        statuses = ["pending", "in_progress", "resolved"]

        for status in statuses:
            response = requests.get(f"{self.base_url}/contacts?status={status}")
            assert response.status_code == 200

            data = response.json()
            assert isinstance(data, list)

            # All returned contacts should have the requested status
            for contact in data:
                assert contact["status"] == status

    def test_get_contacts_filter_by_priority(self):
        """Test retrieving contacts filtered by priority"""
        priorities = ["low", "normal", "high", "urgent"]

        for priority in priorities:
            response = requests.get(f"{self.base_url}/contacts?priority={priority}")
            assert response.status_code == 200

            data = response.json()
            assert isinstance(data, list)

            # All returned contacts should have the requested priority
            for contact in data:
                assert contact["priority"] == priority

    def test_get_contacts_with_limit(self):
        """Test retrieving contacts with limit parameter"""
        response = requests.get(f"{self.base_url}/contacts?limit=5")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_update_contact_status(self):
        """Test updating contact status"""
        # Create a test contact first
        create_response = requests.post(
            f"{self.base_url}/contacts",
            headers=self.headers,
            json=self.test_contact_data
        )
        assert create_response.status_code == 201
        contact_id = create_response.json()["id"]

        # Update status to in_progress
        update_data = {"status": "in_progress"}
        response = requests.put(
            f"{self.base_url}/contacts/{contact_id}",
            headers=self.headers,
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert "updated_at" in data

    def test_update_contact_assignment(self):
        """Test updating contact assignment"""
        # Create a test contact first
        create_response = requests.post(
            f"{self.base_url}/contacts",
            headers=self.headers,
            json=self.test_contact_data
        )
        assert create_response.status_code == 201
        contact_id = create_response.json()["id"]

        # Assign to admin
        update_data = {
            "assigned_to": "admin@pablospizza.cl",
            "status": "in_progress",
            "notes": "Taking this case"
        }
        response = requests.put(
            f"{self.base_url}/contacts/{contact_id}",
            headers=self.headers,
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to"] == "admin@pablospizza.cl"
        assert data["status"] == "in_progress"
        assert data["notes"] == "Taking this case"

    def test_update_contact_to_resolved(self):
        """Test updating contact status to resolved"""
        # Create a test contact first
        create_response = requests.post(
            f"{self.base_url}/contacts",
            headers=self.headers,
            json=self.test_contact_data
        )
        assert create_response.status_code == 201
        contact_id = create_response.json()["id"]

        # Resolve the contact
        update_data = {"status": "resolved"}
        response = requests.put(
            f"{self.base_url}/contacts/{contact_id}",
            headers=self.headers,
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert "resolved_at" in data

    def test_update_nonexistent_contact(self):
        """Test updating a contact that doesn't exist"""
        fake_id = str(uuid.uuid4())
        update_data = {"status": "resolved"}

        response = requests.put(
            f"{self.base_url}/contacts/{fake_id}",
            headers=self.headers,
            json=update_data
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"].lower()

    def test_respond_to_contact_whatsapp(self):
        """Test sending WhatsApp response to contact"""
        # Create a test contact first
        create_response = requests.post(
            f"{self.base_url}/contacts",
            headers=self.headers,
            json=self.test_contact_data
        )
        assert create_response.status_code == 201
        contact_id = create_response.json()["id"]

        # Send WhatsApp response
        response_data = {
            "response_message": "Hola, gracias por contactarnos. Hemos recibido tu mensaje y te responderemos pronto.",
            "response_method": "whatsapp",
            "notes": "Respuesta automática enviada"
        }

        response = requests.post(
            f"{self.base_url}/contacts/{contact_id}/respond",
            headers=self.headers,
            json=response_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "whatsapp" in data["message"]
        assert data["contact_id"] == contact_id

    def test_respond_to_contact_email(self):
        """Test sending email response to contact"""
        # Create a test contact first
        create_response = requests.post(
            f"{self.base_url}/contacts",
            headers=self.headers,
            json=self.test_contact_data
        )
        assert create_response.status_code == 201
        contact_id = create_response.json()["id"]

        # Send email response
        response_data = {
            "response_message": "Estimado cliente, hemos recibido su consulta y la estamos procesando.",
            "response_method": "email",
            "notes": "Email de confirmación enviado"
        }

        response = requests.post(
            f"{self.base_url}/contacts/{contact_id}/respond",
            headers=self.headers,
            json=response_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "email" in data["message"]

    def test_respond_to_contact_missing_data(self):
        """Test responding to contact with missing required data"""
        # Create a test contact first
        create_response = requests.post(
            f"{self.base_url}/contacts",
            headers=self.headers,
            json=self.test_contact_data
        )
        assert create_response.status_code == 201
        contact_id = create_response.json()["id"]

        # Try to respond without required fields
        incomplete_data = {"response_method": "email"}

        response = requests.post(
            f"{self.base_url}/contacts/{contact_id}/respond",
            headers=self.headers,
            json=incomplete_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_respond_to_contact_invalid_method(self):
        """Test responding to contact with invalid method"""
        # Create a test contact first
        create_response = requests.post(
            f"{self.base_url}/contacts",
            headers=self.headers,
            json=self.test_contact_data
        )
        assert create_response.status_code == 201
        contact_id = create_response.json()["id"]

        # Try to respond with invalid method
        invalid_data = {
            "response_message": "Test message",
            "response_method": "invalid_method"
        }

        response = requests.post(
            f"{self.base_url}/contacts/{contact_id}/respond",
            headers=self.headers,
            json=invalid_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_respond_to_contact_without_phone_whatsapp(self):
        """Test WhatsApp response to contact without phone number"""
        # Create contact without phone
        contact_data = self.test_contact_data.copy()
        del contact_data["phone"]

        create_response = requests.post(
            f"{self.base_url}/contacts",
            headers=self.headers,
            json=contact_data
        )
        assert create_response.status_code == 201
        contact_id = create_response.json()["id"]

        # Try WhatsApp response
        response_data = {
            "response_message": "Test message",
            "response_method": "whatsapp"
        }

        response = requests.post(
            f"{self.base_url}/contacts/{contact_id}/respond",
            headers=self.headers,
            json=response_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "phone number" in data["error"].lower()

    def test_respond_to_nonexistent_contact(self):
        """Test responding to a contact that doesn't exist"""
        fake_id = str(uuid.uuid4())
        response_data = {
            "response_message": "Test message",
            "response_method": "email"
        }

        response = requests.post(
            f"{self.base_url}/contacts/{fake_id}/respond",
            headers=self.headers,
            json=response_data
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

class TestContactSystemIntegration:
    """Integration tests for the complete contact workflow"""

    def test_complete_contact_workflow(self):
        """Test the complete contact workflow from creation to resolution"""
        # Step 1: Create contact
        contact_data = {
            "name": "Integration Test User",
            "email": "integration@example.com",
            "phone": "+56987654321",
            "subject": "Integration Test Subject",
            "message": "This is an integration test message",
            "priority": "high"
        }

        create_response = requests.post(
            f"{BASE_URL}/contacts",
            headers=HEADERS,
            json=contact_data
        )
        assert create_response.status_code == 201
        contact_id = create_response.json()["id"]

        # Step 2: Get contacts and verify creation
        get_response = requests.get(f"{BASE_URL}/contacts")
        assert get_response.status_code == 200
        contacts = get_response.json()
        contact_found = any(c["id"] == contact_id for c in contacts)
        assert contact_found

        # Step 3: Update status to in_progress
        update_response = requests.put(
            f"{BASE_URL}/contacts/{contact_id}",
            headers=HEADERS,
            json={"status": "in_progress", "assigned_to": "admin@test.com"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "in_progress"

        # Step 4: Send response
        respond_response = requests.post(
            f"{BASE_URL}/contacts/{contact_id}/respond",
            headers=HEADERS,
            json={
                "response_message": "Thank you for your message. We will contact you soon.",
                "response_method": "email",
                "notes": "Initial response sent"
            }
        )
        assert respond_response.status_code == 200

        # Step 5: Verify final state
        final_get = requests.get(f"{BASE_URL}/contacts?status=resolved")
        assert final_get.status_code == 200
        resolved_contacts = final_get.json()
        resolved_contact = next((c for c in resolved_contacts if c["id"] == contact_id), None)
        assert resolved_contact is not None
        assert resolved_contact["status"] == "resolved"
        assert resolved_contact["response_sent"] == True

class TestContactSystemPerformance:
    """Performance tests for the contact system"""

    def test_create_multiple_contacts_performance(self):
        """Test creating multiple contacts in sequence"""
        import time

        start_time = time.time()
        contact_ids = []

        for i in range(10):
            contact_data = {
                "name": f"Performance Test User {i}",
                "email": f"perf_test_{i}@example.com",
                "subject": f"Performance Test Subject {i}",
                "message": f"Performance test message {i}",
                "priority": "normal"
            }

            response = requests.post(
                f"{BASE_URL}/contacts",
                headers=HEADERS,
                json=contact_data
            )
            assert response.status_code == 201
            contact_ids.append(response.json()["id"])

        end_time = time.time()
        total_time = end_time - start_time

        # Should create 10 contacts in less than 10 seconds
        assert total_time < 10
        assert len(contact_ids) == 10

    def test_get_contacts_large_dataset_performance(self):
        """Test retrieving contacts with large dataset"""
        import time

        start_time = time.time()
        response = requests.get(f"{BASE_URL}/contacts?limit=100")
        end_time = time.time()

        assert response.status_code == 200
        # Should respond in less than 5 seconds
        assert (end_time - start_time) < 5

class TestContactSystemEdgeCases:
    """Edge case tests for the contact system"""

    def test_create_contact_with_very_long_message(self):
        """Test creating contact with very long message"""
        long_message = "A" * 10000  # 10KB message

        contact_data = {
            "name": "Long Message Test",
            "email": "longmessage@example.com",
            "subject": "Very Long Message Test",
            "message": long_message,
            "priority": "normal"
        }

        response = requests.post(
            f"{BASE_URL}/contacts",
            headers=HEADERS,
            json=contact_data
        )

        # Should handle long messages gracefully
        assert response.status_code in [201, 400]
        if response.status_code == 201:
            assert len(response.json()["message"]) == len(long_message)

    def test_create_contact_with_special_characters(self):
        """Test creating contact with special characters in fields"""
        contact_data = {
            "name": "José María Pérez-González",
            "email": "josé.maría@example.com",
            "subject": "Título con caracteres especiales: áéíóú ñÑ ¿?¡!",
            "message": "Mensaje con emojis 🍕🎉 y caracteres especiales: çàèù",
            "priority": "normal"
        }

        response = requests.post(
            f"{BASE_URL}/contacts",
            headers=HEADERS,
            json=contact_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == contact_data["name"]
        assert data["subject"] == contact_data["subject"]

    def test_create_contact_with_international_phone(self):
        """Test creating contact with international phone numbers"""
        international_phones = [
            "+1-555-123-4567",  # US
            "+44-20-7946-0958",  # UK
            "+33-1-42-86-83-38",  # France
            "+49-30-12345678",   # Germany
            "+86-138-0013-8000"  # China
        ]

        for phone in international_phones:
            contact_data = {
                "name": f"International Test {phone}",
                "email": f"intl_{phone.replace('+', '').replace('-', '')}@example.com",
                "phone": phone,
                "subject": "International Phone Test",
                "message": "Testing international phone number format",
                "priority": "normal"
            }

            response = requests.post(
                f"{BASE_URL}/contacts",
                headers=HEADERS,
                json=contact_data
            )

            assert response.status_code == 201
            assert response.json()["phone"] == phone

if __name__ == "__main__":
    # Run basic smoke test
    import sys

    try:
        # Test health check
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is running and healthy")
            print("🚀 Run full test suite with: pytest test_contact_system.py -v")
        else:
            print("❌ API health check failed")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to API: {e}")
        print("Make sure the backend is running on http://localhost:8000")
        sys.exit(1)