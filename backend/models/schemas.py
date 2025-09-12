from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ServiceType(str, Enum):
    WORKSHOP = "workshop"  # Taller para niños
    PIZZA_PARTY = "pizza_party"  # Evento con servicio de pizzas

class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class EventType(str, Enum):
    BIRTHDAY = "birthday"
    CORPORATE = "corporate"
    SCHOOL = "school"
    PRIVATE = "private"

# Schemas para Bookings
class BookingBase(BaseModel):
    client_name: str
    client_email: EmailStr
    client_phone: str
    service_type: ServiceType
    event_type: EventType
    event_date: datetime
    event_time: str
    duration_hours: int
    participants: int
    location: str
    special_requests: Optional[str] = None

class BookingCreate(BookingBase):
    pass

class BookingUpdate(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[EmailStr] = None
    client_phone: Optional[str] = None
    event_date: Optional[datetime] = None
    event_time: Optional[str] = None
    participants: Optional[int] = None
    location: Optional[str] = None
    special_requests: Optional[str] = None
    status: Optional[BookingStatus] = None

class Booking(BookingBase):
    id: str
    status: BookingStatus = BookingStatus.PENDING
    created_at: datetime
    updated_at: Optional[datetime] = None
    estimated_price: Optional[float] = None

# Schemas para Events (eventos realizados)
class EventFinancials(BaseModel):
    income: float
    expenses: List[Dict[str, Any]]  # [{"description": "Ingredientes", "amount": 150.00}]
    total_expenses: float
    profit: float

class EventBase(BaseModel):
    booking_id: str
    actual_participants: int
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None
    photos: Optional[List[str]] = []

class EventCreate(EventBase):
    financials: EventFinancials

class Event(EventBase):
    id: str
    financials: EventFinancials
    created_at: datetime

# Schemas para Gallery
class GalleryImage(BaseModel):
    id: str
    url: str
    event_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    uploaded_at: datetime
    is_featured: bool = False

# Schemas para Reviews
class ReviewBase(BaseModel):
    client_name: str
    client_email: EmailStr
    event_id: Optional[str] = None
    rating: int
    comment: str
    
    @validator('rating')
    def rating_must_be_valid(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating debe estar entre 1 y 5')
        return v

class ReviewCreate(ReviewBase):
    pass

class Review(ReviewBase):
    id: str
    created_at: datetime
    is_approved: bool = False

# Schemas para Inventory
class InventoryItemBase(BaseModel):
    name: str
    category: str  # "ingredientes", "utensilios", "equipos"
    current_stock: int
    min_stock: int
    unit: str  # "kg", "unidades", "litros"
    cost_per_unit: float

class InventoryItemCreate(InventoryItemBase):
    pass

class InventoryItem(InventoryItemBase):
    id: str
    last_updated: datetime
    needs_restock: bool = False

# Schemas para Reports
class MonthlyReport(BaseModel):
    month: int
    year: int
    total_events: int
    total_income: float
    total_expenses: float
    total_profit: float
    avg_participants: float
    most_popular_service: str
    client_retention_rate: float

# Schemas para Notifications
class NotificationBase(BaseModel):
    recipient_phone: str
    message: str
    notification_type: str  # "booking_confirmation", "reminder", "admin_alert"

class NotificationCreate(NotificationBase):
    pass

class Notification(NotificationBase):
    id: str
    sent_at: datetime
    status: str  # "sent", "failed", "pending"

# Schemas para Chat
class ChatMessage(BaseModel):
    id: str
    sender_id: str
    sender_name: str
    message: str
    timestamp: datetime
    is_admin: bool = False

class ChatRoom(BaseModel):
    id: str
    client_name: str
    client_email: EmailStr
    is_active: bool = True
    created_at: datetime
    last_message_at: Optional[datetime] = None