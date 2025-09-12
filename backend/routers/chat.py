from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect
from firebase_admin import firestore
from models.schemas import ChatMessage, ChatRoom
from typing import List, Dict
import uuid
from datetime import datetime
import json

router = APIRouter()
db = firestore.client()

# Conexiones WebSocket activas
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.admin_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, room_id: str, is_admin: bool = False):
        await websocket.accept()
        if is_admin:
            self.admin_connections.append(websocket)
        else:
            self.active_connections[room_id] = websocket

    def disconnect(self, websocket: WebSocket, room_id: str = None, is_admin: bool = False):
        if is_admin and websocket in self.admin_connections:
            self.admin_connections.remove(websocket)
        elif room_id and room_id in self.active_connections:
            del self.active_connections[room_id]

    async def send_message_to_room(self, room_id: str, message: dict):
        if room_id in self.active_connections:
            await self.active_connections[room_id].send_text(json.dumps(message))

    async def send_message_to_admins(self, message: dict):
        for connection in self.admin_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                self.admin_connections.remove(connection)

manager = ConnectionManager()

@router.post("/rooms", response_model=ChatRoom)
async def create_chat_room(client_name: str, client_email: str):
    """Crear nueva sala de chat"""
    room_id = str(uuid.uuid4())
    
    room_data = {
        "id": room_id,
        "client_name": client_name,
        "client_email": client_email,
        "is_active": True,
        "created_at": datetime.now(),
        "last_message_at": None
    }
    
    try:
        db.collection("chat_rooms").document(room_id).set(room_data)
        
        # Notificar a administradores sobre nueva sala
        await manager.send_message_to_admins({
            "type": "new_room",
            "room": room_data
        })
        
        return ChatRoom(**room_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear sala de chat: {str(e)}"
        )

@router.get("/rooms", response_model=List[ChatRoom])
async def get_chat_rooms(active_only: bool = True):
    """Obtener salas de chat (para administradores)"""
    try:
        query = db.collection("chat_rooms").order_by(
            "last_message_at", 
            direction=firestore.Query.DESCENDING
        )
        
        if active_only:
            query = query.where("is_active", "==", True)
        
        docs = query.stream()
        
        rooms = []
        for doc in docs:
            data = doc.to_dict()
            rooms.append(ChatRoom(**data))
        
        return rooms
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener salas de chat: {str(e)}"
        )

@router.get("/rooms/{room_id}/messages", response_model=List[ChatMessage])
async def get_chat_messages(room_id: str, limit: int = 50):
    """Obtener mensajes de una sala de chat"""
    try:
        docs = db.collection("chat_messages").where(
            "room_id", "==", room_id
        ).order_by(
            "timestamp", 
            direction=firestore.Query.ASCENDING
        ).limit(limit).stream()
        
        messages = []
        for doc in docs:
            data = doc.to_dict()
            messages.append(ChatMessage(**data))
        
        return messages
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener mensajes: {str(e)}"
        )

@router.post("/rooms/{room_id}/messages")
async def send_message(room_id: str, message: str, sender_name: str, is_admin: bool = False):
    """Enviar mensaje a sala de chat"""
    message_id = str(uuid.uuid4())
    
    message_data = {
        "id": message_id,
        "room_id": room_id,
        "sender_id": "admin" if is_admin else "client",
        "sender_name": sender_name,
        "message": message,
        "timestamp": datetime.now(),
        "is_admin": is_admin
    }
    
    try:
        # Guardar mensaje
        db.collection("chat_messages").document(message_id).set(message_data)
        
        # Actualizar última actividad de la sala
        db.collection("chat_rooms").document(room_id).update({
            "last_message_at": datetime.now()
        })
        
        # Enviar mensaje via WebSocket
        if is_admin:
            await manager.send_message_to_room(room_id, {
                "type": "message",
                "message": message_data
            })
        else:
            await manager.send_message_to_admins({
                "type": "message",
                "room_id": room_id,
                "message": message_data
            })
        
        return {"message": "Mensaje enviado exitosamente"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al enviar mensaje: {str(e)}"
        )

@router.put("/rooms/{room_id}/close")
async def close_chat_room(room_id: str):
    """Cerrar sala de chat"""
    try:
        room_ref = db.collection("chat_rooms").document(room_id)
        doc = room_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sala de chat no encontrada"
            )
        
        room_ref.update({
            "is_active": False,
            "closed_at": datetime.now()
        })
        
        # Notificar cierre via WebSocket
        await manager.send_message_to_room(room_id, {
            "type": "room_closed",
            "message": "El chat ha sido cerrado por un administrador"
        })
        
        return {"message": "Sala de chat cerrada"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cerrar sala de chat: {str(e)}"
        )

# WebSocket endpoints
@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """WebSocket para clientes"""
    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Procesar mensaje
            await send_message(
                room_id=room_id,
                message=message_data["message"],
                sender_name=message_data["sender_name"],
                is_admin=False
            )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)

@router.websocket("/ws/admin")
async def admin_websocket_endpoint(websocket: WebSocket):
    """WebSocket para administradores"""
    await manager.connect(websocket, None, is_admin=True)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Procesar mensaje de admin
            await send_message(
                room_id=message_data["room_id"],
                message=message_data["message"],
                sender_name=message_data["sender_name"],
                is_admin=True
            )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, is_admin=True)

@router.get("/rooms/{room_id}/status")
async def get_room_status(room_id: str):
    """Verificar estado de la sala de chat"""
    try:
        doc = db.collection("chat_rooms").document(room_id).get()
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sala de chat no encontrada"
            )
        
        room_data = doc.to_dict()
        
        return {
            "is_active": room_data["is_active"],
            "admin_online": len(manager.admin_connections) > 0,
            "client_online": room_id in manager.active_connections
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estado de sala: {str(e)}"
        )