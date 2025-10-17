"""Fixed and Variable Expenses Routes Blueprint"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_db
from firebase_admin import firestore
import uuid

expenses_bp = Blueprint('expenses', __name__, url_prefix='/api/expenses')

@expenses_bp.route('/fixed', methods=['GET'])
def get_fixed_expenses():
    """Get all fixed expenses"""
    try:
        db = get_db()
        expenses = db.collection("fixed_expenses").order_by("created_at", direction=firestore.Query.DESCENDING).get()

        result = []
        for expense in expenses:
            data = expense.to_dict()
            data['id'] = expense.id
            result.append(data)

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@expenses_bp.route('/fixed', methods=['POST'])
def create_fixed_expense():
    """Create a new fixed expense"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400

        required_fields = ['description', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing {field}"}), 400

        db = get_db()
        expense_id = str(uuid.uuid4())

        expense_data = {
            'id': expense_id,
            'description': data['description'],
            'amount': float(data['amount']),
            'category': data.get('category', 'general'),
            'notes': data.get('notes', ''),
            'is_active': data.get('is_active', True),
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }

        db.collection("fixed_expenses").document(expense_id).set(expense_data)

        return jsonify(expense_data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@expenses_bp.route('/fixed/<expense_id>', methods=['PUT'])
def update_fixed_expense(expense_id):
    """Update a fixed expense"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400

        db = get_db()
        doc_ref = db.collection("fixed_expenses").document(expense_id)

        if not doc_ref.get().exists:
            return jsonify({"error": "Not found"}), 404

        update_data = {
            'updated_at': datetime.now()
        }

        if 'description' in data:
            update_data['description'] = data['description']
        if 'amount' in data:
            update_data['amount'] = float(data['amount'])
        if 'category' in data:
            update_data['category'] = data['category']
        if 'notes' in data:
            update_data['notes'] = data['notes']
        if 'is_active' in data:
            update_data['is_active'] = data['is_active']

        doc_ref.update(update_data)

        updated = doc_ref.get().to_dict()
        updated['id'] = expense_id

        return jsonify(updated), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@expenses_bp.route('/fixed/<expense_id>', methods=['DELETE'])
def delete_fixed_expense(expense_id):
    """Delete a fixed expense"""
    try:
        db = get_db()
        doc_ref = db.collection("fixed_expenses").document(expense_id)

        if not doc_ref.get().exists:
            return jsonify({"error": "Not found"}), 404

        doc_ref.delete()

        return jsonify({"message": "Deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@expenses_bp.route('/variable', methods=['GET'])
def get_variable_expenses():
    """Get variable expenses with optional month/year filtering"""
    try:
        db = get_db()
        month = request.args.get('month')  # 1-12
        year = request.args.get('year')

        query = db.collection("variable_expenses")

        if year and month:
            query = query.where("year", "==", int(year)).where("month", "==", int(month))
        elif year:
            query = query.where("year", "==", int(year))

        expenses = query.order_by("created_at", direction=firestore.Query.DESCENDING).get()

        result = []
        for expense in expenses:
            data = expense.to_dict()
            data['id'] = expense.id
            result.append(data)

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@expenses_bp.route('/variable', methods=['POST'])
def create_variable_expense():
    """Create a new variable expense"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400

        required_fields = ['description', 'amount', 'year', 'month']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing {field}"}), 400

        db = get_db()
        expense_id = str(uuid.uuid4())

        expense_data = {
            'id': expense_id,
            'description': data['description'],
            'amount': float(data['amount']),
            'category': data.get('category', 'general'),
            'notes': data.get('notes', ''),
            'year': int(data['year']),
            'month': int(data['month']),
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }

        db.collection("variable_expenses").document(expense_id).set(expense_data)

        return jsonify(expense_data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@expenses_bp.route('/variable/<expense_id>', methods=['PUT'])
def update_variable_expense(expense_id):
    """Update a variable expense"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400

        db = get_db()
        doc_ref = db.collection("variable_expenses").document(expense_id)

        if not doc_ref.get().exists:
            return jsonify({"error": "Not found"}), 404

        update_data = {
            'updated_at': datetime.now()
        }

        if 'description' in data:
            update_data['description'] = data['description']
        if 'amount' in data:
            update_data['amount'] = float(data['amount'])
        if 'category' in data:
            update_data['category'] = data['category']
        if 'notes' in data:
            update_data['notes'] = data['notes']
        if 'year' in data:
            update_data['year'] = int(data['year'])
        if 'month' in data:
            update_data['month'] = int(data['month'])

        doc_ref.update(update_data)

        updated = doc_ref.get().to_dict()
        updated['id'] = expense_id

        return jsonify(updated), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@expenses_bp.route('/variable/<expense_id>', methods=['DELETE'])
def delete_variable_expense(expense_id):
    """Delete a variable expense"""
    try:
        db = get_db()
        doc_ref = db.collection("variable_expenses").document(expense_id)

        if not doc_ref.get().exists:
            return jsonify({"error": "Not found"}), 404

        doc_ref.delete()

        return jsonify({"message": "Deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
