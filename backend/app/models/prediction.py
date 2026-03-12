"""
Prediction Models
=================

Prediction: RFM predictions for customers
PredictionHistory: Track segment changes over time
ModelMetadata: ML model metadata
ModelEvaluation: Model performance metrics
BusinessAction: Actions taken based on predictions
MonthlyMetrics: Aggregated ROI metrics
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Date, Text, Index
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class Prediction(Base):
    """Represents a churn prediction snapshot for a customer at a specific location and reference_date"""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    # The business/location pair keeps every tenant isolated while still
    # allowing branch-level comparisons inside the same company.
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)  # Per location
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # CRITICAL: Reference date for this snapshot
    reference_date = Column(Date, nullable=False)
    
    # These are the snapshot outputs the business sees on the dashboard.
    # churn_probability is now a direct risk score on a 0-1 scale, while
    # segment is the operational label used for recommendations and follow-up.
    segment = Column(String(50), nullable=False)
    churn_probability = Column(Float, nullable=False)
    
    # Store the underlying RFM metrics alongside the snapshot output so the
    # risk state remains explainable even months later during review or audit.
    recency = Column(Integer, nullable=False)
    frequency = Column(Integer, nullable=False)
    monetary = Column(Float, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships connect this snapshot to the business, branch, customer,
    # and any later history records that describe movement over time.
    business = relationship("Business", back_populates="predictions")
    location = relationship("Location", back_populates="predictions")
    customer = relationship("Customer", back_populates="predictions")
    history = relationship("PredictionHistory", back_populates="prediction", cascade="all, delete-orphan")

    __table_args__ = (
        # These indexes support the most common dashboard queries:
        # newest snapshot by location, newest snapshot by business, and
        # filtering customers by segment within one location.
        Index("idx_location_reference_date", "location_id", "reference_date"),  # Per-location snapshots
        Index("idx_business_reference_date", "business_id", "reference_date"),
        Index("idx_segment", "location_id", "segment"),
    )

    def __repr__(self):
        return f"<Prediction(loc={self.location_id}, customer_id={self.customer_id}, segment={self.segment})>"


class ModelMetadata(Base):
    """Stores metadata about future supervised models when the product reaches that stage"""
    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, unique=True)
    # This table is intentionally kept for the later ML phase. The current
    # production workflow does not depend on it, but historical snapshots and
    # intervention outcomes will eventually make this table useful again.
    model_path = Column(String(500), nullable=False)  # Path to serialized model artifact
    training_date = Column(DateTime, nullable=False)
    accuracy = Column(Float, nullable=True)  # Model accuracy on test set
    num_samples = Column(Integer, nullable=False)  # How many customers trained on
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    business = relationship("Business", back_populates="model_metadata")

    def __repr__(self):
        return f"<ModelMetadata(business_id={self.business_id}, accuracy={self.accuracy})>"


class PredictionHistory(Base):
    """Tracks segment changes over time per location"""
    __tablename__ = "prediction_history"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False)
    
    # These fields answer the business question "where was this customer
    # before, and where are they now?" without recalculating old snapshots.
    previous_segment = Column(String(50), nullable=True)
    current_segment = Column(String(50), nullable=False)
    
    # Reference dates
    previous_reference_date = Column(Date, nullable=True)
    current_reference_date = Column(Date, nullable=False)
    
    # Change metadata supports improvement tracking after interventions.
    # segment_improved is a quick business-facing signal, while
    # days_in_previous_segment helps quantify how long a risky state lasted.
    segment_improved = Column(Boolean, nullable=True)
    days_in_previous_segment = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", back_populates="prediction_history")
    location = relationship("Location", back_populates="prediction_history")
    customer = relationship("Customer")
    prediction = relationship("Prediction", back_populates="history")
    
    __table_args__ = (
        Index("idx_location_history", "location_id", "current_reference_date"),
    )
    
    def __repr__(self):
        return f"<PredictionHistory(loc={self.location_id}, {self.previous_segment}→{self.current_segment})>"


class ModelEvaluation(Base):
    """Tracks model performance improvements over time when supervised ML is introduced"""
    __tablename__ = "model_evaluation"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    
    # These fields are not active in the direct-scoring product today, but they
    # define the evaluation contract for the later true ML phase.
    evaluation_date = Column(Date, nullable=False)  # When we evaluated
    reference_date = Column(Date, nullable=False)  # Snapshot being evaluated
    
    # Performance metrics
    accuracy = Column(Float, nullable=False)  # % correct predictions
    precision = Column(Float, nullable=True)  # Of churned predictions, how many were correct
    recall = Column(Float, nullable=True)  # Of actual churned, how many we caught
    f1_score = Column(Float, nullable=True)  # Harmonic mean of precision/recall
    
    # Sample size
    num_predictions = Column(Integer, nullable=False)  # Predictions evaluated
    num_actual_churned = Column(Integer, nullable=False)  # Actual churn cases
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", back_populates="model_evaluations")
    
    __table_args__ = (
        Index("idx_business_eval_date", "business_id", "evaluation_date"),
    )
    
    def __repr__(self):
        return f"<ModelEvaluation(business_id={self.business_id}, accuracy={self.accuracy:.2%})>"


class BusinessAction(Base):
    """Records actions taken based on predictions per location"""
    __tablename__ = "business_actions"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False)
    
    # This links a concrete business action back to the exact risk snapshot
    # that triggered it, which is essential for later ROI and learning loops.
    segment_when_actioned = Column(String(50), nullable=False)
    action_type = Column(String(100), nullable=False)
    action_description = Column(Text, nullable=True)
    
    # Timing
    action_date = Column(Date, nullable=False)
    reference_date = Column(Date, nullable=False)
    
    # Outcome fields turn raw recommendations into measurable retention work.
    # Once staff record return behavior and recovered revenue, the system can
    # later learn which actions and conditions produce better outcomes.
    status = Column(String(50), default="pending")
    outcome_recorded = Column(Boolean, default=False)
    customer_returned = Column(Boolean, nullable=True)
    days_to_return = Column(Integer, nullable=True)
    revenue_recovered = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", back_populates="business_actions")
    location = relationship("Location", back_populates="business_actions")
    customer = relationship("Customer")
    prediction = relationship("Prediction")
    
    __table_args__ = (
        Index("idx_location_action_date", "location_id", "action_date"),
        Index("idx_location_status", "location_id", "status"),
    )
    
    def __repr__(self):
        return f"<BusinessAction(loc={self.location_id}, action_type={self.action_type})>"
    

class MonthlyMetrics(Base):
    """Aggregated ROI and business metrics per month"""
    __tablename__ = "monthly_metrics"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    
    # This table is the roll-up layer above daily snapshots and interventions.
    # It is designed for executive review: monthly health, ROI, and action mix.
    month_year = Column(String(20), nullable=False)  # "2026-04" format
    reference_date_start = Column(Date, nullable=False)  # First snapshot in month
    reference_date_end = Column(Date, nullable=False)  # Last snapshot in month
    
    # Action metrics summarize what the business actually did during the month.
    total_actions_taken = Column(Integer, default=0)  # How many recommendations made
    actions_by_type = Column(String(500), nullable=True)  # JSON: {"discount": 45, "sms": 30, ...}
    
    # Outcome metrics summarize whether those actions changed behavior.
    customers_returned = Column(Integer, default=0)  # How many came back
    return_rate = Column(Float, nullable=True)  # % of actioned customers who returned
    
    # Revenue impact is the commercial proof the owner cares about most.
    total_revenue_recovered = Column(Float, default=0.0)  # Revenue from recovered customers
    average_recovery_value = Column(Float, nullable=True)  # Revenue per recovered customer
    total_cost_of_actions = Column(Float, default=0.0)  # Cost of discount/SMS/etc
    
    # ROI fields make the retention product accountable to business value,
    # not only to segment counts or technical scores.
    net_roi = Column(Float, nullable=True)  # (recovered - cost) / cost * 100
    roi_percent = Column(Float, nullable=True)  # Simple percentage
    
    # Segment counts capture the month-end customer health distribution.
    churned_count = Column(Integer, default=0)  # Customers in CHURNED at end of month
    at_risk_count = Column(Integer, default=0)  # Customers in AT_RISK at end
    active_count = Column(Integer, default=0)  # Customers in ACTIVE at end
    loyal_count = Column(Integer, default=0)  # Customers in LOYAL at end
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", back_populates="monthly_metrics")
    
    __table_args__ = (
        Index("idx_business_month", "business_id", "month_year"),
    )
    
    def __repr__(self):
        return f"<MonthlyMetrics(business_id={self.business_id}, month={self.month_year}, roi={self.roi_percent:.1f}%)>"
