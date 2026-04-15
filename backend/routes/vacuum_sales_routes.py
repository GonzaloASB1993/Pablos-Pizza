"""Vacuum Sales Routes Blueprint - B2B Pizza Sales"""
from flask import Blueprint, request, jsonify
import uuid
from datetime import datetime
from database import get_db
from firebase_admin import firestore

vacuum_sales_bp = Blueprint('vacuum_sales', __name__, url_prefix='/api/vacuum-sales')


def calculate_payment_status(payments, total):
    """Calculate payment status based on payments and total"""
    if not payments or len(payments) == 0:
        return 'unpaid'

    total_paid = sum(float(p.get('amount', 0)) for p in payments)

    if total_paid >= total:
        return 'paid'
    elif total_paid > 0:
        return 'partial'
    return 'unpaid'


def calculate_payment_summary(sale_data):
    """Calculate payment summary for a sale"""
    payments = sale_data.get('payments', [])
    total = float(sale_data.get('total', 0))

    total_paid = sum(float(p.get('amount', 0)) for p in payments)
    balance_due = total - total_paid

    return {
        'total_paid': round(total_paid, 2),
        'balance_due': round(max(0, balance_due), 2),
        'payment_status': calculate_payment_status(payments, total)
    }


@vacuum_sales_bp.route('/', methods=['POST'])
def create_sale():
    """Create a new vacuum pizza sale"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        if 'items' not in data or not data['items']:
            return jsonify({"error": "At least one item is required"}), 400

        if not data.get('customer_id') and not data.get('client_name'):
            return jsonify({"error": "Se requiere un cliente (customer_id o client_name)"}), 400

        db = get_db()
        sale_id = str(uuid.uuid4())
        now = datetime.now()

        # Resolve or create customer
        customer_id = data.get('customer_id')
        customer_name = data.get('customer_name', '')

        if not customer_id:
            # Try to find existing customer by email, or create new one
            client_email = data.get('client_email', '').strip().lower()
            client_name = data.get('client_name', '').strip()
            client_phone = data.get('client_phone', '').strip()

            if client_email:
                existing = db.collection('customers').where('email', '==', client_email).limit(1).get()
                existing_docs = list(existing)
                if existing_docs:
                    customer_id = existing_docs[0].id
                    customer_name = existing_docs[0].to_dict().get('name', client_name)
                    print(f"🔗 Linking vacuum sale to existing customer: {customer_id}")

            if not customer_id and client_name:
                customer_id = str(uuid.uuid4())
                customer_doc = {
                    'id': customer_id,
                    'name': client_name,
                    'email': client_email,
                    'phone': client_phone,
                    'notes': None,
                    'total_bookings': 0,
                    'is_active': True,
                    'created_at': now,
                    'updated_at': now
                }
                db.collection('customers').document(customer_id).set(customer_doc)
                customer_name = client_name
                print(f"✅ New customer created from vacuum sale: {customer_id}")
        elif not customer_name:
            try:
                customer_doc = db.collection('customers').document(customer_id).get()
                if customer_doc.exists:
                    customer_name = customer_doc.to_dict().get('name', '')
            except:
                pass

        # Process items and calculate totals
        processed_items = []
        subtotal = 0
        total_cost = 0

        for item in data['items']:
            product_id = item.get('product_id')
            quantity = float(item.get('quantity', 0))
            unit_price = float(item.get('unit_price', 0))

            # Get product info and cost from inventory
            cost_per_unit = 0
            product_name = item.get('product_name', '')

            if product_id:
                try:
                    product_doc = db.collection('inventory').document(product_id).get()
                    if product_doc.exists:
                        product_data = product_doc.to_dict()
                        cost_per_unit = float(product_data.get('weighted_average_cost', 0) or product_data.get('cost_per_unit', 0) or 0)
                        if not product_name:
                            product_name = product_data.get('name', '')
                except Exception as e:
                    print(f"Error getting product info: {e}")

            item_total = quantity * unit_price
            item_cost = quantity * cost_per_unit

            processed_items.append({
                'product_id': product_id,
                'product_name': product_name,
                'quantity': quantity,
                'unit_price': unit_price,
                'total_price': round(item_total, 2),
                'cost_per_unit': round(cost_per_unit, 2),
                'total_cost': round(item_cost, 2)
            })

            subtotal += item_total
            total_cost += item_cost

            # Create inventory movement (sale/output)
            if product_id and quantity > 0:
                try:
                    movement_id = str(uuid.uuid4())
                    movement_data = {
                        'id': movement_id,
                        'item_id': product_id,
                        'item_name': product_name,
                        'movement_type': 'sale',
                        'quantity': -quantity,  # Negative for output
                        'cost_per_unit': cost_per_unit,
                        'total_cost': item_cost,
                        'reference_type': 'vacuum_sale',
                        'reference_id': sale_id,
                        'notes': f"Venta al vacío - {customer_name}",
                        'created_at': now
                    }
                    db.collection('inventory_movements').document(movement_id).set(movement_data)

                    # Update inventory stock
                    product_ref = db.collection('inventory').document(product_id)
                    product_ref.update({
                        'current_stock': firestore.Increment(-quantity),
                        'updated_at': now
                    })
                except Exception as e:
                    print(f"Error creating inventory movement: {e}")

        discount = float(data.get('discount', 0))
        total = subtotal - discount
        profit = total - total_cost

        # Create sale document
        sale_data = {
            'id': sale_id,
            'customer_id': customer_id,
            'customer_name': customer_name,
            'items': processed_items,
            'subtotal': round(subtotal, 2),
            'discount': round(discount, 2),
            'total': round(total, 2),
            'total_cost': round(total_cost, 2),
            'profit': round(profit, 2),
            'payments': data.get('payments', []),
            'payment_status': 'unpaid',
            'sale_date': data.get('sale_date', now.strftime('%Y-%m-%d')),
            'notes': data.get('notes', ''),
            'created_at': now,
            'updated_at': now
        }

        # Calculate payment status
        sale_data['payment_status'] = calculate_payment_status(sale_data['payments'], sale_data['total'])
        sale_data['payment_summary'] = calculate_payment_summary(sale_data)

        db.collection('vacuum_sales').document(sale_id).set(sale_data)

        print(f"✅ Vacuum sale created: {sale_id}")
        return jsonify(sale_data), 201

    except Exception as e:
        print(f"❌ Error creating vacuum sale: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@vacuum_sales_bp.route('/', methods=['GET'])
def get_sales():
    """Get all vacuum sales with optional filters"""
    try:
        db = get_db()

        # Get query params
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        customer_id = request.args.get('customer_id')
        payment_status = request.args.get('payment_status')
        year = request.args.get('year')
        month = request.args.get('month')

        # Base query
        query = db.collection('vacuum_sales').order_by('created_at', direction=firestore.Query.DESCENDING)

        # Apply filters
        if customer_id:
            query = query.where('customer_id', '==', customer_id)
        if payment_status:
            query = query.where('payment_status', '==', payment_status)

        # Get all results for filtering
        all_docs = list(query.stream())

        # Filter by date if specified
        if year and month:
            target_prefix = f"{year}-{month.zfill(2)}"
            all_docs = [doc for doc in all_docs if doc.to_dict().get('sale_date', '').startswith(target_prefix)]

        # Pagination
        total = len(all_docs)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_docs = all_docs[start_idx:end_idx]

        # Convert to list
        sales = []
        for doc in paginated_docs:
            sale = doc.to_dict()
            sale['id'] = doc.id
            sale['payment_summary'] = calculate_payment_summary(sale)
            sales.append(sale)

        return jsonify({
            'items': sales,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'has_more': end_idx < total
            }
        }), 200

    except Exception as e:
        print(f"❌ Error getting vacuum sales: {e}")
        return jsonify({"error": str(e)}), 500


@vacuum_sales_bp.route('/<sale_id>', methods=['GET'])
def get_sale(sale_id):
    """Get a single vacuum sale by ID"""
    try:
        db = get_db()
        doc = db.collection('vacuum_sales').document(sale_id).get()

        if not doc.exists:
            return jsonify({"error": "Sale not found"}), 404

        sale = doc.to_dict()
        sale['id'] = doc.id
        sale['payment_summary'] = calculate_payment_summary(sale)

        return jsonify(sale), 200

    except Exception as e:
        print(f"❌ Error getting vacuum sale: {e}")
        return jsonify({"error": str(e)}), 500


@vacuum_sales_bp.route('/<sale_id>', methods=['PUT'])
def update_sale(sale_id):
    """Update a vacuum sale"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        db = get_db()
        sale_ref = db.collection('vacuum_sales').document(sale_id)
        doc = sale_ref.get()

        if not doc.exists:
            return jsonify({"error": "Sale not found"}), 404

        # Allowed update fields
        allowed_fields = ['customer_id', 'customer_name', 'discount', 'notes', 'sale_date']
        update_data = {'updated_at': datetime.now()}

        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]

        # Recalculate totals if discount changed
        if 'discount' in data:
            current_data = doc.to_dict()
            subtotal = current_data.get('subtotal', 0)
            discount = float(data['discount'])
            total = subtotal - discount
            total_cost = current_data.get('total_cost', 0)

            update_data['discount'] = round(discount, 2)
            update_data['total'] = round(total, 2)
            update_data['profit'] = round(total - total_cost, 2)

            # Recalculate payment status
            payments = current_data.get('payments', [])
            update_data['payment_status'] = calculate_payment_status(payments, total)

        sale_ref.update(update_data)

        # Get updated sale
        updated_doc = sale_ref.get()
        updated_sale = updated_doc.to_dict()
        updated_sale['id'] = sale_id
        updated_sale['payment_summary'] = calculate_payment_summary(updated_sale)

        return jsonify(updated_sale), 200

    except Exception as e:
        print(f"❌ Error updating vacuum sale: {e}")
        return jsonify({"error": str(e)}), 500


