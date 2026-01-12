"""Bookings Routes Blueprint"""
from flask import Blueprint, request, jsonify
import uuid, os, asyncio
from datetime import datetime
from database import get_db
from firebase_admin import firestore
from utils.pagination import paginate_query, create_pagination_response
from services.whatsapp_service import send_whatsapp_template
from services.email_service import send_admin_email_notification

bookings_bp = Blueprint('bookings', __name__, url_prefix='/api/bookings')

try:
    from config import PricingConfig
except:
    class PricingConfig:
        PIZZEROS_MINIMUM = 135000
        PIZZA_PARTY_BASE_PRICE = 11990
        @staticmethod
        def get_pizzeros_price(p): return 13500 if p<=10 else (10500 if p<=14 else (9500 if p<=19 else 9000))
        @staticmethod
        def get_pizza_party_price(pizzas): return round(PricingConfig.PIZZA_PARTY_BASE_PRICE*0.9) if pizzas>=20 else PricingConfig.PIZZA_PARTY_BASE_PRICE

def calculate_estimated_price(service_types, pizzeros_participants=0, party_participants=0, participants=0, pizza_quantity=0):
    total = 0
    for s in [x.strip() for x in service_types.split(',') if x.strip()]:
        if s in ["workshop","pizzeros"]:
            sp = pizzeros_participants or participants
            if sp > 0:
                total += max(PricingConfig.PIZZEROS_MINIMUM if sp<=10 else 0, sp*PricingConfig.get_pizzeros_price(sp))
        elif s in ["pizza_party","party"]:
            pz = pizza_quantity or party_participants or participants
            if pz > 0: total += pz*PricingConfig.get_pizza_party_price(pz)
    return round(total, 2)

@bookings_bp.route('/', methods=['POST'])
def create_booking():
    """Create new booking with automatic customer linking/creation"""
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "No data"}), 400
        for f in ['service_type','participants']:
            if f not in data: return jsonify({"error": f"Missing {f}"}), 400

        db = get_db()
        bid = str(uuid.uuid4())
        ep = calculate_estimated_price(data.get('service_type',''),data.get('pizzeros_participants',0),data.get('party_participants',0),data.get('participants',0),data.get('pizza_quantity',0))

        # Handle customer linking/creation
        customer_id = data.get('customer_id')
        client_email = data.get('client_email', '').strip().lower()

        if not customer_id and client_email:
            # Check if customer exists by email
            existing = db.collection("customers").where("email", "==", client_email).limit(1).get()
            existing_docs = list(existing)

            if existing_docs:
                # Link to existing customer
                customer_id = existing_docs[0].id
                print(f"🔗 Linking booking to existing customer: {customer_id}")
            else:
                # Create new customer
                customer_id = str(uuid.uuid4())
                now = datetime.now()
                customer_doc = {
                    "id": customer_id,
                    "name": data.get('client_name', '').strip(),
                    "email": client_email,
                    "phone": data.get('client_phone', '').strip(),
                    "address": data.get('location'),
                    "notes": None,
                    "total_bookings": 1,
                    "last_booking_date": data.get('event_date'),
                    "created_at": now,
                    "updated_at": now,
                    "is_active": True
                }
                db.collection("customers").document(customer_id).set(customer_doc)
                print(f"✅ New customer created: {customer_id}")

        # Create booking with customer reference
        # Map special_requests to notes for admin panel compatibility
        notes = data.get('special_requests') or data.get('notes', '')
        bd = {"id":bid,**data,"customer_id":customer_id,"notes":notes,"status":"pending","created_at":datetime.now(),"estimated_price":ep}
        db.collection("bookings").document(bid).set(bd)

        # Update customer stats if customer exists
        if customer_id:
            try:
                customer_ref = db.collection("customers").document(customer_id)
                customer_ref.update({
                    "total_bookings": firestore.Increment(1),
                    "last_booking_date": data.get('event_date'),
                    "updated_at": datetime.now()
                })
            except: pass

        # Send notifications
        try:
            for ph in [os.getenv('ADMIN_WHATSAPP_NUMBER','+56998960858'),os.getenv('PARTNER_WHATSAPP_NUMBER','+56998960858')]:
                asyncio.run(send_whatsapp_template(ph,'new_booking',bd))
        except: pass

        # Send email notification to admin
        try:
            send_admin_email_notification(bd)
        except Exception as e:
            print(f"Error sending admin email: {e}")

        return jsonify(bd), 201
    except Exception as e: return jsonify({"error":str(e)}), 500

