from fastapi import APIRouter, HTTPException, Depends, status
from firebase_admin import firestore
from models.schemas import BookingCreate, BookingUpdate, Booking, BookingStatus
from services.notification_service import send_whatsapp_notification
from services.email_service import send_confirmation_email
from typing import List
import uuid
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

def get_firestore_client():
    """Get Firestore client instance"""
    return firestore.client()

@router.post("/", response_model=Booking)
async def create_booking(booking: BookingCreate):
    """Crear nuevo agendamiento"""
    print("CREATE_BOOKING INICIADO - VERSION_2025_FIXED")
    booking_id = str(uuid.uuid4())

    # Calcular precio estimado basado en servicio y participantes
    print(f"[BEFORE CALL] About to call calculate_estimated_price with: service_type='{booking.service_type}', pizzeros_participants={booking.pizzeros_participants}, party_participants={booking.party_participants}")
    estimated_price = calculate_estimated_price(booking.service_type, booking.participants, booking.pizzeros_participants, booking.party_participants)
    print(f"[AFTER CALL] PRECIO CALCULADO: {booking.service_type} = ${estimated_price} CLP")

    booking_data = {
        "id": booking_id,
        **booking.model_dump(),
        "status": BookingStatus.PENDING,
        "created_at": datetime.now(),
        "estimated_price": estimated_price
    }

    print(f"[DEBUG BOOKING_DATA] Before Firestore:")
    print(f"  - Original estimated_price: {estimated_price}")
    print(f"  - Type: {type(estimated_price)}")
    print(f"  - booking_data['estimated_price']: {booking_data['estimated_price']}")
    print(f"  - Type in booking_data: {type(booking_data['estimated_price'])}")

    logger.info(f"DATOS ANTES FIRESTORE: precio = ${booking_data['estimated_price']} CLP")
    
    try:
        # Guardar en Firestore
        db = get_firestore_client()
        db.collection("bookings").document(booking_id).set(booking_data)
        print(f"GUARDADO EN FIRESTORE: {booking_id}")

        # Verificar que se guardó correctamente
        saved_doc = db.collection("bookings").document(booking_id).get()
        if saved_doc.exists:
            saved_data = saved_doc.to_dict()
            print(f"VERIFICACION: precio guardado = ${saved_data.get('estimated_price', 0)} CLP")
        else:
            print("ERROR: Documento no encontrado")
        
        # Enviar notificación WhatsApp al cliente confirmando que se registró el agendamiento
        client_message = f"""
¡Hola {booking_data['client_name']}!

Tu solicitud de agendamiento ha sido recibida:
📅 Fecha: {booking_data['event_date'].strftime('%d/%m/%Y')}
⏰ Hora: {booking_data['event_time']}
👥 Participantes: {booking_data['participants']}
Servicio: {'Pizzeros en Acción' if booking_data['service_type'] == 'workshop' else 'Pizza Party'}

Pronto nos pondremos en contacto contigo para confirmar los detalles.

¡Gracias por elegir Pablo's Pizza!         """

        await send_whatsapp_notification(
            booking_data['client_phone'],
            client_message,
            "booking_confirmation"
        )
        
        return Booking(**booking_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear agendamiento: {str(e)}"
        )

@router.get("/", response_model=List[Booking])
async def get_bookings(status_filter: str = None, limit: int = 100):
    """Obtener todos los agendamientos con filtro opcional por estado"""
    try:
        db = get_firestore_client()
        query = db.collection("bookings").order_by("created_at", direction=firestore.Query.DESCENDING)
        
        if status_filter:
            query = query.where("status", "==", status_filter)
        
        docs = query.limit(limit).stream()
        bookings = []
        
        for doc in docs:
            data = doc.to_dict()
            print(f"[LECTURA] Firestore: ID={doc.id}, estimated_price = ${data.get('estimated_price', 0):,.0f} CLP")
            bookings.append(Booking(**data))

        print(f"[RETORNO] {len(bookings)} bookings al frontend")
        return bookings
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener agendamientos: {str(e)}"
        )

@router.get("/{booking_id}", response_model=Booking)
async def get_booking(booking_id: str):
    """Obtener agendamiento específico"""
    try:
        db = get_firestore_client()
        doc = db.collection("bookings").document(booking_id).get()
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agendamiento no encontrado"
            )
        
        data = doc.to_dict()
        return Booking(**data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener agendamiento: {str(e)}"
        )

