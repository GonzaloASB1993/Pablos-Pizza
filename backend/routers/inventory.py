from fastapi import APIRouter, HTTPException, status
from firebase_admin import firestore
from models.schemas import InventoryItemCreate, InventoryItemUpdate, InventoryItem
from services.notification_service import send_inventory_alert
from typing import List, Optional
import uuid
from datetime import datetime

router = APIRouter()
db = firestore.client()

@router.post("/", response_model=InventoryItem)
async def create_inventory_item(item: InventoryItemCreate):
    """Crear nuevo item de inventario"""
    item_id = str(uuid.uuid4())
    
    item_data = {
        "id": item_id,
        **item.model_dump(),
        "last_updated": datetime.now(),
        "needs_restock": item.current_stock <= item.min_stock
    }
    
    try:
        db.collection("inventory").document(item_id).set(item_data)
        return InventoryItem(**item_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear item de inventario: {str(e)}"
        )

@router.get("/", response_model=List[InventoryItem])
async def get_inventory_items(category: str = None, needs_restock: bool = None):
    """Obtener items de inventario con filtros"""
    try:
        query = db.collection("inventory").order_by("name")
        
        if category:
            query = query.where("category", "==", category)
        
        if needs_restock is not None:
            query = query.where("needs_restock", "==", needs_restock)
        
        docs = query.stream()
        
        items = []
        for doc in docs:
            data = doc.to_dict()
            items.append(InventoryItem(**data))
        
        return items
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener inventario: {str(e)}"
        )

@router.put("/{item_id}/stock")
async def update_stock(item_id: str, new_stock: int, operation: str = "set"):
    """
    Actualizar stock de un item
    operation: 'set' (establecer), 'add' (agregar), 'subtract' (quitar)
    """
    try:
        item_ref = db.collection("inventory").document(item_id)
        doc = item_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item de inventario no encontrado"
            )
        
        current_data = doc.to_dict()
        current_stock = current_data["current_stock"]
        min_stock = current_data["min_stock"]
        
        if operation == "set":
            final_stock = new_stock
        elif operation == "add":
            final_stock = current_stock + new_stock
        elif operation == "subtract":
            final_stock = max(0, current_stock - new_stock)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Operación inválida. Use: set, add, subtract"
            )
        
        needs_restock = final_stock <= min_stock
        
        item_ref.update({
            "current_stock": final_stock,
            "needs_restock": needs_restock,
            "last_updated": datetime.now()
        })
        
        # Enviar alerta si es necesario
        if needs_restock and not current_data.get("needs_restock", False):
            await send_inventory_alert(
                current_data["name"],
                final_stock,
                min_stock
            )
        
        return {
            "message": "Stock actualizado exitosamente",
            "new_stock": final_stock,
            "needs_restock": needs_restock
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar stock: {str(e)}"
        )

@router.get("/categories")
async def get_inventory_categories():
    """Obtener todas las categorías de inventario"""
    try:
        docs = db.collection("inventory").stream()
        categories = set()
        
        for doc in docs:
            data = doc.to_dict()
            categories.add(data["category"])
        
        return {"categories": sorted(list(categories))}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener categorías: {str(e)}"
        )

@router.get("/alerts")
async def get_inventory_alerts():
    """Obtener items que necesitan restock"""
    try:
        docs = db.collection("inventory").where(
            "needs_restock", "==", True
        ).order_by("current_stock").stream()
        
        alerts = []
        for doc in docs:
            data = doc.to_dict()
            alerts.append({
                "id": data["id"],
                "name": data["name"],
                "category": data["category"],
                "current_stock": data["current_stock"],
                "min_stock": data["min_stock"],
                "unit": data["unit"],
                "priority": "high" if data["current_stock"] == 0 else "medium"
            })
        
        return {"alerts": alerts, "total": len(alerts)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener alertas: {str(e)}"
        )

@router.get("/{item_id}", response_model=InventoryItem)
async def get_inventory_item(item_id: str):
    """Obtener un item específico de inventario"""
    try:
        doc = db.collection("inventory").document(item_id).get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item de inventario no encontrado"
            )

        data = doc.to_dict()
        return InventoryItem(**data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener item: {str(e)}"
        )

@router.put("/{item_id}", response_model=InventoryItem)
async def update_inventory_item(item_id: str, item_update: InventoryItemUpdate):
    """Actualizar un item de inventario"""
    try:
        item_ref = db.collection("inventory").document(item_id)
        doc = item_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item de inventario no encontrado"
            )

        # Solo actualizar campos que no son None
        update_data = {k: v for k, v in item_update.model_dump().items() if v is not None}
        update_data["last_updated"] = datetime.now()

        # Recalcular needs_restock si se actualizaron stocks
        if "current_stock" in update_data or "min_stock" in update_data:
            current_data = doc.to_dict()
            new_current = update_data.get("current_stock", current_data["current_stock"])
            new_min = update_data.get("min_stock", current_data["min_stock"])
            update_data["needs_restock"] = new_current <= new_min

        item_ref.update(update_data)

        # Obtener datos actualizados
        updated_doc = item_ref.get()
        return InventoryItem(**updated_doc.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar item: {str(e)}"
        )

@router.delete("/{item_id}")
async def delete_inventory_item(item_id: str):
    """Eliminar un item de inventario"""
    try:
        item_ref = db.collection("inventory").document(item_id)
        doc = item_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item de inventario no encontrado"
            )

        item_ref.delete()

        return {"message": "Item de inventario eliminado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar item: {str(e)}"
        )