@bookings_bp.route('/', methods=['GET'])
def get_bookings():
    try:
        db = get_db()
        if not db: return jsonify({'error':'DB failed'}), 500
        page,limit = int(request.args.get('page',1)),int(request.args.get('limit',20))
        br = db.collection("bookings").order_by('created_at',direction=firestore.Query.DESCENDING)
        pb,hm,ts = paginate_query(br,page,limit)
        for b in pb:
            try:
                # Computed costs
                fin = (b or {}).get('financials') or {}
                es,rs,oe = float(fin.get('estimated_supply_cost',0) or 0),float(fin.get('supply_cost',0) or 0),float(fin.get('other_expenses',0) or 0)
                cs,tc = (rs if rs>0 else es),(rs if rs>0 else es)+oe
                b['computed_costs'] = {'estimated_supply_cost':es,'real_supply_cost':rs,'other_expenses_total':oe,'current_supply_cost':cs,'total_cost':tc,'source':'real' if rs>0 else 'estimated'}

                # Payment summary
                b['payment_summary'] = calculate_payment_summary(b)
            except: pass
        return jsonify(create_pagination_response(pb,page,limit,hm,ts)), 200
    except Exception as e: return jsonify({"error":str(e)}), 500

@bookings_bp.route('/<booking_id>', methods=['GET'])
def get_booking(booking_id):
    try:
        db = get_db()
        doc = db.collection("bookings").document(booking_id).get()
        if doc.exists:
            b = doc.to_dict()
            b['id'] = doc.id
            # Add payment summary
            b['payment_summary'] = calculate_payment_summary(b)
            return jsonify(b), 200
        return jsonify({"error":"Not found"}), 404
    except Exception as e: return jsonify({"error":str(e)}), 500

@bookings_bp.route('/<booking_id>', methods=['PUT'])
def update_booking(booking_id):
    try:
        data = request.get_json()
        if not data: return jsonify({"error":"No data"}), 400
        db = get_db()
        dr = db.collection("bookings").document(booking_id)
        doc = dr.get()
        if not doc.exists: return jsonify({"error":"Not found"}), 404

        # Get current booking data to check for status changes
        current_booking = doc.to_dict()
        old_status = current_booking.get('status')
        new_status = data.get('status')

        # Update the booking
        dr.update(data)
        updated_booking = dr.get().to_dict()
        updated_booking['id'] = booking_id

        # Send notifications if status changed from non-confirmed to confirmed
        if new_status == 'confirmed' and old_status != 'confirmed':
            print(f"📧 Estado cambió de '{old_status}' a 'confirmed' - enviando notificaciones")

            # Send email to client
            client_email = updated_booking.get('client_email')
            if client_email:
                try:
                    from services.email_service import send_confirmation_email
                    email_sent = send_confirmation_email(updated_booking)
                    if email_sent:
                        print(f"✅ Email de confirmación enviado a {client_email}")
                    else:
                        print(f"❌ Error enviando email a {client_email}")
                except Exception as e:
                    print(f"❌ Error en envío de email: {e}")

            # Send WhatsApp to client
            client_phone = updated_booking.get('client_phone')
            if client_phone:
                try:
                    asyncio.run(send_whatsapp_template(client_phone, 'booking_confirmed', updated_booking))
                    print(f"✅ WhatsApp de confirmación enviado al cliente {client_phone}")
                except Exception as e:
                    print(f"❌ Error enviando WhatsApp al cliente: {e}")

            # Send WhatsApp to admins
            for admin_phone in [os.getenv('ADMIN_WHATSAPP_NUMBER'), os.getenv('PARTNER_WHATSAPP_NUMBER')]:
                if admin_phone:
                    try:
                        asyncio.run(send_whatsapp_template(admin_phone, 'booking_confirmed_admin', updated_booking))
                        print(f"✅ WhatsApp enviado al admin {admin_phone}")
                    except Exception as e:
                        print(f"❌ Error enviando WhatsApp al admin: {e}")

        # Create event automatically when booking is completed
        if new_status == 'completed' and old_status != 'completed':
            print(f"🎉 Estado cambió de '{old_status}' a 'completed' - creando evento automáticamente")

            try:
                # Prepare event data from booking
                event_data = {
                    'title': f"{updated_booking.get('service_type', 'Evento').replace('workshop', 'Pizzeros en Acción').replace('pizza_party', 'Pizza Party')} - {updated_booking.get('client_name', 'Cliente')}",
                    'description': f"Evento realizado para {updated_booking.get('client_name', 'cliente')} en {updated_booking.get('location', 'ubicación no especificada')}.",
                    'event_date': updated_booking.get('event_date'),
                    'participants': updated_booking.get('participants', 0),
                    'pizzeros_participants': updated_booking.get('pizzeros_participants', 0),
                    'party_guests': updated_booking.get('party_guests', 0) or updated_booking.get('party_participants', 0),
                    'pizza_quantity': updated_booking.get('pizza_quantity', 10),
                    'final_price': updated_booking.get('estimated_price', 0),
                    'event_cost': data.get('event_cost', 0) or updated_booking.get('event_cost', 0),
                    'profit': (updated_booking.get('estimated_price', 0) - (data.get('event_cost', 0) or updated_booking.get('event_cost', 0))),
                    'notes': updated_booking.get('notes', ''),
                    'status': 'completed',
                    'booking_id': booking_id,
                    'service_type': updated_booking.get('service_type', ''),
                    'location': updated_booking.get('location', ''),
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'is_published': False,  # Not published by default
                    'is_featured': False,
                    'category': 'workshop' if 'workshop' in updated_booking.get('service_type', '') else 'pizza_party',
                    'satisfaction': 5,
                    'highlight': 'Experiencia única',
                    'age_group': 'Todas las edades'
                }

                # Create the event
                event_ref = db.collection("events").add(event_data)
                event_id = event_ref[1].id
                print(f"✅ Evento creado automáticamente con ID: {event_id}")

            except Exception as e:
                print(f"❌ Error creando evento automáticamente: {e}")
                # Don't fail the booking update if event creation fails

        return jsonify(updated_booking), 200
    except Exception as e:
        print(f"❌ Error en update_booking: {e}")
        return jsonify({"error":str(e)}), 500

