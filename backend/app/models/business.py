"""
Business and Location Models
=============================

Business: Represents a supermarket/retail chain
Location: Represents a physical branch of a business
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Date, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class Business(Base):
    """Represents a supermarket/retail business using the platform"""
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(20), nullable=True)
    country = Column(String(100), nullable=False, default="Rwanda")
    currency = Column(String(10), default="RWF")
    timezone = Column(String(50), default="Africa/Kigali")
    is_active = Column(Boolean, default=True)  # Admin controlls this for payment
    subscription_status = Column(String(50), default="trial")
    trial_started_at = Column(Date, nullable=True)
    trial_ends_at = Column(Date, nullable=True)
    billing_due_date = Column(Date, nullable=True)
    last_payment_reminder_sent_at = Column(DateTime, nullable=True)
    monthly_price = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # These fields describe how this business naturally operates.
    # They allow the same platform to support different retail rhythms,
    # from a fast-moving kiosk to a pharmacy to a supermarket chain.
    upload_frequency = Column(String(50), default="weekly")  # "daily", "weekly", "bi-weekly", "monthly", "quarterly", "irregular"
    reference_period_days = Column(Integer, default=60)  # Lookback window for RFM calculation
    allow_manual_reference_date = Column(Boolean, default=False)  # For irregular uploads, user sets reference_date
    
    # These thresholds are the business-specific definition of healthy vs risky
    # customer behavior. They are the knobs the owner can tune without needing
    # to understand the internals of the scoring formula.
    recency_threshold_days = Column(Integer, default=7)  # Days without purchase = inactive
    frequency_threshold = Column(Integer, default=5)  # Minimum purchases in reference period
    monetary_threshold = Column(Float, default=500)  # Minimum amount spent in reference period

    # Column mapping stores the business's spreadsheet vocabulary so we can
    # translate future uploads into one standard internal schema automatically.
    column_mapping = Column(JSON, default={
        'uses_locations': False,
        'identity_strategy': 'customer_id',
        'agreed_identifier_label': 'Customer ID',
        'customer_id_column': 'customer_id',
        'customer_name_column': None,
        'phone_column': None,
        'email_column': None,
        'location_code_column': None,
        'date_column': 'purchase_date',
        'amount_column': 'amount',
        'product_column': 'product_name'
    })
    
    # Date format is stored separately because the same file labels can still
    # use different local date conventions across businesses or countries.
    date_format = Column(String(50), default='%Y-%m-%d')  # How they format dates
    
    # These relationships describe the full tenant data estate: raw activity,
    # scored snapshots, action tracking, and future learning artifacts.
    customers = relationship("Customer", back_populates="business", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="business", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="business", cascade="all, delete-orphan")
    prediction_history = relationship("PredictionHistory", back_populates="business", cascade="all, delete-orphan")
    model_metadata = relationship("ModelMetadata", back_populates="business", cascade="all, delete-orphan")
    model_evaluations = relationship("ModelEvaluation", back_populates="business", cascade="all, delete-orphan")
    business_actions = relationship("BusinessAction", back_populates="business", cascade="all, delete-orphan")
    monthly_metrics = relationship("MonthlyMetrics", back_populates="business", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="business", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Business(id={self.id}, name={self.name}, country={self.country})>"


class Location(Base):
    """
    Represents a physical location/branch of a business.
    
    Example:
    - Business: "ABC Supermarkets" (Rwanda)
    - Location 1: "Kigali Town" (KGL_01)
    - Location 2: "Kigali Suburb" (KGL_02)
    - Location 3: "Butare" (BUT_01)
    
    Each location:
    - Has independent transactions
    - Gets own RFM calculations
    - Gets own predictions
    - Can have own manager(s)
    """
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    location_code = Column(String(50), nullable=False)  # "KGL_01", "KGL_02", etc
    name = Column(String(255), nullable=False)  # "Kigali Town", "Kigali Suburb"
    city = Column(String(100), nullable=True)  # Kigali, Butare, etc
    phone = Column(String(20), nullable=True)
    manager_name = Column(String(255), nullable=True)
    manager_email = Column(String(255), nullable=True)
    
    # Location-level overrides matter when one branch has a different customer
    # cycle from the rest of the business. If a field is NULL, the business
    # default still applies.
    reference_period_days = Column(Integer, nullable=True)  # NULL = use business default
    recency_threshold_days = Column(Integer, nullable=True)
    frequency_threshold = Column(Integer, nullable=True)
    monetary_threshold = Column(Float, nullable=True)
    column_mapping = Column(JSON, nullable=True)
    date_format = Column(String(50), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # These relationships let every branch keep its own operational truth while
    # still rolling up to the parent business for overall reporting.
    business = relationship("Business", back_populates="locations")
    transactions = relationship("Transaction", back_populates="location", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="location", cascade="all, delete-orphan")
    prediction_history = relationship("PredictionHistory", back_populates="location", cascade="all, delete-orphan")
    business_actions = relationship("BusinessAction", back_populates="location", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_business_location", "business_id", "location_code"),
        Index("idx_location_active", "business_id", "is_active"),
    )
    
    def __repr__(self):
        return f"<Location(id={self.id}, code={self.location_code}, name={self.name})>"
