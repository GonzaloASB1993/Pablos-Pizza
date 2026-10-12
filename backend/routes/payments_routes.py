"""Payments Routes Blueprint - MercadoPago integration"""
from flask import Blueprint, request, jsonify
import uuid
import os
import asyncio
import hashlib
import hmac
import logging
import time
from datetime import datetime
from database import get_db
import mercadopago
from firebase_admin import firestore
from utils.limiter import limiter

payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')
logger = logging.getLogger(__name__)
_transactional = firestore.transactional

# Usar el dominio estable de Firebase Hosting para el webhook (no cambia con cada deploy)
PRODUCTION_BACKEND_URL = 'https://pablospizza.web.app'
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
@limiter.limit("10 per minute")
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
        if not isinstance(description, str) or len(description) > MAX_DESCRIPTION:
            return jsonify({"error": f"description must be text of at most {MAX_DESCRIPTION} characters"}), 400
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
                    "id": booking_id,
                    "title": description,
                    "description": f"Reserva de evento en Pablo's Pizza - ID {booking_id[:8].upper()}",
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


MAX_DESCRIPTION = 200
SIGNATURE_MAX_AGE_SECONDS = 300
_secret_missing_logged = False


def verify_mp_signature(headers, data_id, secret, now=None):
    """Verify MercadoPago's `x-signature` header (`ts=...,v1=...`).

    Manifest (MercadoPago docs): `id:{data.id};request-id:{x-request-id};ts:{ts};` where a field that is absent is
    omitted and an alphanumeric data.id is lowercased. HMAC-SHA256 with the webhook secret, constant-time compare,
    and a `ts` older (or newer) than 5 minutes is rejected. Returns (ok, reason); the reason never contains secrets."""
    header = headers.get('x-signature', '')
    if not header:
        return False, 'missing x-signature header'
    fields = {}
    for part in header.split(','):
        key, _, value = part.partition('=')
        fields[key.strip()] = value.strip()
    ts, received = fields.get('ts', ''), fields.get('v1', '')
    if not ts or not received:
        return False, 'malformed x-signature header'
    try:
        stamp = float(ts)
    except ValueError:
        return False, 'malformed ts'
    if stamp > 1e11:  # MercadoPago sends milliseconds
        stamp /= 1000
    current = time.time() if now is None else now
    if abs(current - stamp) > SIGNATURE_MAX_AGE_SECONDS:
        return False, 'ts outside the 5 minute window'
    manifest = ''
    if data_id:
        manifest += f"id:{data_id.lower() if data_id.isalnum() else data_id};"
    request_id = headers.get('x-request-id', '')
    if request_id:
        manifest += f'request-id:{request_id};'
    manifest += f'ts:{ts};'
    expected = hmac.new(secret.encode('utf-8'), manifest.encode('utf-8'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        return False, 'signature mismatch'
    return True, 'ok'


def _append_mp_payment(db, booking_ref, payment_id, amount):
    """Add the MercadoPago payment to the booking exactly once (checked and written in one transaction).
    Returns (booking_data, True) when it was added, (booking_data, False) when it was already there."""
    transaction = db.transaction()

    @_transactional
    def run(txn):
        snapshot = booking_ref.get(transaction=txn)
        if not snapshot.exists:
            return None, False
        booking_data = snapshot.to_dict()
        payments = list(booking_data.get('payments') or [])
        marker = f'#{payment_id}'
        if any(str(p.get('mp_payment_id', '')) == str(payment_id) or marker in (p.get('notes') or '') for p in payments):
            return booking_data, False
        now = datetime.now()
        payments.append({
            "id": str(uuid.uuid4()),
            "type": "abono",
            "method": "mercadopago",
            "amount": round(float(amount), 2),
            "date": now.isoformat(),
            "notes": f"Pago online MercadoPago #{payment_id}",
            "mp_payment_id": str(payment_id),
            "created_at": now,
        })
        summary = recalculate_payment_summary({**booking_data, 'payments': payments})
        txn.update(booking_ref, {"payments": payments, "payment_summary": summary, "updated_at": now})
        return booking_data, True

    return run(transaction)


def _notify_payment(booking_data, booking_id, mp_amount):
    try:
        admin_phone = os.environ.get('ADMIN_WHATSAPP_NUMBER', '')
        partner_phone = os.environ.get('PARTNER_WHATSAPP_NUMBER', '')
        amount_formatted = f"${round(float(mp_amount)):,}".replace(',', '.')
        from services.whatsapp_service import send_whatsapp_notification
        msg = (
            f"💳 *Pago MercadoPago Recibido*\n"
            f"Cliente: {booking_data.get('client_name', 'Cliente')}\n"
            f"Monto: {amount_formatted} CLP\n"
            f"Evento: {booking_data.get('event_date', '')}\n"
            f"Booking: {booking_id[:8]}..."
        )
        if os.environ.get('SKIP_NOTIFICATIONS', 'false').lower() == 'true':
            return
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(send_whatsapp_notification(admin_phone, msg, 'payment'))
            if partner_phone:
                loop.run_until_complete(send_whatsapp_notification(partner_phone, msg, 'payment'))
        finally:
            loop.close()
    except Exception:  # noqa: BLE001 - WhatsApp errors don't fail the webhook
        pass


@payments_bp.route('/webhook', methods=['POST'])
def webhook():
    """MercadoPago webhook - answers 200 on internal errors (MP would retry forever); 401 only for a bad signature
    when MP_WEBHOOK_ENFORCE=true (default: log-only)."""
    global _secret_missing_logged
    try:
        # MP sends either query params or JSON body. The body is never logged (only ids).
        topic = request.args.get('topic') or request.args.get('type')
        signed_id = request.args.get('data.id')
        payment_id = request.args.get('id') or signed_id
        body = None
        if not payment_id or not signed_id:
            body = request.get_json(silent=True) or {}
            data_block = body.get('data') if isinstance(body.get('data'), dict) else {}
            topic = topic or body.get('type', '')
            payment_id = payment_id or data_block.get('id')
            signed_id = signed_id or (str(data_block['id']) if data_block.get('id') is not None else None)
        logger.info("[WEBHOOK] received topic=%s payment_id=%s", topic, payment_id)

        secret = os.environ.get('MP_WEBHOOK_SECRET', '')
        if not secret:
            if not _secret_missing_logged:
                _secret_missing_logged = True
                logger.warning("[WEBHOOK] MP_WEBHOOK_SECRET is not configured: x-signature is NOT being verified")
        else:
            valid, reason = verify_mp_signature(request.headers, signed_id, secret)
            if not valid:
                logger.warning("[WEBHOOK] invalid x-signature (%s) for payment_id=%s", reason, payment_id)
                if os.environ.get('MP_WEBHOOK_ENFORCE', '').lower() == 'true':
                    return jsonify({"status": "invalid signature"}), 401

        # Only process payment notifications
        if topic not in ('payment', 'merchant_order') and not payment_id:
            return jsonify({"status": "ignored"}), 200

        if not payment_id:
            return jsonify({"status": "no payment_id"}), 200
        payment_id = str(payment_id)

        sdk = get_mp_sdk()
        payment_response = sdk.payment().get(payment_id)
        payment_info = payment_response.get("response", {})

        external_reference = payment_info.get("external_reference")  # booking_id
        mp_status = payment_info.get("status")
        mp_amount = payment_info.get("transaction_amount", 0) or 0

        logger.info("[WEBHOOK] payment_id=%s status=%s external_ref=%s amount=%s", payment_id, mp_status, external_reference, mp_amount)

        if not external_reference:
            logger.warning("[WEBHOOK] payment_id=%s has no external_reference", payment_id)
            return jsonify({"status": "no external_reference"}), 200

        db = get_db()
        booking_id = str(external_reference)
        booking_ref = db.collection("bookings").document(booking_id)
        mp_docs = list(db.collection("mp_payments").where("booking_id", "==", booking_id).get())
        if not mp_docs or not booking_ref.get().exists:
            logger.warning("[WEBHOOK] payment_id=%s references an unknown booking/preference (%s): ignored", payment_id, booking_id)
            return jsonify({"status": "unknown reference"}), 200

        def _amount(doc):
            try:
                return float(doc.to_dict().get("amount", 0) or 0)
            except (TypeError, ValueError):
                return 0.0

        # The preference this payment belongs to: already linked to it, else a pending one with the same amount
        linked = [d for d in mp_docs if str(d.to_dict().get("mp_payment_id", "")) == payment_id]
        pending = [d for d in mp_docs if d.to_dict().get("status") == "pending"]
        amount_matches = [d for d in mp_docs if abs(_amount(d) - float(mp_amount)) <= 1]
        target = (linked or [d for d in pending if d in amount_matches] or pending or [None])[0]

        if mp_status == "approved" and not (linked or amount_matches):
            logger.warning("[WEBHOOK] payment_id=%s amount %s matches no preference of booking %s: not registered",
                           payment_id, mp_amount, booking_id)
            return jsonify({"status": "amount mismatch"}), 200

        if target is not None:
            target.reference.update({"status": mp_status, "mp_payment_id": payment_id, "updated_at": datetime.now()})

        if mp_status == "approved":
            booking_data, added = _append_mp_payment(db, booking_ref, payment_id, mp_amount)
            if not added:
                logger.info("[WEBHOOK] payment_id=%s already registered, skipping", payment_id)
                return jsonify({"status": "already processed"}), 200
            _notify_payment(booking_data, booking_id, mp_amount)

        return jsonify({"status": "ok"}), 200

    except Exception:  # noqa: BLE001
        # Webhook must always return 200
        logger.exception("[WEBHOOK] internal error")
        return jsonify({"status": "ok"}), 200


@payments_bp.route('/status/<booking_id>', methods=['GET'])
@limiter.limit("60 per minute")
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
