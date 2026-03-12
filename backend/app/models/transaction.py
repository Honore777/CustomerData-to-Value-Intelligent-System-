"""
Transaction Model
=================

Represents individual purchase transactions
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class Transaction(Base):
    """Represents a single purchase transaction at a specific location"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    # Transactions are the immutable behavioral foundation of the whole system.
    # Every score, comparison, and intervention analysis ultimately traces back
    # to these rows.
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)  # Which branch?
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_name = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    quantity = Column(Integer, default=1)
    purchase_date = Column(DateTime, nullable=False)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships connect this raw behavior row back to the tenant, branch,
    # and customer it belongs to.
    business = relationship("Business", back_populates="transactions")
    location = relationship("Location", back_populates="transactions")
    customer = relationship("Customer", back_populates="transactions")

    __table_args__ = (
        # These indexes accelerate the exact filters used by the scoring window
        # and dashboard rollups: by branch, by business, and by customer over time.
        Index("idx_location_date", "location_id", "purchase_date"),  # Speed up per-location queries
        Index("idx_business_date", "business_id", "purchase_date"),
        Index("idx_customer_date", "customer_id", "purchase_date"),
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, location_id={self.location_id}, customer_id={self.customer_id}, amount={self.amount})>"
