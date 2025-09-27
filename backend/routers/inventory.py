from fastapi import APIRouter, HTTPException, status
from firebase_admin import firestore
from models.schemas import (
    InventoryItemCreate, InventoryItemUpdate, InventoryItem,
    InventoryMovementCreate, InventoryMovement, StockUpdateRequest,
    MovementType
)
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

# Funciones auxiliares para costo promedio ponderado
async def calculate_weighted_average_cost(item_id: str, new_quantity: float, new_cost: float):
    """Calcular nuevo costo promedio ponderado"""
    try:
        item_ref = db.collection("inventory").document(item_id)
        doc = item_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item de inventario no encontrado"
            )

        current_data = doc.to_dict()
        current_stock = current_data.get("current_stock", 0)
        current_avg_cost = current_data.get("weighted_avg_cost", current_data.get("cost_per_unit", 0))

        # Si no hay stock actual, el nuevo costo es el costo promedio
        if current_stock <= 0:
            new_avg_cost = new_cost
            new_total_value = new_quantity * new_cost
        else:
            # Cálculo del costo promedio ponderado
            current_total_value = current_stock * current_avg_cost
            new_total_value = current_total_value + (new_quantity * new_cost)
            new_total_stock = current_stock + new_quantity

            if new_total_stock > 0:
                new_avg_cost = new_total_value / new_total_stock
            else:
                new_avg_cost = current_avg_cost

        return {
            "new_avg_cost": new_avg_cost,
            "new_total_value": new_total_value,
            "previous_avg_cost": current_avg_cost
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al calcular costo promedio: {str(e)}"
        )

async def create_inventory_movement(movement_data: dict):
    """Crear un movimiento de inventario"""
    try:
        movement_id = str(uuid.uuid4())
        movement_data["id"] = movement_id
        movement_data["created_at"] = datetime.now()

        db.collection("inventory_movements").document(movement_id).set(movement_data)
        return movement_id

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear movimiento: {str(e)}"
        )

@router.post("/movements/", response_model=dict)
async def update_stock_with_movement(request: StockUpdateRequest):
    """Actualizar stock con costo promedio ponderado y registrar movimiento"""
    try:
        item_ref = db.collection("inventory").document(request.item_id)
        doc = item_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item de inventario no encontrado"
            )

        current_data = doc.to_dict()
        stock_before = current_data.get("current_stock", 0)
        avg_cost_before = current_data.get("weighted_avg_cost", current_data.get("cost_per_unit", 0))

        # Determinar si es entrada o salida
        is_inbound = request.movement_type in [MovementType.PURCHASE, MovementType.PRODUCTION, MovementType.RETURN, MovementType.ADJUSTMENT]

        if is_inbound and request.quantity > 0:
            # Entrada de inventario - calcular nuevo costo promedio
            cost_calc = await calculate_weighted_average_cost(
                request.item_id,
                request.quantity,
                request.cost_per_unit
            )

            new_stock = stock_before + request.quantity
            new_avg_cost = cost_calc["new_avg_cost"]
            new_total_value = cost_calc["new_total_value"]

        elif not is_inbound and request.quantity > 0:
            # Salida de inventario - usar costo promedio actual
            new_stock = max(0, stock_before - request.quantity)
            new_avg_cost = avg_cost_before
            new_total_value = new_stock * new_avg_cost
            actual_quantity = -(min(request.quantity, stock_before))  # Negativo para salida

        elif request.movement_type == MovementType.ADJUSTMENT:
            # Ajuste - puede ser positivo o negativo
            new_stock = max(0, stock_before + request.quantity)
            if request.quantity > 0:
                # Ajuste positivo - calcular nuevo promedio
                cost_calc = await calculate_weighted_average_cost(
                    request.item_id,
                    request.quantity,
                    request.cost_per_unit
                )
                new_avg_cost = cost_calc["new_avg_cost"]
                new_total_value = cost_calc["new_total_value"]
            else:
                # Ajuste negativo - usar costo actual
                new_avg_cost = avg_cost_before
                new_total_value = new_stock * new_avg_cost
            actual_quantity = request.quantity
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de movimiento o cantidad inválidos"
            )

        # Actualizar item de inventario
        needs_restock = new_stock <= current_data.get("min_stock", 0)

        update_data = {
            "current_stock": new_stock,
            "weighted_avg_cost": new_avg_cost,
            "total_value": new_total_value,
            "cost_per_unit": new_avg_cost,  # Mantener compatibilidad
            "needs_restock": needs_restock,
            "last_updated": datetime.now()
        }

        item_ref.update(update_data)

        # Crear movimiento de inventario
        movement_data = {
            "item_id": request.item_id,
            "item_name": current_data.get("name"),
            "movement_type": request.movement_type,
            "quantity": actual_quantity if 'actual_quantity' in locals() else request.quantity,
            "unit": current_data.get("unit"),
            "cost_per_unit": request.cost_per_unit,
            "total_cost": abs(actual_quantity if 'actual_quantity' in locals() else request.quantity) * request.cost_per_unit,
            "reference_id": request.reference_id,
            "reference_type": request.reference_type,
            "notes": request.notes,
            "supplier": request.supplier,
            "stock_before": stock_before,
            "stock_after": new_stock,
            "avg_cost_before": avg_cost_before,
            "avg_cost_after": new_avg_cost
        }

        movement_id = await create_inventory_movement(movement_data)

        # Enviar alerta si es necesario
        if needs_restock and not current_data.get("needs_restock", False):
            await send_inventory_alert(
                current_data["name"],
                new_stock,
                current_data.get("min_stock", 0)
            )

        return {
            "message": "Stock actualizado exitosamente",
            "movement_id": movement_id,
            "stock_before": stock_before,
            "stock_after": new_stock,
            "avg_cost_before": avg_cost_before,
            "avg_cost_after": new_avg_cost,
            "needs_restock": needs_restock
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar stock: {str(e)}"
        )

@router.get("/movements/", response_model=List[InventoryMovement])
async def get_inventory_movements(
    item_id: str = None,
    movement_type: MovementType = None,
    limit: int = 100
):
    """Obtener movimientos de inventario"""
    try:
        query = db.collection("inventory_movements").order_by("created_at", direction=firestore.Query.DESCENDING)

        if item_id:
            query = query.where("item_id", "==", item_id)

        if movement_type:
            query = query.where("movement_type", "==", movement_type)

        docs = query.limit(limit).stream()

        movements = []
        for doc in docs:
            data = doc.to_dict()
            movements.append(InventoryMovement(**data))

        return movements

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener movimientos: {str(e)}"
        )

@router.get("/movements/{movement_id}", response_model=InventoryMovement)
async def get_inventory_movement(movement_id: str):
    """Obtener un movimiento específico"""
    try:
        doc = db.collection("inventory_movements").document(movement_id).get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movimiento no encontrado"
            )

        return InventoryMovement(**doc.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener movimiento: {str(e)}"
        )