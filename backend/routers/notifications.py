from fastapi import APIRouter, HTTPException, status
from firebase_admin import firestore
from models.schemas import NotificationCreate, Notification
from services.notification_service import send_whatsapp_notification
from typing import List
from datetime import datetime, timedelta

router = APIRouter()
db = firestore.client()

@router.post("/send")
async def send_notification(notification: NotificationCreate):
    """Enviar notificación WhatsApp manualmente"""
    try:
        success = await send_whatsapp_notification(
            notification.recipient_phone,
            notification.message,
            notification.notification_type
        )
        
        if success:
            return {"message": "Notificación enviada exitosamente"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error enviando notificación"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enviando notificación: {str(e)}"
        )

@router.get("/", response_model=List[Notification])
async def get_notifications(
    limit: int = 100,
    status_filter: str = None,
    days_back: int = 7
):
    """Obtener historial de notificaciones"""
    try:
        # Filtro por fecha (últimos N días)
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        query = db.collection("notifications").where(
            "sent_at", ">=", cutoff_date
        ).order_by(
            "sent_at", 
            direction=firestore.Query.DESCENDING
        )
        
        if status_filter:
            query = query.where("status", "==", status_filter)
        
        docs = query.limit(limit).stream()
        
        notifications = []
        for doc in docs:
            data = doc.to_dict()
            notifications.append(Notification(**data))
        
        return notifications
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener notificaciones: {str(e)}"
        )

@router.get("/stats")
async def get_notification_stats():
    """Estadísticas de notificaciones"""
    try:
        # Últimos 30 días
        cutoff_date = datetime.now() - timedelta(days=30)
        
        docs = db.collection("notifications").where(
            "sent_at", ">=", cutoff_date
        ).stream()
        
        total = 0
        sent = 0
        failed = 0
        by_type = {}
        
        for doc in docs:
            data = doc.to_dict()
            total += 1
            
            status = data.get("status", "unknown")
            if status == "sent":
                sent += 1
            elif status == "failed":
                failed += 1
            
            notification_type = data.get("notification_type", "unknown")
            by_type[notification_type] = by_type.get(notification_type, 0) + 1
        
        success_rate = (sent / total * 100) if total > 0 else 0
        
        return {
            "total_notifications": total,
            "sent": sent,
            "failed": failed,
            "success_rate": round(success_rate, 2),
            "by_type": by_type
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )

@router.post("/test")
async def send_test_notification(phone: str, message: str = "Este es un mensaje de prueba de Pablo's Pizza 🍕"):
    """Enviar notificación de prueba"""
    try:
        success = await send_whatsapp_notification(
            phone,
            message,
            "test"
        )
        
        if success:
            return {"message": "Notificación de prueba enviada exitosamente"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error enviando notificación de prueba"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enviando notificación de prueba: {str(e)}"
        )

@router.post("/reminders/send-daily")
async def send_daily_reminders():
    """Enviar recordatorios diarios automáticos"""
    try:
        from datetime import date
        tomorrow = date.today() + timedelta(days=1)
        
        # Obtener eventos para mañana
        bookings = db.collection("bookings").where(
            "event_date", "==", tomorrow
        ).where(
            "status", "==", "confirmed"
        ).stream()
        
        sent_count = 0
        
        for booking_doc in bookings:
            booking_data = booking_doc.to_dict()
            
            message = f"""
⏰ RECORDATORIO - Pablo's Pizza

Hola {booking_data['client_name']},

Te recordamos tu evento programado para MAÑANA:

📅 Fecha: {booking_data['event_date'].strftime('%d/%m/%Y')}
⏰ Hora: {booking_data['event_time']}
👥 Participantes: {booking_data['participants']}
📍 Ubicación: {booking_data['location']}

¡Estamos emocionados por hacer de tu evento algo especial! 🍕✨

Si tienes alguna pregunta, ¡contáctanos!
            """
            
            success = await send_whatsapp_notification(
                booking_data['client_phone'],
                message,
                "daily_reminder"
            )
            
            if success:
                sent_count += 1
        
        return {
            "message": f"Recordatorios enviados exitosamente",
            "sent_count": sent_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enviando recordatorios diarios: {str(e)}"
        )

@router.post("/bulk-send")
async def send_bulk_notification(
    message: str,
    notification_type: str,
    recipient_filter: str = "all"  # "all", "recent_clients", "active_bookings"
):
    """Enviar notificación masiva"""
    try:
        recipients = []
        
        if recipient_filter == "recent_clients":
            # Clientes de los últimos 30 días
            cutoff_date = datetime.now() - timedelta(days=30)
            bookings = db.collection("bookings").where(
                "created_at", ">=", cutoff_date
            ).stream()
            
            seen_phones = set()
            for booking_doc in bookings:
                booking_data = booking_doc.to_dict()
                phone = booking_data.get("client_phone")
                if phone and phone not in seen_phones:
                    recipients.append(phone)
                    seen_phones.add(phone)
                    
        elif recipient_filter == "active_bookings":
            # Clientes con bookings confirmados futuros
            today = datetime.now().date()
            bookings = db.collection("bookings").where(
                "event_date", ">", today
            ).where(
                "status", "==", "confirmed"
            ).stream()
            
            for booking_doc in bookings:
                booking_data = booking_doc.to_dict()
                phone = booking_data.get("client_phone")
                if phone:
                    recipients.append(phone)
        
        # Enviar a todos los recipients
        sent_count = 0
        failed_count = 0
        
        for phone in recipients:
            success = await send_whatsapp_notification(
                phone,
                message,
                f"bulk_{notification_type}"
            )
            
            if success:
                sent_count += 1
            else:
                failed_count += 1
        
        return {
            "message": "Notificación masiva procesada",
            "total_recipients": len(recipients),
            "sent": sent_count,
            "failed": failed_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enviando notificación masiva: {str(e)}"
        )