@bookings_bp.route('/<booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    try:
        db = get_db()
        dr = db.collection("bookings").document(booking_id)
        if not dr.get().exists: return jsonify({"error":"Not found"}), 404
        dr.delete()
        return jsonify({"message":"Deleted"}), 200
    except Exception as e: return jsonify({"error":str(e)}), 500

# ============== PAYMENTS ENDPOINTS ==============

def calculate_payment_summary(booking_doc):
    """
    Calculate payment summary from payments array

    Args:
        booking_doc (dict): Booking document with payments array

    Returns:
        dict: payment_summary with total_paid, balance_due, payment_status
    """
    payments = booking_doc.get('payments', [])
    estimated_price = float(booking_doc.get('estimated_price', 0))

    # Calculate total paid
    total_paid = sum(float(p.get('amount', 0)) for p in payments)

    # Calculate balance due
    balance_due = estimated_price - total_paid

    # Determine payment status
    if total_paid == 0:
        payment_status = 'unpaid'
    elif balance_due > 0:
        payment_status = 'partial'
    else:
        payment_status = 'paid'

    return {
        'total_paid': round(total_paid, 2),
        'balance_due': round(balance_due, 2),
        'payment_status': payment_status
    }

@bookings_bp.route('/<booking_id>/payments', methods=['POST'])
def add_payment(booking_id):
    """Add a new payment to a booking"""
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "No data"}), 400

        # Validate required fields
        required_fields = ['amount', 'method', 'type']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Validate amount
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({"error": "Amount must be greater than 0"}), 400
        except ValueError:
            return jsonify({"error": "Invalid amount"}), 400

        # Validate method
        if data['method'] not in ['efectivo', 'transferencia']:
            return jsonify({"error": "Invalid payment method"}), 400

        # Validate type
        if data['type'] not in ['abono', 'saldo']:
            return jsonify({"error": "Invalid payment type"}), 400

        db = get_db()
        booking_ref = db.collection("bookings").document(booking_id)
        booking_doc = booking_ref.get()

        if not booking_doc.exists:
            return jsonify({"error": "Booking not found"}), 404

        booking_data = booking_doc.to_dict()

        # Validate payment doesn't exceed balance
        current_payments = booking_data.get('payments', [])
        current_paid = sum(float(p.get('amount', 0)) for p in current_payments)
        estimated_price = float(booking_data.get('estimated_price', 0))
        balance = estimated_price - current_paid

        if amount > balance:
            return jsonify({"error": f"Payment amount (${amount:,.0f}) exceeds balance due (${balance:,.0f})"}), 400

        # Create payment object
        payment = {
            'id': str(uuid.uuid4()),
            'amount': round(amount, 2),
            'method': data['method'],
            'type': data['type'],
            'date': data.get('date', datetime.now().isoformat()),
            'notes': data.get('notes', ''),
            'created_at': datetime.now()
        }

        # Update booking with new payment
        updated_payments = current_payments + [payment]
        booking_data['payments'] = updated_payments

        # Calculate and update payment_summary
        payment_summary = calculate_payment_summary({**booking_data, 'payments': updated_payments})

        booking_ref.update({
            'payments': updated_payments,
            'payment_summary': payment_summary,
            'updated_at': datetime.now()
        })

        return jsonify({
            'payment': payment,
            'payment_summary': payment_summary
        }), 201

    except Exception as e:
        print(f"❌ Error adding payment: {e}")
        return jsonify({"error": str(e)}), 500

