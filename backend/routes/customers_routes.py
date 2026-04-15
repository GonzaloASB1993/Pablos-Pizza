"""Customers Routes Blueprint - API endpoints for customer management"""
from flask import Blueprint, request, jsonify
import uuid
from datetime import datetime
from firebase_admin import firestore
from database import get_db
from utils.pagination import paginate_query, create_pagination_response
from models.customer import CustomerCreate, CustomerUpdate, CustomerResponse, CustomerSearchResult
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)

customers_bp = Blueprint('customers', __name__, url_prefix='/api/customers')


@customers_bp.route('/', methods=['POST'])
def create_customer():
    """Create a new customer

    Request Body:
        - name (str): Customer full name
        - email (str): Customer email (unique)
        - phone (str): Customer phone number
        - address (str, optional): Customer physical address
        - notes (str, optional): Internal notes

    Returns:
        201: Customer created successfully
        400: Validation error
        409: Customer with this email already exists
        500: Internal server error
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate data with Pydantic
        try:
            customer_data = CustomerCreate(**data)
        except ValidationError as e:
            return jsonify({"error": "Validation error", "details": e.errors()}), 400

        db = get_db()
        if not db:
            return jsonify({"error": "Database connection failed"}), 500

        # Check if customer with this email already exists
        existing = db.collection("customers").where("email", "==", customer_data.email).limit(1).get()
        if existing:
            existing_docs = list(existing)
            if existing_docs:
                return jsonify({
                    "error": "Customer with this email already exists",
                    "existing_customer_id": existing_docs[0].id
                }), 409

        # Create customer document
        customer_id = str(uuid.uuid4())
        now = datetime.now()

        customer_doc = {
            "id": customer_id,
            "name": customer_data.name,
            "email": customer_data.email,
            "phone": customer_data.phone,
            "address": customer_data.address,
            "notes": customer_data.notes,
            "total_bookings": 0,
            "last_booking_date": None,
            "created_at": now,
            "updated_at": now
        }

        db.collection("customers").document(customer_id).set(customer_doc)

        logger.info(f"✅ Customer created: {customer_id} - {customer_data.email}")
        return jsonify(customer_doc), 201

    except Exception as e:
        logger.error(f"❌ Error creating customer: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@customers_bp.route('/', methods=['GET'])
def get_customers():
    """Get all customers with pagination and optional filtering

    Query Parameters:
        - page (int): Page number (default: 1)
        - limit (int): Items per page (default: 20, max: 100)
        - search (str): Search query (name, email, or phone)

    Returns:
        200: List of customers with pagination info
        500: Internal server error
    """
    try:
        db = get_db()
        if not db:
            return jsonify({"error": "Database connection failed"}), 500

        # Pagination parameters
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)
        search_query = request.args.get('search', '').strip()

        # Base query
        query = db.collection("customers").order_by('created_at', direction=firestore.Query.DESCENDING)

        # Apply search filter if provided (basic implementation)
        # Note: Firestore doesn't support full-text search natively
        # For production, consider using Algolia or Elastic Search
        customers_list = []
        if search_query:
            # Fetch all customers and filter in memory (not ideal for large datasets)
            all_customers = query.stream()
            search_lower = search_query.lower()

            for doc in all_customers:
                customer = doc.to_dict()
                customer['id'] = doc.id

                # Search in name, email, and phone
                if (search_lower in customer.get('name', '').lower() or
                    search_lower in customer.get('email', '').lower() or
                    search_lower in customer.get('phone', '').lower()):
                    customers_list.append(customer)

            # Manual pagination for filtered results
            total = len(customers_list)
            start = (page - 1) * limit
            end = start + limit
            paginated_customers = customers_list[start:end]
            has_more = end < total

            return jsonify({
                "items": paginated_customers,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "has_more": has_more
                }
            }), 200
        else:
            # Use built-in pagination for non-filtered queries
            paginated_customers, has_more, total = paginate_query(query, page, limit)
            return jsonify(create_pagination_response(paginated_customers, page, limit, has_more, total)), 200

    except Exception as e:
        logger.error(f"❌ Error getting customers: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@customers_bp.route('/search', methods=['GET'])
def search_customers():
    """Search customers by name, email, or phone (optimized for autocomplete)

    Query Parameters:
        - q (str): Search query
        - limit (int): Max results (default: 20)

    Returns:
        200: List of matching customers
        400: Missing query parameter
        500: Internal server error
    """
    try:
        query_string = request.args.get('q', '').strip()
        if not query_string:
            return jsonify({"error": "Query parameter 'q' is required"}), 400

        limit = min(int(request.args.get('limit', 20)), 50)

        db = get_db()
        if not db:
            return jsonify({"error": "Database connection failed"}), 500

        # Fetch all customers (is_active field may not exist on older docs)
        query = db.collection("customers").limit(200)
        all_customers = query.stream()

        search_lower = query_string.lower()
        results = []

        for doc in all_customers:
            customer = doc.to_dict()
            customer['id'] = doc.id

            # Skip explicitly deactivated customers only
            if customer.get('is_active') is False:
                continue

            # Search in name, email, and phone
            if (search_lower in customer.get('name', '').lower() or
                search_lower in customer.get('email', '').lower() or
                search_lower in customer.get('phone', '').lower()):

                # Return simplified result for autocomplete
                results.append({
                    "id": customer['id'],
                    "name": customer.get('name'),
                    "email": customer.get('email'),
                    "phone": customer.get('phone'),
                    "total_bookings": customer.get('total_bookings', 0),
                    "last_booking_date": customer.get('last_booking_date')
                })

                if len(results) >= limit:
                    break

        return jsonify({"results": results, "count": len(results)}), 200

    except Exception as e:
        logger.error(f"❌ Error searching customers: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@customers_bp.route('/<customer_id>', methods=['GET'])
def get_customer(customer_id):
    """Get a single customer by ID

    Path Parameters:
        - customer_id (str): Customer UUID

    Returns:
        200: Customer data
        404: Customer not found
        500: Internal server error
    """
    try:
        db = get_db()
        if not db:
            return jsonify({"error": "Database connection failed"}), 500

        doc = db.collection("customers").document(customer_id).get()

        if not doc.exists:
            return jsonify({"error": "Customer not found"}), 404

        customer = doc.to_dict()
        customer['id'] = doc.id

        return jsonify(customer), 200

    except Exception as e:
        logger.error(f"❌ Error getting customer {customer_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@customers_bp.route('/<customer_id>', methods=['PUT'])
def update_customer(customer_id):
    """Update an existing customer

    Path Parameters:
        - customer_id (str): Customer UUID

    Request Body:
        - name (str, optional): Customer full name
        - email (str, optional): Customer email
        - phone (str, optional): Customer phone number
        - address (str, optional): Customer address
        - notes (str, optional): Internal notes

    Returns:
        200: Customer updated successfully
        400: Validation error
        404: Customer not found
        409: Email already used by another customer
        500: Internal server error
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate data with Pydantic
        try:
            update_data = CustomerUpdate(**data)
        except ValidationError as e:
            return jsonify({"error": "Validation error", "details": e.errors()}), 400

        db = get_db()
        if not db:
            return jsonify({"error": "Database connection failed"}), 500

        doc_ref = db.collection("customers").document(customer_id)
        doc = doc_ref.get()

        if not doc.exists:
            return jsonify({"error": "Customer not found"}), 404

        # Check if email is being changed and if it's already used
        if update_data.email and update_data.email != doc.to_dict().get('email'):
            existing = db.collection("customers").where("email", "==", update_data.email).limit(1).get()
            if existing:
                existing_docs = list(existing)
                if existing_docs and existing_docs[0].id != customer_id:
                    return jsonify({
                        "error": "Email already used by another customer",
                        "existing_customer_id": existing_docs[0].id
                    }), 409

        # Prepare update data (only non-None fields)
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        update_dict['updated_at'] = datetime.now()

        doc_ref.update(update_dict)

        # Return updated customer
        updated_doc = doc_ref.get()
        customer = updated_doc.to_dict()
        customer['id'] = updated_doc.id

        logger.info(f"✅ Customer updated: {customer_id}")
        return jsonify(customer), 200

    except Exception as e:
        logger.error(f"❌ Error updating customer {customer_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@customers_bp.route('/<customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    """Delete a customer (soft delete by marking as inactive)

    Path Parameters:
        - customer_id (str): Customer UUID

    Returns:
        200: Customer deleted successfully
        404: Customer not found
        500: Internal server error
    """
    try:
        db = get_db()
        if not db:
            return jsonify({"error": "Database connection failed"}), 500

        doc_ref = db.collection("customers").document(customer_id)
        doc = doc_ref.get()

        if not doc.exists:
            return jsonify({"error": "Customer not found"}), 404

        # Soft delete: mark as inactive instead of deleting
        # This preserves data integrity with existing bookings
        doc_ref.update({
            "is_active": False,
            "deleted_at": datetime.now(),
            "updated_at": datetime.now()
        })

        logger.info(f"✅ Customer soft-deleted: {customer_id}")
        return jsonify({"message": "Customer deleted successfully"}), 200

    except Exception as e:
        logger.error(f"❌ Error deleting customer {customer_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@customers_bp.route('/<customer_id>/bookings', methods=['GET'])
def get_customer_bookings(customer_id):
    """Get all bookings for a specific customer

    Path Parameters:
        - customer_id (str): Customer UUID

    Query Parameters:
        - page (int): Page number (default: 1)
        - limit (int): Items per page (default: 20)

    Returns:
        200: List of customer's bookings
        404: Customer not found
        500: Internal server error
    """
    try:
        db = get_db()
        if not db:
            return jsonify({"error": "Database connection failed"}), 500

        # Verify customer exists
        customer_doc = db.collection("customers").document(customer_id).get()
        if not customer_doc.exists:
            return jsonify({"error": "Customer not found"}), 404

        # Pagination
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)

        # Query bookings by customer_id
        query = db.collection("bookings").where("customer_id", "==", customer_id).order_by('created_at', direction=firestore.Query.DESCENDING)
        paginated_bookings, has_more, total = paginate_query(query, page, limit)

        return jsonify(create_pagination_response(paginated_bookings, page, limit, has_more, total)), 200

    except Exception as e:
        logger.error(f"❌ Error getting customer bookings: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
