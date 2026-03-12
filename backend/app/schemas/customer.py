"""
Customer Schemas
================

Schemas for Customer model responses
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional,List


class CustomerBase(BaseModel):
    """Base customer info"""
    customer_id: str = Field(..., min_length=1, max_length=100)
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class CustomerCreate(CustomerBase):
    """Create customer request"""
    pass


class CustomerResponse(CustomerBase):
    """Customer response"""
    id: int
    last_purchase_date: Optional[datetime]
    total_spent: float
    total_purchases: int

    class Config:
        from_attributes = True


class CustomerTransactionSummary(BaseModel):
    id: int
    product_name: str
    amount: float
    quantity: int
    purchase_date: datetime
    category: Optional[str] = None

    class Config:
        from_attributes = True


class CustomerPredictionSummary(BaseModel):
    reference_date: datetime
    segment: str
    churn_probability: float
    recency: int
    frequency: int
    monetary: float

    class Config:
        from_attributes = True


class CustomerDetailResponse(BaseModel):
    id: int
    customer_id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    business_id: int
    last_purchase_date: Optional[datetime] = None
    total_spent: float
    total_purchases: int
    current_prediction: Optional[CustomerPredictionSummary] = None
    recent_transactions: List[CustomerTransactionSummary]

    class Config:
        from_attributes = True