@vacuum_sales_bp.route('/<sale_id>', methods=['DELETE'])
def delete_sale(sale_id):
    """Delete a vacuum sale and revert inventory movements"""
    try:
        db = get_db()
        sale_ref = db.collection('vacuum_sales').document(sale_id)
        doc = sale_ref.get()

        if not doc.exists:
            return jsonify({"error": "Sale not found"}), 404

        sale_data = doc.to_dict()
        now = datetime.now()

        # Revert inventory movements
        for item in sale_data.get('items', []):
            product_id = item.get('product_id')
            quantity = float(item.get('quantity', 0))

            if product_id and quantity > 0:
                try:
                    # Create reversal movement
                    reversal_id = str(uuid.uuid4())
                    reversal_data = {
                        'id': reversal_id,
                        'item_id': product_id,
                        'item_name': item.get('product_name', ''),
                        'movement_type': 'reversal',
                        'quantity': quantity,  # Positive for reversal
                        'cost_per_unit': item.get('cost_per_unit', 0),
                        'total_cost': item.get('total_cost', 0),
                        'reference_type': 'vacuum_sale_delete',
                        'reference_id': sale_id,
                        'notes': f"Reversión por eliminación de venta al vacío",
                        'created_at': now
                    }
                    db.collection('inventory_movements').document(reversal_id).set(reversal_data)

                    # Restore inventory stock
                    product_ref = db.collection('inventory').document(product_id)
                    product_ref.update({
                        'current_stock': firestore.Increment(quantity),
                        'updated_at': now
                    })
                except Exception as e:
                    print(f"Error reverting inventory movement: {e}")

        # Delete the sale
        sale_ref.delete()

        print(f"✅ Vacuum sale deleted: {sale_id}")
        return jsonify({"message": "Sale deleted successfully"}), 200

    except Exception as e:
        print(f"❌ Error deleting vacuum sale: {e}")
        return jsonify({"error": str(e)}), 500


