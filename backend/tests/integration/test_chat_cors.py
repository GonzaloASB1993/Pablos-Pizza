"""
Integration tests for Chat CORS functionality
Tests the /api/chat/rooms endpoint and CORS headers functionality
"""
import pytest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


class TestChatCORSIntegration:
    """Integration tests for Chat API endpoints with CORS support"""

    @pytest.mark.integration
    @pytest.mark.chat
    def test_chat_rooms_get_with_cors_headers(self, client, mock_firestore, sample_chat_rooms):
        """Test GET /api/chat/rooms endpoint returns proper CORS headers"""

        # Mock chat rooms data
        mock_docs = []
        for room in sample_chat_rooms:
            mock_doc = MagicMock()
            mock_doc.to_dict.return_value = room
            mock_doc.id = room["id"]
            mock_docs.append(mock_doc)

        # Configure the mock Firestore query chain
        mock_query = MagicMock()
        mock_query.stream.return_value = mock_docs
        mock_firestore['chat_rooms'].order_by.return_value = mock_query

        with patch('main.get_db', return_value=mock_firestore['db']):
            # Make GET request to chat rooms endpoint
            response = client.get('/api/chat/rooms')

            # Verify response status
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            # Verify CORS headers are present
            assert 'Access-Control-Allow-Origin' in response.headers, "CORS Origin header should be present"
            assert 'Access-Control-Allow-Headers' in response.headers, "CORS Headers header should be present"
            assert 'Access-Control-Allow-Methods' in response.headers, "CORS Methods header should be present"

            # Verify CORS values
            assert response.headers['Access-Control-Allow-Origin'] == '*', "Should allow all origins"
            assert 'Content-Type' in response.headers['Access-Control-Allow-Headers'], "Should allow Content-Type"
            assert 'GET' in response.headers['Access-Control-Allow-Methods'], "Should allow GET method"

            # Verify data structure
            data = json.loads(response.data)
            assert isinstance(data, list), "Response should be a list of chat rooms"

    @pytest.mark.integration
    @pytest.mark.chat
    def test_chat_rooms_get_active_only_parameter(self, client, mock_firestore, sample_chat_rooms):
        """Test GET /api/chat/rooms with active_only parameter"""

        # Mock chat rooms data with mixed statuses
        mock_docs = []
        for room in sample_chat_rooms:
            mock_doc = MagicMock()
            mock_doc.to_dict.return_value = room
            mock_doc.id = room["id"]
            mock_docs.append(mock_doc)

        # Configure mock for active_only=true query
        mock_active_query = MagicMock()
        mock_active_docs = [doc for doc in mock_docs if doc.to_dict()['status'] == 'open']
        mock_active_query.stream.return_value = mock_active_docs

        mock_order_query = MagicMock()
        mock_order_query.where.return_value = mock_active_query
        mock_firestore['chat_rooms'].order_by.return_value = mock_order_query

        with patch('main.get_db', return_value=mock_firestore['db']):
            # Test with active_only=true (default)
            response = client.get('/api/chat/rooms?active_only=true')
            assert response.status_code == 200

            data = json.loads(response.data)
            # Should only return active rooms
            active_rooms = [room for room in sample_chat_rooms if room['status'] == 'open']
            assert len(data) == len(active_rooms), f"Expected {len(active_rooms)} active rooms"

            # Verify all returned rooms have is_active=True or status='open'
            for room in data:
                assert room.get('status') == 'open' or room.get('is_active') == True, \
                    f"Room {room['id']} should be active"

    @pytest.mark.integration
    @pytest.mark.chat
    def test_chat_rooms_get_all_rooms(self, client, mock_firestore, sample_chat_rooms):
        """Test GET /api/chat/rooms with active_only=false"""

        # Mock all chat rooms
        mock_docs = []
        for room in sample_chat_rooms:
            mock_doc = MagicMock()
            mock_doc.to_dict.return_value = room
            mock_doc.id = room["id"]
            mock_docs.append(mock_doc)

        # Configure mock for active_only=false query (no status filter)
        mock_query = MagicMock()
        mock_query.stream.return_value = mock_docs
        mock_firestore['chat_rooms'].order_by.return_value = mock_query

        with patch('main.get_db', return_value=mock_firestore['db']):
            # Test with active_only=false
            response = client.get('/api/chat/rooms?active_only=false')
            assert response.status_code == 200

            data = json.loads(response.data)
            # Should return all rooms
            assert len(data) == len(sample_chat_rooms), f"Expected {len(sample_chat_rooms)} total rooms"

            # Should include both active and closed rooms
            statuses = {room['status'] for room in data}
            assert 'open' in statuses, "Should include open rooms"
            assert 'closed' in statuses, "Should include closed rooms"

    @pytest.mark.integration
    @pytest.mark.chat
    def test_chat_rooms_post_create_room(self, client, mock_firestore):
        """Test POST /api/chat/rooms to create a new chat room"""

        # Mock Firestore document creation
        mock_doc_ref = MagicMock()
        mock_firestore['chat_rooms'].document.return_value = mock_doc_ref

        room_data = {
            "client_name": "Test Client",
            "client_email": "test@example.com"
        }

        with patch('main.get_db', return_value=mock_firestore['db']):
            response = client.post('/api/chat/rooms',
                                 data=json.dumps(room_data),
                                 content_type='application/json')

            # Verify response
            assert response.status_code == 201, f"Expected 201, got {response.status_code}"

            # Verify CORS headers
            assert 'Access-Control-Allow-Origin' in response.headers
            assert response.headers['Access-Control-Allow-Origin'] == '*'

            # Verify response data structure
            data = json.loads(response.data)
            assert 'id' in data, "Response should include room ID"
            assert data['client_name'] == room_data['client_name']
            assert data['client_email'] == room_data['client_email']
            assert data['status'] == 'open', "New room should be open"
            assert 'created_at' in data

            # Verify Firestore was called to create document
            mock_firestore['chat_rooms'].document.assert_called_once()
            mock_doc_ref.set.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.chat
    def test_chat_rooms_options_preflight(self, client):
        """Test OPTIONS preflight request for CORS"""

        response = client.options('/api/chat/rooms')

        # Verify preflight response
        assert response.status_code == 200, f"Expected 200 for OPTIONS, got {response.status_code}"

        # Verify CORS preflight headers
        assert 'Access-Control-Allow-Origin' in response.headers
        assert 'Access-Control-Allow-Headers' in response.headers
        assert 'Access-Control-Allow-Methods' in response.headers

        # Verify allowed methods
        allowed_methods = response.headers.get('Access-Control-Allow-Methods', '')
        assert 'GET' in allowed_methods, "Should allow GET method"
        assert 'POST' in allowed_methods, "Should allow POST method"
        assert 'OPTIONS' in allowed_methods, "Should allow OPTIONS method"

        # Verify allowed headers
        allowed_headers = response.headers.get('Access-Control-Allow-Headers', '')
        assert 'Content-Type' in allowed_headers, "Should allow Content-Type header"

    @pytest.mark.integration
    @pytest.mark.chat
    def test_chat_room_messages_endpoint(self, client, mock_firestore):
        """Test GET /api/chat/rooms/{room_id}/messages endpoint"""

        room_id = "test-room-123"
        sample_messages = [
            {
                "id": "msg-1",
                "room_id": room_id,
                "message": "Hello, I need help with my booking",
                "sender_name": "Test Client",
                "is_admin": False,
                "created_at": datetime.now()
            },
            {
                "id": "msg-2",
                "room_id": room_id,
                "message": "Hello! How can I help you?",
                "sender_name": "Admin",
                "is_admin": True,
                "created_at": datetime.now()
            }
        ]

        # Mock message documents
        mock_docs = []
        for msg in sample_messages:
            mock_doc = MagicMock()
            mock_doc.to_dict.return_value = msg
            mock_doc.id = msg["id"]
            mock_docs.append(mock_doc)

        # Configure mock query chain
        mock_order_query = MagicMock()
        mock_order_query.stream.return_value = mock_docs

        mock_where_query = MagicMock()
        mock_where_query.order_by.return_value = mock_order_query

        mock_firestore['chat_messages'].where.return_value = mock_where_query

        with patch('main.get_db', return_value=mock_firestore['db']):
            response = client.get(f'/api/chat/rooms/{room_id}/messages')

            # Verify response
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            # Verify CORS headers
            assert 'Access-Control-Allow-Origin' in response.headers

            # Verify data structure
            data = json.loads(response.data)
            assert isinstance(data, list), "Should return list of messages"
            assert len(data) == len(sample_messages), f"Expected {len(sample_messages)} messages"

            # Verify message structure
            for message in data:
                assert 'id' in message
                assert 'room_id' in message
                assert 'message' in message
                assert 'sender_name' in message
                assert 'is_admin' in message

    @pytest.mark.integration
    @pytest.mark.chat
    def test_chat_rooms_error_handling(self, client):
        """Test error handling and CORS headers in error responses"""

        with patch('main.get_db', return_value=None):  # Simulate database connection failure
            response = client.get('/api/chat/rooms')

            # Should return error but still have CORS headers
            assert response.status_code == 500, f"Expected 500, got {response.status_code}"
            assert 'Access-Control-Allow-Origin' in response.headers, "CORS headers should be present even in errors"

            # Verify error response structure
            data = json.loads(response.data)
            assert 'error' in data, "Error response should contain error message"

    @pytest.mark.integration
    @pytest.mark.chat
    def test_chat_room_creation_validation(self, client, mock_firestore):
        """Test chat room creation with invalid data"""

        # Test missing required fields
        invalid_data = {
            "client_name": "Test Client"
            # Missing client_email
        }

        with patch('main.get_db', return_value=mock_firestore['db']):
            response = client.post('/api/chat/rooms',
                                 data=json.dumps(invalid_data),
                                 content_type='application/json')

            # Should return validation error
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"

            # Verify CORS headers are still present
            assert 'Access-Control-Allow-Origin' in response.headers

            # Verify error message
            data = json.loads(response.data)
            assert 'error' in data
            assert 'client_email' in data['error'], "Error should mention missing client_email"

    @pytest.mark.integration
    @pytest.mark.chat
    def test_chat_room_data_structure_compatibility(self, client, mock_firestore):
        """Test that chat room data structure matches frontend expectations"""

        sample_room_data = {
            "id": "room-123",
            "client_name": "Frontend Test Client",
            "client_email": "frontend@example.com",
            "status": "open",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "messages_count": 5
        }

        # Mock document
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = sample_room_data
        mock_doc.id = sample_room_data["id"]

        # Configure mock query
        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_doc]
        mock_firestore['chat_rooms'].order_by.return_value = mock_query

        with patch('main.get_db', return_value=mock_firestore['db']):
            response = client.get('/api/chat/rooms')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert len(data) == 1

            room = data[0]
            # Verify expected fields for frontend compatibility
            assert 'id' in room
            assert 'client_name' in room
            assert 'client_email' in room
            assert 'status' in room
            assert 'is_active' in room  # Should be added by backend logic
            assert 'messages_count' in room

            # Verify is_active field is properly set based on status
            expected_is_active = sample_room_data['status'] == 'open'
            assert room['is_active'] == expected_is_active, f"is_active should be {expected_is_active}"

    @pytest.mark.integration
    @pytest.mark.chat
    def test_chat_cors_with_multiple_origins(self, client, mock_firestore):
        """Test CORS handling with different origin headers"""

        # Mock empty response for simplicity
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_firestore['chat_rooms'].order_by.return_value = mock_query

        allowed_origins = [
            'https://pablospizza.web.app',
            'https://pablospizza.firebaseapp.com',
            'http://localhost:5173'
        ]

        with patch('main.get_db', return_value=mock_firestore['db']):
            for origin in allowed_origins:
                response = client.get('/api/chat/rooms',
                                    headers={'Origin': origin})

                assert response.status_code == 200
                # Should allow all origins (configured with '*')
                assert response.headers.get('Access-Control-Allow-Origin') == '*'

    @pytest.mark.integration
    @pytest.mark.chat
    def test_chat_performance_with_large_room_list(self, client, mock_firestore):
        """Test chat rooms endpoint performance with large number of rooms"""

        # Generate large number of chat rooms
        large_room_set = []
        for i in range(200):  # 200 rooms
            room = {
                "id": f"room-{i}",
                "client_name": f"Client {i}",
                "client_email": f"client{i}@example.com",
                "status": "open" if i % 3 == 0 else "closed",
                "created_at": datetime.now(),
                "messages_count": i % 10
            }
            large_room_set.append(room)

        # Mock documents
        mock_docs = []
        for room in large_room_set:
            mock_doc = MagicMock()
            mock_doc.to_dict.return_value = room
            mock_doc.id = room["id"]
            mock_docs.append(mock_doc)

        mock_query = MagicMock()
        mock_query.stream.return_value = mock_docs
        mock_firestore['chat_rooms'].order_by.return_value = mock_query

        with patch('main.get_db', return_value=mock_firestore['db']):
            import time
            start_time = time.time()

            response = client.get('/api/chat/rooms?active_only=false')

            end_time = time.time()
            response_time = end_time - start_time

            # Performance assertions
            assert response.status_code == 200
            assert response_time < 2.0, f"Response took too long: {response_time}s"

            data = json.loads(response.data)
            assert len(data) == 200, "Should return all rooms"

            # Verify CORS headers are still present with large response
            assert 'Access-Control-Allow-Origin' in response.headers