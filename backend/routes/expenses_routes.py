"""Fixed and Variable Expenses Routes Blueprint (thin wrappers over expenses_service)"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_db
from services import expenses_service as svc
from utils.auth import require_admin

expenses_bp = Blueprint('expenses', __name__, url_prefix='/api/expenses')


def _handle(action):
    """Run a service call and translate its errors to the API's JSON responses"""
    try:
        return action()
    except svc.MissingField as e:
        return jsonify({"error": str(e)}), 400
    except svc.ExpenseNotFound:
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _json_body():
    return request.get_json()


@expenses_bp.route('/fixed', methods=['GET'])
@require_admin
def get_fixed_expenses():
    """Get all fixed expenses"""
    return _handle(lambda: (jsonify(svc.list_fixed(get_db())), 200))


@expenses_bp.route('/fixed', methods=['POST'])
def create_fixed_expense():
    """Create a new fixed expense"""
    def run():
        data = _json_body()
        if not data:
            return jsonify({"error": "No data"}), 400
        return jsonify(svc.create_fixed(get_db(), data)), 201
    return _handle(run)


@expenses_bp.route('/fixed/<expense_id>', methods=['PUT'])
def update_fixed_expense(expense_id):
    """Update a fixed expense"""
    def run():
        data = _json_body()
        if not data:
            return jsonify({"error": "No data"}), 400
        return jsonify(svc.update_fixed(get_db(), expense_id, data)), 200
    return _handle(run)


@expenses_bp.route('/fixed/<expense_id>', methods=['DELETE'])
def delete_fixed_expense(expense_id):
    """Delete a fixed expense"""
    def run():
        svc.delete_fixed(get_db(), expense_id)
        return jsonify({"message": "Deleted"}), 200
    return _handle(run)


@expenses_bp.route('/variable', methods=['GET'])
@require_admin
def get_variable_expenses():
    """Get variable expenses with optional month/year filtering"""
    def run():
        result = svc.list_variable(
            get_db(),
            year=request.args.get('year'),
            month=request.args.get('month'),  # 1-12
        )
        return jsonify(result), 200
    return _handle(run)


@expenses_bp.route('/variable', methods=['POST'])
def create_variable_expense():
    """Create a new variable expense"""
    def run():
        data = _json_body()
        if not data:
            return jsonify({"error": "No data"}), 400
        return jsonify(svc.create_variable(get_db(), data)), 201
    return _handle(run)


@expenses_bp.route('/variable/<expense_id>', methods=['PUT'])
def update_variable_expense(expense_id):
    """Update a variable expense"""
    def run():
        data = _json_body()
        if not data:
            return jsonify({"error": "No data"}), 400
        return jsonify(svc.update_variable(get_db(), expense_id, data)), 200
    return _handle(run)


@expenses_bp.route('/variable/<expense_id>', methods=['DELETE'])
def delete_variable_expense(expense_id):
    """Delete a variable expense"""
    def run():
        svc.delete_variable(get_db(), expense_id)
        return jsonify({"message": "Deleted"}), 200
    return _handle(run)


# Tax endpoints
@expenses_bp.route('/tax', methods=['GET'])
@require_admin
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
