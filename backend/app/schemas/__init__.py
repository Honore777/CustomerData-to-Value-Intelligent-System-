"""
Request/Response Schemas
=========================

All Pydantic schemas for request/response validation.
Each schema file maps to a feature area.

Import schemas from here for easy access.

Example:
    from app.schemas import SignupRequest, LoginRequest, UserResponse, TokenResponse
"""

from app.schemas.common import SegmentEnum
from app.schemas.business import BusinessBase, BusinessCreate, BusinessResponse
from app.schemas.customer import (CustomerBase, CustomerCreate, CustomerResponse,CustomerTransactionSummary, CustomerPredictionSummary, CustomerDetailResponse)
from app.schemas.transaction import TransactionBase, TransactionCreate, TransactionResponse
from app.schemas.prediction import PredictionBase, PredictionResponse

from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    UserResponse,
    TokenResponse,
    InviteManagerRequest,
    AcceptInviteRequest
)

from app.schemas.admin import (
    AdminBusinessesResponse,
    AdminBusinessSummary,
    AdminBusinessUpdateRequest,
    AdminReminderResponse,
)

from app.schemas.dashboard import(
    SegmentSummary,
    DashboardMetrics,
    CSVUploadResponse,
    CustomerRecommendation,
    RecommendationsResponse,
    SegmentCustomerSummary,
    SegmentCustomersResponse,
    DashboardLocationOption,
    DashboardLocationsResponse,
    SegmentComparisonDelta,
    SnapshotComparisonResponse,
    VipCustomerSummary,
    VipConcentrationResponse,
    BusinessActionCreateRequest,
    BusinessActionOutcomeUpdateRequest,
    BusinessActionResponse,
    InterventionListResponse,
)

__all__ = [
    # Common
    "SegmentEnum",
    # Business
    "BusinessBase",
    "BusinessCreate",
    "BusinessResponse",
    # Customer
    "CustomerBase",
    "CustomerCreate",
    "CustomerResponse",
    "CustomerTransactionSummary",
    "CustomerPredictionSummary",
    "CustomerDetailResponse",
    # Transaction
    "TransactionBase",
    "TransactionCreate",
    "TransactionResponse",
    # Prediction
    "PredictionBase",
    "PredictionResponse",
    # Dashboard
    "SegmentSummary",
    "DashboardMetrics",
    "CSVUploadResponse",
    "CustomerRecommendation",
    "RecommendationsResponse",
    "SegmentCustomerSummary",
    "SegmentCustomersResponse",
    "DashboardLocationOption",
    "DashboardLocationsResponse",
    "SegmentComparisonDelta",
    "SnapshotComparisonResponse",
    "VipCustomerSummary",
    "VipConcentrationResponse",
    "BusinessActionCreateRequest",
    "BusinessActionOutcomeUpdateRequest",
    "BusinessActionResponse",
    "InterventionListResponse",
    # Auth
    "SignupRequest",
    "LoginRequest",
    "UserResponse",
    "TokenResponse",
    "InviteManagerRequest",
    "AcceptInviteRequest",
    # Admin
    "AdminBusinessesResponse",
    "AdminBusinessSummary",
    "AdminBusinessUpdateRequest",
    "AdminReminderResponse",
]
