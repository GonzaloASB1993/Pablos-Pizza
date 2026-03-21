"""Payments Routes Blueprint - MercadoPago integration"""
from flask import Blueprint, request, jsonify
import uuid
import os
import asyncio
from datetime import datetime
from database import get_db
import mercadopago

payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')

PRODUCTION_BACKEND_URL = 'https://main-446811667554.us-central1.run.app'
PRODUCTION_FRONTEND_URL = 'https://pablospizza.web.app'


def get_mp_sdk():
    access_token = os.environ.get('MP_ACCESS_TOKEN', '')
    sdk = mercadopago.SDK(access_token)
    return sdk


def recalculate_payment_summary(booking_data):
    payments = booking_data.get('payments', [])
    estimated_price = booking_data.get('estimated_price', 0)
    total_paid = sum(p.get('amount', 0) for p in payments)
    balance_due = max(0, estimated_price - total_paid)

    if total_paid >= estimated_price and estimated_price > 0:
        payment_status = 'paid'
    elif total_paid > 0:
        payment_status = 'partial'
    else:
        payment_status = 'pending'

    return {
        'estimated_price': estimated_price,
        'total_paid': round(total_paid, 2),
        'balance_due': round(balance_due, 2),
        'payment_status': payment_status
    }


@payments_bp.route('/create-preference', methods=['POST'])
def create_preference():
    """Create a MercadoPago payment preference for a booking"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        booking_id = data.get('booking_id')
        amount = data.get('amount')
        description = data.get('description', "Abono Reserva Pablo's Pizza")

        if not booking_id:
            return jsonify({"error": "booking_id is required"}), 400
        if amount is None:
            return jsonify({"error": "amount is required"}), 400

        try:
            amount = float(amount)
            if amount <= 0:
                return jsonify({"error": "amount must be greater than 0"}), 400
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid amount"}), 400

        db = get_db()
        booking_ref = db.collection("bookings").document(booking_id)
        booking_doc = booking_ref.get()

        if not booking_doc.exists:
            return jsonify({"error": "Booking not found"}), 404

        booking_data = booking_doc.to_dict()
        payment_summary = booking_data.get('payment_summary', {})

        if payment_summary.get('payment_status') == 'paid':
            return jsonify({"error": "Booking is already fully paid"}), 400

        balance_due = payment_summary.get('balance_due', booking_data.get('estimated_price', 0))
        if amount > balance_due + 1:  # +1 for floating point tolerance
            return jsonify({"error": f"Amount ({amount}) exceeds balance due ({balance_due})"}), 400

        sdk = get_mp_sdk()

        preference_data = {
            "items": [
                {
                    "title": description,
                    "quantity": 1,
                    "unit_price": round(amount),
                    "currency_id": "CLP"
                }
            ],
            "back_urls": {
                "success": f"{PRODUCTION_FRONTEND_URL}/pago/exitoso?booking_id={booking_id}",
                "failure": f"{PRODUCTION_FRONTEND_URL}/pago/fallido?booking_id={booking_id}",
                "pending": f"{PRODUCTION_FRONTEND_URL}/pago/pendiente?booking_id={booking_id}"
            },
            "auto_return": "approved",
            "notification_url": f"{PRODUCTION_BACKEND_URL}/api/payments/webhook",
            "external_reference": booking_id,
            "statement_descriptor": "PABLOSPIZZA"
        }

        preference_response = sdk.preference().create(preference_data)
        preference = preference_response.get("response", {})

        if preference_response.get("status") not in [200, 201]:
            return jsonify({"error": "Failed to create MercadoPago preference", "detail": preference}), 500

        preference_id = preference.get("id")
        init_point = preference.get("init_point")

        mp_payment_id = str(uuid.uuid4())
        mp_payment_doc = {
            "id": mp_payment_id,
            "booking_id": booking_id,
            "mp_preference_id": preference_id,
            "amount": round(amount),
            "status": "pending",
            "init_point": init_point,
            "created_at": datetime.now()
        }
        db.collection("mp_payments").document(mp_payment_id).set(mp_payment_doc)

        return jsonify({
            "init_point": init_point,
            "preference_id": preference_id
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@payments_bp.route('/webhook', methods=['POST'])
def webhook():
    """MercadoPago webhook - always returns 200"""
    try:
        # MP sends either query params or JSON body
        topic = request.args.get('topic') or request.args.get('type')
        payment_id = request.args.get('id') or request.args.get('data.id')

        # Also check JSON body
        if not payment_id:
            body = request.get_json(silent=True) or {}
            topic = topic or body.get('type', '')
            payment_id = body.get('data', {}).get('id')

        # Only process payment notifications
        if topic not in ('payment', 'merchant_order') and not payment_id:
            return jsonify({"status": "ignored"}), 200

        if not payment_id:
            return jsonify({"status": "no payment_id"}), 200

        sdk = get_mp_sdk()
        payment_response = sdk.payment().get(payment_id)
        payment_info = payment_response.get("response", {})

        external_reference = payment_info.get("external_reference")  # booking_id
        mp_status = payment_info.get("status")
        mp_amount = payment_info.get("transaction_amount", 0)

        if not external_reference:
            return jsonify({"status": "no external_reference"}), 200

        db = get_db()
        booking_id = external_reference

        # Idempotency: check if already processed
        existing_payments = db.collection("mp_payments") \
            .where("booking_id", "==", booking_id) \
            .where("status", "==", "approved") \
            .limit(1) \
            .get()

        if list(existing_payments) and mp_status == "approved":
            return jsonify({"status": "already processed"}), 200

        # Update mp_payments record
        mp_payment_docs = db.collection("mp_payments") \
            .where("booking_id", "==", booking_id) \
            .where("status", "==", "pending") \
            .order_by("created_at", direction="DESCENDING") \
            .limit(1) \
            .get()

        mp_payment_docs_list = list(mp_payment_docs)
        if mp_payment_docs_list:
            mp_doc_ref = mp_payment_docs_list[0].reference
            mp_doc_ref.update({
                "status": mp_status,
                "mp_payment_id": str(payment_id),
                "updated_at": datetime.now()
            })

        if mp_status == "approved":
            booking_ref = db.collection("bookings").document(booking_id)
            booking_doc = booking_ref.get()

            if booking_doc.exists:
                booking_data = booking_doc.to_dict()
                payments = booking_data.get('payments', [])

                new_payment = {
                    "id": str(uuid.uuid4()),
                    "type": "abono",
                    "method": "mercadopago",
                    "amount": round(float(mp_amount), 2),
                    "date": datetime.now().isoformat(),
                    "notes": f"Pago online MercadoPago #{payment_id}",
                    "created_at": datetime.now()
                }
                payments.append(new_payment)

                updated_booking = dict(booking_data)
                updated_booking['payments'] = payments
                payment_summary = recalculate_payment_summary(updated_booking)

                booking_ref.update({
                    "payments": payments,
                    "payment_summary": payment_summary,
                    "updated_at": datetime.now()
                })

                # Notify admin via WhatsApp
                try:
                    admin_phone = os.environ.get('ADMIN_WHATSAPP_NUMBER', '')
                    partner_phone = os.environ.get('PARTNER_WHATSAPP_NUMBER', '')
                    client_name = booking_data.get('client_name', 'Cliente')
                    event_date = booking_data.get('event_date', '')
                    amount_formatted = f"${round(float(mp_amount)):,}".replace(',', '.')

                    from services.whatsapp_service import send_whatsapp_notification
                    msg = (
                        f"💳 *Pago MercadoPago Recibido*\n"
                        f"Cliente: {client_name}\n"
                        f"Monto: {amount_formatted} CLP\n"
                        f"Evento: {event_date}\n"
                        f"Booking: {booking_id[:8]}..."
                    )
                    skip = os.environ.get('SKIP_NOTIFICATIONS', 'false').lower() == 'true'
                    if not skip:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(send_whatsapp_notification(admin_phone, msg, 'payment'))
                            if partner_phone:
                                loop.run_until_complete(send_whatsapp_notification(partner_phone, msg, 'payment'))
                        finally:
                            loop.close()
                except Exception:
                    pass  # WhatsApp errors don't fail the webhook

        return jsonify({"status": "ok"}), 200

    except Exception:
        # Webhook must always return 200
        return jsonify({"status": "ok"}), 200


@payments_bp.route('/status/<booking_id>', methods=['GET'])
def get_payment_status(booking_id):
    """Get latest MercadoPago payment status for a booking"""
    try:
        db = get_db()
        mp_payment_docs = db.collection("mp_payments") \
            .where("booking_id", "==", booking_id) \
            .order_by("created_at", direction="DESCENDING") \
            .limit(1) \
            .get()

        docs_list = list(mp_payment_docs)
        if not docs_list:
            return jsonify({"status": "not_found", "amount": 0, "mp_payment_id": None}), 200

        doc_data = docs_list[0].to_dict()
        return jsonify({
            "status": doc_data.get("status", "pending"),
            "amount": doc_data.get("amount", 0),
            "mp_payment_id": doc_data.get("mp_payment_id")
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
