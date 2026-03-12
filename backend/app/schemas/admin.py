from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class AdminBusinessSummary(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    country: str
    currency: str
    is_active: bool
    subscription_status: str
    trial_started_at: Optional[date] = None
    trial_ends_at: Optional[date] = None
    billing_due_date: Optional[date] = None
    last_payment_reminder_sent_at: Optional[datetime] = None
    monthly_price: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    total_locations: int
    total_users: int
    days_until_trial_end: Optional[int] = None
    days_until_billing_due: Optional[int] = None
    needs_payment_reminder: bool


class AdminBusinessesResponse(BaseModel):
    businesses: List[AdminBusinessSummary]


class AdminBusinessUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=20)
    country: Optional[str] = Field(default=None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    subscription_status: Optional[str] = Field(default=None, min_length=2, max_length=50)
    trial_started_at: Optional[date] = None
    trial_ends_at: Optional[date] = None
    billing_due_date: Optional[date] = None
    monthly_price: Optional[float] = Field(default=None, ge=0)


class AdminReminderResponse(BaseModel):
    business_id: int
    recipient_email: str
    subject: str
    message: str
    sent_at: datetime