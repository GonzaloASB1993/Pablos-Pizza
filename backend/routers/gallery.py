from fastapi import APIRouter, HTTPException, status, UploadFile, File
from firebase_admin import firestore, storage
from models.schemas import GalleryImage
from typing import List, Optional
import uuid
from datetime import datetime
from PIL import Image
import io

router = APIRouter()
db = firestore.client()
bucket = storage.bucket()

@router.post("/upload", response_model=GalleryImage)
async def upload_image(
    file: UploadFile = File(...),
    event_id: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    is_featured: bool = False
):
    """Subir imagen a la galería"""
    
    # Validar tipo de archivo
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser una imagen"
        )
    
    try:
        # Leer y procesar imagen
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Redimensionar si es muy grande (máximo 1920px)
        max_size = (1920, 1920)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convertir de vuelta a bytes
        img_byte_arr = io.BytesIO()
        format = image.format or 'JPEG'
        image.save(img_byte_arr, format=format, quality=85)
        img_byte_arr.seek(0)
        
        # Generar nombre único para el archivo
        image_id = str(uuid.uuid4())
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        blob_name = f"gallery/{image_id}.{file_extension}"
        
        # Subir a Firebase Storage
        blob = bucket.blob(blob_name)
        blob.upload_from_file(img_byte_arr, content_type=file.content_type)
        
        # Hacer público el archivo
        blob.make_public()
        
        # Crear registro en base de datos
        image_data = {
            "id": image_id,
            "url": blob.public_url,
            "event_id": event_id,
            "title": title or f"Imagen {datetime.now().strftime('%d/%m/%Y')}",
            "description": description,
            "uploaded_at": datetime.now(),
            "is_featured": is_featured
        }
        
        db.collection("gallery").document(image_id).set(image_data)
        
        return GalleryImage(**image_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir imagen: {str(e)}"
        )

@router.get("/", response_model=List[GalleryImage])
async def get_gallery_images(
    event_id: Optional[str] = None,
    featured_only: bool = False,
    limit: int = 50
):
    """Obtener imágenes de la galería"""
    try:
        query = db.collection("gallery").order_by(
            "uploaded_at", 
            direction=firestore.Query.DESCENDING
        )
        
        if event_id:
            query = query.where("event_id", "==", event_id)
        
        if featured_only:
            query = query.where("is_featured", "==", True)
        
        docs = query.limit(limit).stream()
        
        images = []
        for doc in docs:
            data = doc.to_dict()
            images.append(GalleryImage(**data))
        
        return images
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener imágenes: {str(e)}"
        )

@router.get("/{image_id}", response_model=GalleryImage)
async def get_image(image_id: str):
    """Obtener imagen específica"""
    try:
        doc = db.collection("gallery").document(image_id).get()
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Imagen no encontrada"
            )
        
        data = doc.to_dict()
        return GalleryImage(**data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener imagen: {str(e)}"
        )

@router.put("/{image_id}")
async def update_image(
    image_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    is_featured: Optional[bool] = None
):
    """Actualizar metadatos de imagen"""
    try:
        image_ref = db.collection("gallery").document(image_id)
        doc = image_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Imagen no encontrada"
            )
        
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if is_featured is not None:
            update_data["is_featured"] = is_featured
        
        if update_data:
            update_data["updated_at"] = datetime.now()
            image_ref.update(update_data)
        
        return {"message": "Imagen actualizada exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar imagen: {str(e)}"
        )

@router.delete("/{image_id}")
async def delete_image(image_id: str):
    """Eliminar imagen de la galería"""
    try:
        # Obtener datos de la imagen
        doc = db.collection("gallery").document(image_id).get()
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Imagen no encontrada"
            )
        
        image_data = doc.to_dict()
        
        # Eliminar de Firebase Storage
        try:
            blob_name = f"gallery/{image_id}"
            blob = bucket.blob(blob_name)
            blob.delete()
        except:
            pass  # Continuar aunque falle la eliminación del archivo
        
        # Eliminar registro de base de datos
        db.collection("gallery").document(image_id).delete()
        
        return {"message": "Imagen eliminada exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar imagen: {str(e)}"
        )

@router.get("/featured/homepage")
async def get_featured_images(limit: int = 6):
    """Obtener imágenes destacadas para la página principal"""
    try:
        docs = db.collection("gallery").where(
            "is_featured", "==", True
        ).order_by(
            "uploaded_at", 
            direction=firestore.Query.DESCENDING
        ).limit(limit).stream()
        
        images = []
        for doc in docs:
            data = doc.to_dict()
            images.append({
                "id": data["id"],
                "url": data["url"],
                "title": data["title"],
                "description": data["description"]
            })
        
        return {"images": images}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener imágenes destacadas: {str(e)}"
        )