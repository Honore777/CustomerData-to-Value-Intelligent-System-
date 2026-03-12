"""
Prediction Schemas
==================

Schemas for Prediction model responses
"""

from pydantic import BaseModel, Field
from datetime import datetime
from app.schemas.common import SegmentEnum


class PredictionBase(BaseModel):
    """Base prediction info"""
    segment: SegmentEnum
    churn_probability: float = Field(..., ge=0, le=1)
    recency: int
    frequency: int
    monetary: float


class PredictionResponse(PredictionBase):
    """Prediction response"""
    id: int
    customer_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
