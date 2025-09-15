from fastapi import APIRouter, HTTPException, Depends, status
from firebase_admin import firestore
from models.schemas import BookingCreate, BookingUpdate, Booking, BookingStatus
from services.notification_service import send_whatsapp_notification
from services.email_service import send_confirmation_email
from typing import List
import uuid
from datetime import datetime

router = APIRouter()

def get_firestore_client():
    """Get Firestore client instance"""
    return firestore.client()

@router.post("/", response_model=Booking)
async def create_booking(booking: BookingCreate):
    """Crear nuevo agendamiento"""
    booking_id = str(uuid.uuid4())
    
    # Calcular precio estimado basado en servicio y participantes
    estimated_price = calculate_estimated_price(booking.service_type, booking.participants)
    
    booking_data = {
        "id": booking_id,
        **booking.model_dump(),
        "status": BookingStatus.PENDING,
        "created_at": datetime.now(),
        "estimated_price": estimated_price
    }
    
    try:
        # Guardar en Firestore
        db = get_firestore_client()
        db.collection("bookings").document(booking_id).set(booking_data)
        
        # Enviar notificación WhatsApp al cliente confirmando que se registró el agendamiento
        client_message = f"""
¡Hola {booking_data['client_name']}!

Tu solicitud de agendamiento ha sido recibida:
📅 Fecha: {booking_data['event_date'].strftime('%d/%m/%Y')}
⏰ Hora: {booking_data['event_time']}
👥 Participantes: {booking_data['participants']}
🍕 Servicio: {'Pizzeros en Acción' if booking_data['service_type'] == 'workshop' else 'Pizza Party'}

Pronto nos pondremos en contacto contigo para confirmar los detalles.

¡Gracias por elegir Pablo's Pizza! 🍕
        """

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
            bookings.append(Booking(**data))
        
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
        update_data = booking_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now()
        
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
def calculate_estimated_price(service_type: str, participants: int) -> float:
    """Calcular precio estimado basado en el tipo de servicio y participantes"""
    base_prices = {
        "workshop": 25.0,  # $25 por niño en taller
        "pizza_party": 20.0  # $20 por persona en pizza party
    }
    
    base_price = base_prices.get(service_type, 20.0)
    total = base_price * participants
    
    # Descuento por volumen
    if participants >= 20:
        total *= 0.9  # 10% descuento
    elif participants >= 10:
        total *= 0.95  # 5% descuento
    
    return round(total, 2)

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

¡Gracias por elegir Pablo's Pizza! 🍕
    """
    
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

¡Nos vemos pronto para una experiencia increíble con Pablo's Pizza! 🍕🎉
    """
    
    await send_whatsapp_notification(
        booking_data['client_phone'],
        message,
        "confirmation"
    )