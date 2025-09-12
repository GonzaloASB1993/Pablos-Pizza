from fastapi import APIRouter, HTTPException, status, Query
from firebase_admin import firestore
from models.schemas import ReviewCreate, Review
from typing import List, Optional
import uuid
from datetime import datetime

router = APIRouter()
db = firestore.client()

@router.post("/", response_model=Review)
async def create_review(review: ReviewCreate):
    """Crear nueva reseña"""
    review_id = str(uuid.uuid4())
    
    review_data = {
        "id": review_id,
        **review.model_dump(),
        "created_at": datetime.now(),
        "is_approved": False  # Requiere aprobación manual
    }
    
    try:
        db.collection("reviews").document(review_id).set(review_data)
        return Review(**review_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear reseña: {str(e)}"
        )

@router.get("/", response_model=List[Review])
async def get_reviews(
    approved_only: bool = Query(True, description="Solo mostrar reseñas aprobadas"),
    limit: int = Query(50, description="Número máximo de reseñas")
):
    """Obtener reseñas con filtros"""
    try:
        query = db.collection("reviews").order_by(
            "created_at", 
            direction=firestore.Query.DESCENDING
        )
        
        if approved_only:
            query = query.where("is_approved", "==", True)
        
        docs = query.limit(limit).stream()
        
        reviews = []
        for doc in docs:
            data = doc.to_dict()
            reviews.append(Review(**data))
        
        return reviews
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reseñas: {str(e)}"
        )

@router.get("/stats")
async def get_review_stats():
    """Obtener estadísticas de reseñas"""
    try:
        # Obtener todas las reseñas aprobadas
        docs = db.collection("reviews").where("is_approved", "==", True).stream()
        
        ratings = []
        total_reviews = 0
        
        for doc in docs:
            data = doc.to_dict()
            ratings.append(data["rating"])
            total_reviews += 1
        
        if total_reviews == 0:
            return {
                "total_reviews": 0,
                "average_rating": 0,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        
        average_rating = sum(ratings) / len(ratings)
        
        # Distribución de calificaciones
        rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for rating in ratings:
            rating_distribution[rating] += 1
        
        return {
            "total_reviews": total_reviews,
            "average_rating": round(average_rating, 2),
            "rating_distribution": rating_distribution
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )

@router.get("/{review_id}", response_model=Review)
async def get_review(review_id: str):
    """Obtener reseña específica"""
    try:
        doc = db.collection("reviews").document(review_id).get()
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reseña no encontrada"
            )
        
        data = doc.to_dict()
        return Review(**data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reseña: {str(e)}"
        )

@router.put("/{review_id}/approve")
async def approve_review(review_id: str):
    """Aprobar reseña (solo admin)"""
    try:
        review_ref = db.collection("reviews").document(review_id)
        doc = review_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reseña no encontrada"
            )
        
        review_ref.update({
            "is_approved": True,
            "approved_at": datetime.now()
        })
        
        return {"message": "Reseña aprobada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al aprobar reseña: {str(e)}"
        )

@router.delete("/{review_id}")
async def delete_review(review_id: str):
    """Eliminar reseña (solo admin)"""
    try:
        review_ref = db.collection("reviews").document(review_id)
        doc = review_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reseña no encontrada"
            )
        
        review_ref.delete()
        
        return {"message": "Reseña eliminada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar reseña: {str(e)}"
        )

@router.get("/event/{event_id}")
async def get_reviews_by_event(event_id: str):
    """Obtener reseñas de un evento específico"""
    try:
        docs = db.collection("reviews").where(
            "event_id", "==", event_id
        ).where(
            "is_approved", "==", True
        ).stream()
        
        reviews = []
        for doc in docs:
            data = doc.to_dict()
            reviews.append(Review(**data))
        
        return reviews
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reseñas del evento: {str(e)}"
        )

@router.get("/featured/top")
async def get_featured_reviews(limit: int = Query(6, description="Número de reseñas destacadas")):
    """Obtener reseñas destacadas para mostrar en la página principal"""
    try:
        docs = db.collection("reviews").where(
            "is_approved", "==", True
        ).where(
            "rating", ">=", 4  # Solo 4 y 5 estrellas
        ).order_by(
            "rating", direction=firestore.Query.DESCENDING
        ).order_by(
            "created_at", direction=firestore.Query.DESCENDING
        ).limit(limit).stream()
        
        reviews = []
        for doc in docs:
            data = doc.to_dict()
            reviews.append(Review(**data))
        
        return reviews
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reseñas destacadas: {str(e)}"
        )