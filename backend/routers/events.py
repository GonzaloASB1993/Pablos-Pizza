from fastapi import APIRouter, HTTPException, status
from firebase_admin import firestore
from models.schemas import EventCreate, Event, EventFinancials
from services.notification_service import send_review_request
from typing import List
import uuid
from datetime import datetime

router = APIRouter()
db = firestore.client()

@router.post("/", response_model=Event)
async def create_event(event: EventCreate):
    """Crear registro de evento realizado"""
    event_id = str(uuid.uuid4())
    
    event_data = {
        "id": event_id,
        **event.model_dump(),
        "created_at": datetime.now()
    }
    
    try:
        # Guardar evento
        db.collection("events").document(event_id).set(event_data)
        
        # Actualizar estado del booking a completado
        booking_ref = db.collection("bookings").document(event.booking_id)
        booking_ref.update({
            "status": "completed",
            "updated_at": datetime.now()
        })
        
        # Programar envío de solicitud de review (después de 2 horas)
        # En producción, usar un scheduler como Celery
        
        return Event(**event_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear evento: {str(e)}"
        )

@router.get("/", response_model=List[Event])
async def get_events(limit: int = 100):
    """Obtener todos los eventos realizados"""
    try:
        docs = db.collection("events").order_by(
            "start_time", 
            direction=firestore.Query.DESCENDING
        ).limit(limit).stream()
        
        events = []
        for doc in docs:
            data = doc.to_dict()
            events.append(Event(**data))
        
        return events
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener eventos: {str(e)}"
        )

@router.get("/{event_id}", response_model=Event)
async def get_event(event_id: str):
    """Obtener evento específico"""
    try:
        doc = db.collection("events").document(event_id).get()
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento no encontrado"
            )
        
        data = doc.to_dict()
        return Event(**data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener evento: {str(e)}"
        )

@router.put("/{event_id}/financials")
async def update_event_financials(event_id: str, financials: EventFinancials):
    """Actualizar información financiera del evento"""
    try:
        event_ref = db.collection("events").document(event_id)
        doc = event_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento no encontrado"
            )
        
        event_ref.update({
            "financials": financials.model_dump(),
            "updated_at": datetime.now()
        })
        
        return {"message": "Información financiera actualizada"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar información financiera: {str(e)}"
        )

@router.post("/{event_id}/request-review")
async def request_event_review(event_id: str):
    """Enviar solicitud de review para el evento"""
    try:
        # Verificar que el evento existe
        doc = db.collection("events").document(event_id).get()
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento no encontrado"
            )
        
        success = await send_review_request(event_id)
        
        if success:
            return {"message": "Solicitud de review enviada exitosamente"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error enviando solicitud de review"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al solicitar review: {str(e)}"
        )

@router.get("/booking/{booking_id}")
async def get_events_by_booking(booking_id: str):
    """Obtener eventos asociados a un booking"""
    try:
        docs = db.collection("events").where(
            "booking_id", "==", booking_id
        ).stream()
        
        events = []
        for doc in docs:
            data = doc.to_dict()
            events.append(Event(**data))
        
        return events
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener eventos: {str(e)}"
        )