"""
Dashboard & CSV Schemas
=======================

Schemas for dashboards, CSV uploads, and recommendations
"""

from datetime import date
from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.common import SegmentEnum


class SegmentSummary(BaseModel):
    """Summary of customers in a segment"""
    # This schema is intentionally compact because it feeds the dashboard cards
    # and charts that answer "how many customers are in each health bucket?"
    segment: SegmentEnum
    count: int
    total_at_risk_value: float
    avg_monetary: float


class DashboardMetrics(BaseModel):
    """Main dashboard metrics"""
    # These are the top-level business numbers shown for the latest snapshot
    # scope. They combine snapshot health with revenue context.
    current_reference_date: date
    scoring_window_start: date
    scoring_window_end: date
    first_transaction_date: Optional[date] = None
    last_transaction_date: Optional[date] = None
    total_customers: int
    total_revenue: float
    revenue_at_risk: float  # Revenue from at_risk + churned
    avg_customer_value: float
    segment_summary: List[SegmentSummary]
    top_products: List[dict]  # [{product_name, total_quantity_sold, total_revenue, times_purchased}]


class CSVUploadResponse(BaseModel):
    """Response after CSV upload and churn snapshot scoring"""
    # This response tells the frontend what operational work completed, not
    # just whether the file was accepted.
    message: str
    status: str
    reference_date: date
    upload_start_date: date
    upload_end_date: date
    scoring_window_start: date
    scoring_window_end: date
    total_transactions_uploaded: int
    total_customers: int
    recommendations_count: int
    scoring_engine: str
    scoring_version: Optional[str] = None


class CustomerRecommendation(BaseModel):
    """Action recommendation for a specific customer"""
    # This is the actionable unit a manager or owner will actually work with:
    # one customer, one risk state, one suggested next move.
    customer_id: str
    segment: SegmentEnum
    churn_probability: float
    recommended_action: str
    urgency: str  # "immediate", "high", "medium", "low"
    reasoning: str


class RecommendationsResponse(BaseModel):
    """Batch recommendations for a business"""
    # This wrapper adds light summary counts so the UI can show urgency before
    # rendering the individual recommendation list.
    churned_count: int
    at_risk_count: int
    recommendations: List[CustomerRecommendation]


class SegmentCustomerSummary(BaseModel):
    """Customer row inside a segment drilldown view"""
    # This powers the transition from a dashboard card to an actionable
    # customer worklist without recalculating any live scores.
    customer_id: str
    customer_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    location_id: int
    location_name: str
    location_code: str
    reference_date: date
    segment: SegmentEnum
    churn_probability: float
    recency: int
    frequency: int
    monetary: float
    total_spent: float
    total_purchases: int
    last_purchase_date: Optional[date] = None
    recommended_action: str
    urgency: str
    reasoning: str


class SegmentCustomersResponse(BaseModel):
    """Current snapshot customers for one segment and scope"""
    segment: SegmentEnum
    current_reference_date: date
    total_customers: int
    customers: List[SegmentCustomerSummary]

class DashboardLocationOption(BaseModel):
    # Used to populate the location filter on the dashboard.
    id:int
    location_code:str
    name:str

class DashboardLocationsResponse(BaseModel):
    locations:List[DashboardLocationOption]


class SegmentComparisonDelta(BaseModel):
    """How a segment changed between two snapshots"""
    # The delta is the business-facing answer to "did this segment grow or shrink?"
    segment: SegmentEnum
    current_count: int
    previous_count: int
    delta: int


class SnapshotComparisonResponse(BaseModel):
    """Month-over-month or quarter-over-quarter comparison for one scope"""
    # This schema supports trend storytelling for owners: customer movement,
    # revenue-at-risk movement, and which segments improved or worsened.
    period: str
    snapshot_offset: int
    current_reference_date: date
    previous_reference_date: date
    current_total_customers: int
    previous_total_customers: int
    total_customers_delta: int
    current_window_revenue: float
    previous_window_revenue: float
    window_revenue_delta: float
    current_revenue_at_risk: float
    previous_revenue_at_risk: float
    revenue_at_risk_delta: float
    improved_customers: int
    worsened_customers: int
    unchanged_customers: int
    recovered_customers: int
    slipped_customers: int
    segment_changes: List[SegmentComparisonDelta]


class VipCustomerSummary(BaseModel):
    """Top-value customer shown in VIP concentration analysis"""
    customer_id: str
    customer_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    segment: SegmentEnum
    location_name: str
    location_code: str
    churn_probability: float
    monetary: float
    total_spent: float
    total_purchases: int


class VipConcentrationResponse(BaseModel):
    """Revenue concentration view for the current snapshot"""
    current_reference_date: date
    total_customers: int
    vip_customer_count: int
    vip_share_threshold: float
    vip_revenue: float
    total_revenue: float
    vip_revenue_share: float
    non_vip_revenue: float
    top_customers: List[VipCustomerSummary]


class BusinessActionCreateRequest(BaseModel):
    """Record that the business acted on a recommendation"""
    # This request turns an on-screen recommendation into a tracked intervention.
    prediction_id: int
    action_type: str = Field(min_length=2, max_length=100)
    action_description: Optional[str] = Field(default=None, max_length=1000)
    action_date: Optional[date] = None


class BusinessActionOutcomeUpdateRequest(BaseModel):
    """Record the business outcome after an intervention"""
    # The follow-up outcome is what later enables ROI tracking and supervised labels.
    status: str = Field(min_length=2, max_length=50)
    outcome_recorded: bool = False
    customer_returned: Optional[bool] = None
    days_to_return: Optional[int] = Field(default=None, ge=0)
    revenue_recovered: Optional[float] = Field(default=None, ge=0)


class BusinessActionResponse(BaseModel):
    """Tracked action shown back on the dashboard"""
    # This is the persisted intervention record that managers review later.
    id: int
    prediction_id: int
    customer_id: str
    customer_name: Optional[str]
    location_id: int
    segment_when_actioned: SegmentEnum
    action_type: str
    action_description: Optional[str]
    action_date: date
    reference_date: date
    status: str
    outcome_recorded: bool
    customer_returned: Optional[bool]
    days_to_return: Optional[int]
    revenue_recovered: Optional[float]


class InterventionListResponse(BaseModel):
    """Tracked actions plus basic recovery summary"""
    # The summary fields give a quick operational picture before the UI renders
    # the detailed intervention table.
    total_actions: int
    completed_actions: int
    returned_customers: int
    total_revenue_recovered: float
    actions: List[BusinessActionResponse]


