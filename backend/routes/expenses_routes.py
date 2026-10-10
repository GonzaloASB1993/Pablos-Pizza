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
        expenses = db.collection("fixed_expenses").get()

        result = []
        for expense in expenses:
            data = expense.to_dict()
            data['id'] = expense.id
            result.append(data)

        # Sort by created_at descending in Python
        result.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)

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
            # Optional effective date range (YYYY-MM). None means "no limit" on that side.
            'effective_from': data.get('effective_from') or None,
            'effective_to': data.get('effective_to') or None,
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
        if 'effective_from' in data:
            update_data['effective_from'] = data['effective_from'] or None
        if 'effective_to' in data:
            update_data['effective_to'] = data['effective_to'] or None

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

        # Get all expenses and filter in Python to avoid index requirements
        all_expenses = db.collection("variable_expenses").get()

        result = []
        for expense in all_expenses:
            data = expense.to_dict()
            data['id'] = expense.id

            # Apply filters
            if year and data.get('year') != int(year):
                continue
            if month and data.get('month') != int(month):
                continue

            result.append(data)

        # Sort by created_at descending
        result.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)

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

# Tax endpoints
@expenses_bp.route('/tax', methods=['GET'])
def get_tax():
    """Get tax for a specific month/year"""
    try:
        db = get_db()
        month = request.args.get('month')
        year = request.args.get('year')

        if not year or not month:
            return jsonify({"error": "Year and month required"}), 400

        # Get tax document for this month/year
        tax_id = f"{year}_{month}"
        doc = db.collection("monthly_taxes").document(tax_id).get()

        if doc.exists:
            data = doc.to_dict()
            return jsonify({"amount": data.get('amount', 0)}), 200
        else:
            return jsonify({"amount": 0}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@expenses_bp.route('/tax', methods=['POST'])
def save_tax():
    """Save tax for a specific month/year"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400

        required_fields = ['year', 'month', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing {field}"}), 400

        db = get_db()
        tax_id = f"{data['year']}_{data['month']}"

        tax_data = {
            'year': int(data['year']),
            'month': int(data['month']),
            'amount': float(data['amount']),
            'updated_at': datetime.now()
        }

        db.collection("monthly_taxes").document(tax_id).set(tax_data)

        return jsonify(tax_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
