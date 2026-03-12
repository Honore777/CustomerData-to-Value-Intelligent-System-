"""
Common Schemas
==============

Enums and shared schemas used across the application
"""

from enum import Enum


class SegmentEnum(str, Enum):
    """
    Customer segment types based on RFM analysis.
    
    CHURNED: High recency, Low frequency, Low monetary → customers who have left
    AT_RISK: Medium-high recency, Medium frequency, Medium monetary → at risk of leaving
    ACTIVE: Low recency, High frequency, Medium+ monetary → regularly buying
    LOYAL: Very low recency, Very high frequency, High monetary → top customers
    """
    # Keeping these values centralized prevents one route, model, or frontend
    # component from inventing a slightly different segment vocabulary.
    CHURNED = "churned"
    AT_RISK = "at_risk"
    ACTIVE = "active"
    LOYAL = "loyal"
