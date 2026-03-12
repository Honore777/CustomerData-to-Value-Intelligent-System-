"""
Transaction Schemas
===================

Schemas for Transaction model requests/responses
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class TransactionBase(BaseModel):
    """Base transaction info"""
    customer_id: str
    product_name: str
    amount: float = Field(..., gt=0)
    quantity: int = Field(default=1, ge=1)
    purchase_date: datetime
    category: Optional[str] = None


class TransactionCreate(TransactionBase):
    """Create transaction request"""
    pass


class TransactionResponse(TransactionBase):
    """Transaction response"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