@bookings_bp.route('/<booking_id>/payments/<payment_id>', methods=['PUT'])
def update_payment(booking_id, payment_id):
    """Update an existing payment"""
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "No data"}), 400

        db = get_db()
        booking_ref = db.collection("bookings").document(booking_id)
        booking_doc = booking_ref.get()

        if not booking_doc.exists:
            return jsonify({"error": "Booking not found"}), 404

        booking_data = booking_doc.to_dict()
        payments = booking_data.get('payments', [])

        # Find payment to update
        payment_index = next((i for i, p in enumerate(payments) if p.get('id') == payment_id), None)
        if payment_index is None:
            return jsonify({"error": "Payment not found"}), 404

        # Validate new amount if provided
        if 'amount' in data:
            try:
                new_amount = float(data['amount'])
                if new_amount <= 0:
                    return jsonify({"error": "Amount must be greater than 0"}), 400

                # Calculate if new amount is valid
                other_payments_total = sum(float(p.get('amount', 0)) for i, p in enumerate(payments) if i != payment_index)
                estimated_price = float(booking_data.get('estimated_price', 0))

                if (other_payments_total + new_amount) > estimated_price:
                    return jsonify({"error": f"Total payments would exceed booking price"}), 400

            except ValueError:
                return jsonify({"error": "Invalid amount"}), 400

        # Update payment fields
        payment = payments[payment_index]
        if 'amount' in data:
            payment['amount'] = round(float(data['amount']), 2)
        if 'method' in data and data['method'] in ['efectivo', 'transferencia']:
            payment['method'] = data['method']
        if 'type' in data and data['type'] in ['abono', 'saldo']:
            payment['type'] = data['type']
        if 'date' in data:
            payment['date'] = data['date']
        if 'notes' in data:
            payment['notes'] = data['notes']

        payment['updated_at'] = datetime.now()
        payments[payment_index] = payment

        # Calculate and update payment_summary
        payment_summary = calculate_payment_summary({**booking_data, 'payments': payments})

        booking_ref.update({
            'payments': payments,
            'payment_summary': payment_summary,
            'updated_at': datetime.now()
        })

        return jsonify({
            'payment': payment,
            'payment_summary': payment_summary
        }), 200

    except Exception as e:
        print(f"❌ Error updating payment: {e}")
        return jsonify({"error": str(e)}), 500

@bookings_bp.route('/<booking_id>/payments/<payment_id>', methods=['DELETE'])
def delete_payment(booking_id, payment_id):
    """Delete a payment from a booking"""
    try:
        db = get_db()
        booking_ref = db.collection("bookings").document(booking_id)
        booking_doc = booking_ref.get()

        if not booking_doc.exists:
            return jsonify({"error": "Booking not found"}), 404

        booking_data = booking_doc.to_dict()
        payments = booking_data.get('payments', [])

        # Filter out the payment to delete
        updated_payments = [p for p in payments if p.get('id') != payment_id]

        if len(updated_payments) == len(payments):
            return jsonify({"error": "Payment not found"}), 404

        # Calculate and update payment_summary
        payment_summary = calculate_payment_summary({**booking_data, 'payments': updated_payments})

        booking_ref.update({
            'payments': updated_payments,
            'payment_summary': payment_summary,
            'updated_at': datetime.now()
        })

        return jsonify({
            'message': 'Payment deleted successfully',
            'payment_summary': payment_summary
        }), 200

    except Exception as e:
        print(f"❌ Error deleting payment: {e}")
        return jsonify({"error": str(e)}), 500