# ============== PAYMENTS ==============

@vacuum_sales_bp.route('/<sale_id>/payments', methods=['POST'])
def add_payment(sale_id):
    """Add a payment to a vacuum sale"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['amount', 'method']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        db = get_db()
        sale_ref = db.collection('vacuum_sales').document(sale_id)
        doc = sale_ref.get()

        if not doc.exists:
            return jsonify({"error": "Sale not found"}), 404

        sale_data = doc.to_dict()

        # Validate payment amount
        amount = float(data['amount'])
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than 0"}), 400

        current_payments = sale_data.get('payments', [])
        total_paid = sum(float(p.get('amount', 0)) for p in current_payments)
        balance = float(sale_data.get('total', 0)) - total_paid

        if amount > balance:
            return jsonify({"error": f"Payment amount (${amount:,.0f}) exceeds balance (${balance:,.0f})"}), 400

        # Create payment
        payment = {
            'id': str(uuid.uuid4()),
            'amount': round(amount, 2),
            'method': data['method'],
            'date': data.get('date', datetime.now().strftime('%Y-%m-%d')),
            'notes': data.get('notes', ''),
            'created_at': datetime.now()
        }

        updated_payments = current_payments + [payment]
        payment_status = calculate_payment_status(updated_payments, sale_data.get('total', 0))

        sale_ref.update({
            'payments': updated_payments,
            'payment_status': payment_status,
            'updated_at': datetime.now()
        })

        return jsonify({
            'payment': payment,
            'payment_summary': calculate_payment_summary({**sale_data, 'payments': updated_payments})
        }), 201

    except Exception as e:
        print(f"❌ Error adding payment: {e}")
        return jsonify({"error": str(e)}), 500


@vacuum_sales_bp.route('/<sale_id>/payments/<payment_id>', methods=['PUT'])
def update_payment(sale_id, payment_id):
    """Update a payment"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        db = get_db()
        sale_ref = db.collection('vacuum_sales').document(sale_id)
        doc = sale_ref.get()

        if not doc.exists:
            return jsonify({"error": "Sale not found"}), 404

        sale_data = doc.to_dict()
        payments = sale_data.get('payments', [])

        # Find payment
        payment_idx = next((i for i, p in enumerate(payments) if p.get('id') == payment_id), None)
        if payment_idx is None:
            return jsonify({"error": "Payment not found"}), 404

        # Update payment fields
        payment = payments[payment_idx]
        if 'amount' in data:
            payment['amount'] = round(float(data['amount']), 2)
        if 'method' in data:
            payment['method'] = data['method']
        if 'date' in data:
            payment['date'] = data['date']
        if 'notes' in data:
            payment['notes'] = data['notes']

        payment['updated_at'] = datetime.now()
        payments[payment_idx] = payment

        payment_status = calculate_payment_status(payments, sale_data.get('total', 0))

        sale_ref.update({
            'payments': payments,
            'payment_status': payment_status,
            'updated_at': datetime.now()
        })

        return jsonify({
            'payment': payment,
            'payment_summary': calculate_payment_summary({**sale_data, 'payments': payments})
        }), 200

    except Exception as e:
        print(f"❌ Error updating payment: {e}")
        return jsonify({"error": str(e)}), 500


