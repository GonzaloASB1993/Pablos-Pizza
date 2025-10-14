"""Customer Model - Pydantic schema for customer data validation"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import re


class CustomerBase(BaseModel):
    """Base customer model with common fields"""
    name: str = Field(..., min_length=2, max_length=200, description="Customer full name")
    email: EmailStr = Field(..., description="Customer email address (unique)")
    phone: str = Field(..., min_length=8, max_length=20, description="Customer phone number")
    address: Optional[str] = Field(None, max_length=500, description="Customer physical address")
    notes: Optional[str] = Field(None, max_length=1000, description="Internal notes about customer")

    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format (flexible for international formats)"""
        if not v:
            raise ValueError('Phone number is required')

        # Remove common separators for validation
        cleaned = re.sub(r'[\s\-\(\)]+', '', v)

        # Check if it's a valid format (numbers, optional + prefix)
        if not re.match(r'^\+?\d{8,15}$', cleaned):
            raise ValueError('Phone number must contain 8-15 digits (optional + prefix)')

        return v

    @validator('name')
    def validate_name(cls, v):
        """Validate name is not just whitespace"""
        if not v or not v.strip():
            raise ValueError('Name cannot be empty or just whitespace')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Juan Pérez",
                "email": "juan.perez@email.com",
                "phone": "+56998960858",
                "address": "Av. Providencia 123, Santiago",
                "notes": "Cliente VIP - Prefiere eventos en fin de semana"
            }
        }


class CustomerCreate(CustomerBase):
    """Schema for creating a new customer"""
    pass


class CustomerUpdate(BaseModel):
    """Schema for updating an existing customer (all fields optional)"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=8, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)

    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format if provided"""
        if v:
            cleaned = re.sub(r'[\s\-\(\)]+', '', v)
            if not re.match(r'^\+?\d{8,15}$', cleaned):
                raise ValueError('Phone number must contain 8-15 digits (optional + prefix)')
        return v

    @validator('name')
    def validate_name(cls, v):
        """Validate name if provided"""
        if v and not v.strip():
            raise ValueError('Name cannot be empty or just whitespace')
        return v.strip() if v else None


class CustomerResponse(CustomerBase):
    """Schema for customer response with metadata"""
    id: str = Field(..., description="Unique customer ID")
    total_bookings: int = Field(0, description="Total number of bookings made")
    last_booking_date: Optional[datetime] = Field(None, description="Date of most recent booking")
    created_at: datetime = Field(..., description="Customer creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "cust_abc123xyz",
                "name": "Juan Pérez",
                "email": "juan.perez@email.com",
                "phone": "+56998960858",
                "address": "Av. Providencia 123, Santiago",
                "notes": "Cliente VIP - Prefiere eventos en fin de semana",
                "total_bookings": 5,
                "last_booking_date": "2025-10-01T15:30:00Z",
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-10-01T15:30:00Z"
            }
        }


class CustomerSearchResult(BaseModel):
    """Schema for customer search results"""
    id: str
    name: str
    email: str
    phone: str
    total_bookings: int = 0
    last_booking_date: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "cust_abc123xyz",
                "name": "Juan Pérez",
                "email": "juan.perez@email.com",
                "phone": "+56998960858",
                "total_bookings": 5,
                "last_booking_date": "2025-10-01T15:30:00Z"
            }
        }
