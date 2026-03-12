"""
Customer Model
==============

Represents customers of a business
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class Customer(Base):
    """Represents a customer of a business"""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    # customer_id is the platform's stable identity key for that business.
    # It may come from a real loyalty ID, a normalized name, or a name+phone
    # composite depending on the onboarding strategy the business uses.
    customer_id = Column(String(100), nullable=False)  # Unique ID from business
    name = Column(String(255), nullable=True)
    # Contact fields are optional because many businesses can identify a
    # customer without having a phone number or email on file.
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    # These summary fields are optional convenience attributes. Transactions
    # remain the source of truth, while these can support quick customer views
    # or future denormalized optimizations.
    last_purchase_date = Column(DateTime, nullable=True)
    total_spent = Column(Float, default=0.0)
    total_purchases = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # The customer sits at the center of the retention story: raw purchases,
    # scored snapshots, and later interventions all connect back here.
    business = relationship("Business", back_populates="customers")
    transactions = relationship("Transaction", back_populates="customer", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="customer", uselist=False)

    __table_args__ = (
        # This index is critical because uploads repeatedly resolve external
        # identifiers back to the correct internal customer row.
        Index("idx_business_customer", "business_id", "customer_id"),  # Speed up lookups
    )

    def __repr__(self):
        return f"<Customer(id={self.id}, customer_id={self.customer_id})>"