@router.put("/{booking_id}", response_model=Booking)
async def update_booking(booking_id: str, booking_update: BookingUpdate):
    """Actualizar agendamiento"""
    try:
        db = get_firestore_client()
        booking_ref = db.collection("bookings").document(booking_id)
        doc = booking_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agendamiento no encontrado"
            )
        
        current_data = doc.to_dict()

        # DEBUG: Log what we're receiving
        print(f"🔧 BACKEND DEBUG: booking_update received: {booking_update}")
        print(f"🔧 BACKEND DEBUG: booking_update.model_dump(): {booking_update.model_dump()}")
        print(f"🔧 BACKEND DEBUG: booking_update.model_dump(exclude_unset=True): {booking_update.model_dump(exclude_unset=True)}")

        update_data = booking_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now()

        print(f"🔧 BACKEND DEBUG: final update_data: {update_data}")
        
        # Si se actualiza el estado a confirmado, enviar notificaciones
        if update_data.get("status") == BookingStatus.CONFIRMED:
            # Enviar WhatsApp de confirmación
            await send_confirmation_notification(current_data)
            # Enviar Email de confirmación con detalles completos
            await send_confirmation_email(current_data)
        
        booking_ref.update(update_data)
        
        # Obtener datos actualizados
        updated_doc = booking_ref.get()
        updated_data = updated_doc.to_dict()
        
        return Booking(**updated_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar agendamiento: {str(e)}"
        )

@router.delete("/{booking_id}")
async def cancel_booking(booking_id: str):
    """Cancelar agendamiento"""
    try:
        db = get_firestore_client()
        booking_ref = db.collection("bookings").document(booking_id)
        doc = booking_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agendamiento no encontrado"
            )
        
        booking_ref.update({
            "status": BookingStatus.CANCELLED,
            "updated_at": datetime.now()
        })
        
        return {"message": "Agendamiento cancelado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cancelar agendamiento: {str(e)}"
        )

@router.get("/test-price/{service_type}/{pizzeros_participants}/{party_participants}")
async def test_price_calculation(service_type: str, pizzeros_participants: int = 0, party_participants: int = 0):
    """Test endpoint to verify price calculation"""
    total_participants = max(pizzeros_participants, party_participants)
    price = calculate_estimated_price(service_type, total_participants, pizzeros_participants, party_participants)
    return {
        "service_type": service_type,
        "pizzeros_participants": pizzeros_participants,
        "party_participants": party_participants,
        "calculated_price": price,
        "new_pricing_structure": {
            "pizzeros_0_10": "13500 (minimum)",
            "pizzeros_11_14": "10500 per child",
            "pizzeros_15_19": "9500 per child",
            "pizzeros_20_plus": "9000 per child"
        }
    }

@router.get("/calendar/{year}/{month}")
async def get_calendar_events(year: int, month: int):
    """Obtener eventos del calendario para un mes específico"""
    try:
        from datetime import date
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        db = get_firestore_client()
        query = db.collection("bookings").where(
            "event_date", ">=", start_date
        ).where(
            "event_date", "<", end_date
        ).where(
            "status", "in", [BookingStatus.CONFIRMED, BookingStatus.COMPLETED]
        )
        
        docs = query.stream()
        events = []
        
        for doc in docs:
            data = doc.to_dict()
            events.append({
                "id": data["id"],
                "title": f"{data['service_type']} - {data['client_name']}",
                "date": data["event_date"].isoformat(),
                "time": data["event_time"],
                "participants": data["participants"],
                "location": data["location"],
                "status": data["status"]
            })
        
        return events
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener eventos del calendario: {str(e)}"
        )