@vacuum_sales_bp.route('/<sale_id>/payments/<payment_id>', methods=['DELETE'])
def delete_payment(sale_id, payment_id):
    """Delete a payment"""
    try:
        db = get_db()
        sale_ref = db.collection('vacuum_sales').document(sale_id)
        doc = sale_ref.get()

        if not doc.exists:
            return jsonify({"error": "Sale not found"}), 404

        sale_data = doc.to_dict()
        payments = sale_data.get('payments', [])

        # Filter out the payment
        updated_payments = [p for p in payments if p.get('id') != payment_id]

        if len(updated_payments) == len(payments):
            return jsonify({"error": "Payment not found"}), 404

        payment_status = calculate_payment_status(updated_payments, sale_data.get('total', 0))

        sale_ref.update({
            'payments': updated_payments,
            'payment_status': payment_status,
            'updated_at': datetime.now()
        })

        return jsonify({
            'message': 'Payment deleted successfully',
            'payment_summary': calculate_payment_summary({**sale_data, 'payments': updated_payments})
        }), 200

    except Exception as e:
        print(f"❌ Error deleting payment: {e}")
        return jsonify({"error": str(e)}), 500


# ============== SUMMARY/REPORTS ==============

@vacuum_sales_bp.route('/summary', methods=['GET'])
def get_summary():
    """Get vacuum sales summary for a specific month"""
    try:
        db = get_db()

        year = request.args.get('year', datetime.now().year)
        month = request.args.get('month', datetime.now().month)

        target_prefix = f"{year}-{str(month).zfill(2)}"

        # Get all sales for the month
        all_sales = list(db.collection('vacuum_sales').stream())
        month_sales = [doc.to_dict() for doc in all_sales if doc.to_dict().get('sale_date', '').startswith(target_prefix)]

        # Calculate summary
        total_sales = len(month_sales)
        total_income = sum(float(s.get('total', 0)) for s in month_sales)
        total_cost = sum(float(s.get('total_cost', 0)) for s in month_sales)
        total_profit = sum(float(s.get('profit', 0)) for s in month_sales)
        total_items = sum(sum(float(item.get('quantity', 0)) for item in s.get('items', [])) for s in month_sales)

        # Payment stats
        total_paid = sum(
            sum(float(p.get('amount', 0)) for p in s.get('payments', []))
            for s in month_sales
        )
        total_pending = total_income - total_paid

        # Unique customers
        unique_customers = len(set(s.get('customer_id') for s in month_sales if s.get('customer_id')))

        return jsonify({
            'period': f"{year}-{str(month).zfill(2)}",
            'total_sales': total_sales,
            'total_items': int(total_items),
            'total_income': round(total_income, 2),
            'total_cost': round(total_cost, 2),
            'total_profit': round(total_profit, 2),
            'profit_margin': round((total_profit / total_income * 100) if total_income > 0 else 0, 2),
            'total_paid': round(total_paid, 2),
            'total_pending': round(total_pending, 2),
            'unique_customers': unique_customers
        }), 200

    except Exception as e:
        print(f"❌ Error getting vacuum sales summary: {e}")
        return jsonify({"error": str(e)}), 500
