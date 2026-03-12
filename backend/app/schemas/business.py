"""
Business Schemas
================

Schemas for Business model CRUD operations
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class BusinessBase(BaseModel):
    """Base business info"""
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None


class BusinessCreate(BusinessBase):
    """Create business request"""
    country: str = Field(default="Rwanda")


class BusinessResponse(BusinessBase):
    """Business response"""
    id: int
    country: str
    currency: str
    timezone: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True  # Allows reading from SQLAlchemy ORM models