# Funciones auxiliares
def calculate_estimated_price(service_type: str, total_participants: int, pizzeros_participants: int = 0, party_participants: int = 0) -> float:
    """Calcular precio estimado basado en el tipo de servicio y participantes por servicio"""
    print(f"[CALCULATE] Starting calculation: service_type='{service_type}', pizzeros_participants={pizzeros_participants}, party_participants={party_participants}")

    total = 0

    # Manejar múltiples servicios (separated by comma)
    services = service_type.split(',') if ',' in service_type else [service_type]

    for service in services:
        service = service.strip()

        if service == "workshop" and pizzeros_participants > 0:  # Pizzeros en Acción
            print(f"[DEBUG] Processing workshop with {pizzeros_participants} children...")

            # Nueva estructura de precios
            if pizzeros_participants <= 10:
                # 0-10 children: $13,500 (minimum charge)
                service_total = 13500
                print(f"[DEBUG] <= 10 participants, minimum charge = {service_total}")
            elif pizzeros_participants <= 14:
                # 11-14 children: $10,500 per child
                service_total = 10500 * pizzeros_participants
                print(f"[DEBUG] 11-14 participants, {10500} * {pizzeros_participants} = {service_total}")
            elif pizzeros_participants <= 19:
                # 15-19 children: $9,500 per child
                service_total = 9500 * pizzeros_participants
                print(f"[DEBUG] 15-19 participants, {9500} * {pizzeros_participants} = {service_total}")
            else:
                # 20+ children: $9,000 per child
                service_total = 9000 * pizzeros_participants
                print(f"[DEBUG] 20+ participants, {9000} * {pizzeros_participants} = {service_total}")

            total += service_total
            print(f"[DEBUG] Workshop subtotal: {service_total}")

        elif service == "pizza_party" and party_participants > 0:  # Pizza Party
            print(f"[DEBUG] Processing pizza_party with {party_participants} people...")
            unit_base = 11990  # Precio base por persona
            if party_participants >= 20:
                unit_final = round(unit_base * 0.9)  # 10% descuento para 20+ = 10,791
                print(f"[DEBUG] >= 20 participants, unit_final = {unit_final}")
            else:
                unit_final = unit_base
                print(f"[DEBUG] < 20 participants, unit_final = {unit_final}")

            service_total = unit_final * party_participants
            total += service_total
            print(f"[DEBUG] Pizza party subtotal: {service_total}")

    # Fallback for single service types using total_participants
    if total == 0:
        print(f"[DEBUG] Using fallback calculation with total_participants={total_participants}")
        if "workshop" in service_type:
            # Use new workshop pricing with total_participants
            if total_participants <= 10:
                total = 13500
            elif total_participants <= 14:
                total = 10500 * total_participants
            elif total_participants <= 19:
                total = 9500 * total_participants
            else:
                total = 9000 * total_participants
        elif "pizza_party" in service_type:
            unit_base = 11990
            unit_final = round(unit_base * 0.9) if total_participants >= 20 else unit_base
            total = unit_final * total_participants
        else:
            total = 10000 * total_participants

    result = round(total, 2)
    print(f"[CALCULATE] Final result: {result}")
    return result

async def send_booking_notifications(booking_data: dict):
    """Enviar notificaciones WhatsApp para nuevo agendamiento"""
    # Notificación al cliente
    client_message = f"""
¡Hola {booking_data['client_name']}! 

Tu solicitud de agendamiento ha sido recibida:
📅 Fecha: {booking_data['event_date'].strftime('%d/%m/%Y')}
⏰ Hora: {booking_data['event_time']}
👥 Participantes: {booking_data['participants']}
🍕 Servicio: {booking_data['service_type']}

Te contactaremos pronto para confirmar los detalles.

¡Gracias por elegir Pablo's Pizza!     """
    
    await send_whatsapp_notification(
        booking_data['client_phone'],
        client_message,
        "booking_confirmation"
    )
    
    # Notificación al admin (configurar número en variables de entorno)
    admin_message = f"""
🚨 NUEVO AGENDAMIENTO

Cliente: {booking_data['client_name']}
📧 Email: {booking_data['client_email']}
📞 Teléfono: {booking_data['client_phone']}
📅 Fecha: {booking_data['event_date'].strftime('%d/%m/%Y')}
⏰ Hora: {booking_data['event_time']}
👥 Participantes: {booking_data['participants']}
📍 Ubicación: {booking_data['location']}
🍕 Servicio: {booking_data['service_type']}
💰 Precio estimado: ${booking_data['estimated_price']}

ID: {booking_data['id']}
    """
    
    # Configurar ADMIN_WHATSAPP_NUMBER en variables de entorno
    import os
    admin_phone = os.getenv("ADMIN_WHATSAPP_NUMBER", "+56912345678")  # Número de Pablo's Pizza
    await send_whatsapp_notification(
        admin_phone,
        admin_message,
        "admin_alert"
    )

async def send_confirmation_notification(booking_data: dict):
    """Enviar notificación de confirmación al cliente"""
    message = f"""
✅ ¡AGENDAMIENTO CONFIRMADO!

Hola {booking_data['client_name']},

Tu evento ha sido confirmado:
📅 Fecha: {booking_data['event_date'].strftime('%d/%m/%Y')}
⏰ Hora: {booking_data['event_time']}
👥 Participantes: {booking_data['participants']}
📍 Ubicación: {booking_data['location']}

¡Nos vemos pronto para una experiencia increíble con Pablo's Pizza! 🍕    """
    
    await send_whatsapp_notification(
        booking_data['client_phone'],
        message,
        "confirmation"
    )