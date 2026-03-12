"""
Business Configuration Endpoints
Handles onboarding, settings, column mapping, etc.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile
from sqlalchemy import text, func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Optional, Literal, List, Any
from datetime import datetime, date, timedelta
import logging
import re
from io import BytesIO

import pandas as pd

from app.database import get_db
from app.models import Business, Location, Customer, Prediction, Transaction, InviteToken, User
from app.routers.auth import get_current_user
from app.schemas import CSVUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/businesses", tags=["businesses"])


DEFAULT_LOCATION_CODE = "main"
DEFAULT_LOCATION_NAME = "Main Business"
DEFAULT_COLUMN_MAPPING = {
    # The defaults describe the simplest onboarding case: one business,
    # one location, and a stable customer_id column. Older businesses may
    # have partial mappings saved, so these defaults also act as a safety net.
    "uses_locations": False,
    "identity_strategy": "customer_id",
    "agreed_identifier_label": "Customer ID",
    "customer_id_column": "customer_id",
    "customer_name_column": None,
    "phone_column": None,
    "email_column": None,
    "location_code_column": None,
    "date_column": "purchase_date",
    "amount_column": "amount",
    "product_column": "product_name",
}


def _normalize_identity_part(value: Optional[object]) -> Optional[str]:
    # Customer names and phone numbers often arrive with inconsistent casing,
    # spacing, or accidental formatting differences. We normalize them before
    # building a composite key so repeat uploads map back to the same customer.
    if value is None:
        return None

    normalized = re.sub(r"\s+", " ", str(value).strip().lower())
    return normalized or None


def _get_effective_column_mapping(raw_mapping: Optional[Dict]) -> Dict:
    # Normalize old and new business configs into one internal shape.
    # This keeps older businesses working even after the product evolves.
    mapping = {**DEFAULT_COLUMN_MAPPING}

    if raw_mapping:
        mapping.update(raw_mapping)

    if raw_mapping is not None and "uses_locations" not in raw_mapping:
        mapping["uses_locations"] = bool(mapping.get("location_code_column"))

    if not mapping.get("uses_locations"):
        mapping["location_code_column"] = None

    return mapping


def _read_uploaded_dataframe(file: UploadFile) -> pd.DataFrame:
    # Read the uploaded file once and convert it into a pandas dataframe.
    # Both preview mode and full upload mode use this same parsing rule.
    file_content = BytesIO(file.file.read())
    file.file.seek(0)

    if file.filename.endswith('.csv'):
        return pd.read_csv(file_content)

    if file.filename.endswith(('.xlsx', '.xls')):
        return pd.read_excel(file_content)

    raise ValueError("File must be CSV or Excel (.xlsx, .xls)")


def _clean_optional_text(value: Optional[object]) -> Optional[str]:
    # Optional descriptive fields such as names and phone numbers should be
    # preserved when available, but empty strings should not create noisy data.
    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None


def _guess_first_matching_column(columns: List[str], candidates: List[str]) -> Optional[str]:
    # Matching is case-insensitive because businesses rarely use identical labels.
    normalized_columns = {column.strip().lower(): column for column in columns}

    for candidate in candidates:
        if candidate in normalized_columns:
            return normalized_columns[candidate]

    return None


def _build_mapping_preview(columns: List[str]) -> Dict[str, Any]:
    # This is the product heart of guided onboarding:
    # inspect the file headers first, then propose a mapping the owner can confirm.
    location_column = _guess_first_matching_column(
        columns,
        [
            'location_code', 'branch_code', 'branch', 'branch name', 'outlet',
            'outlet_code', 'store', 'store_code', 'shop', 'shop_code'
        ],
    )
    customer_id_column = _guess_first_matching_column(
        columns,
        ['customer_id', 'customer number', 'client_id', 'client number', 'member_id', 'phone'],
    )
    customer_name_column = _guess_first_matching_column(
        columns,
        ['customer_name', 'customer name', 'client_name', 'client name', 'name', 'full name'],
    )
    phone_column = _guess_first_matching_column(
        columns,
        ['phone', 'phone_number', 'phone number', 'telephone', 'mobile'],
    )
    email_column = _guess_first_matching_column(
        columns,
        ['email', 'email_address', 'email address', 'customer_email', 'client_email'],
    )

    if customer_id_column:
        # Stable explicit IDs are best because they survive name spelling changes
        # and phone number updates better than derived identifiers.
        identity_strategy = 'customer_id'
    elif customer_name_column and phone_column:
        # Name + phone is the most practical fallback for many African SMEs that
        # know customers personally but do not issue formal loyalty IDs.
        identity_strategy = 'customer_name_phone'
    elif customer_name_column:
        identity_strategy = 'customer_name'
    else:
        identity_strategy = 'customer_id'

    suggested_mapping = {
        'uses_locations': location_column is not None,
        'identity_strategy': identity_strategy,
        'agreed_identifier_label': 'Customer ID' if identity_strategy == 'customer_id' else 'Customer Identity',
        'customer_id_column': customer_id_column,
        'customer_name_column': customer_name_column,
        'phone_column': phone_column,
        'email_column': email_column,
        'location_code_column': location_column,
        'date_column': _guess_first_matching_column(
            columns,
            ['purchase_date', 'date', 'transaction_date', 'sale_date', 'invoice_date'],
        ),
        'amount_column': _guess_first_matching_column(
            columns,
            ['amount', 'total', 'total_paid', 'total paid', 'value', 'sales_amount'],
        ),
        'product_column': _guess_first_matching_column(
            columns,
            ['product_name', 'product', 'item_name', 'item', 'service_name'],
        ),
    }

    required_fields = ['date_column', 'amount_column', 'product_column']
    if identity_strategy == 'customer_id':
        required_fields.append('customer_id_column')
    else:
        required_fields.append('customer_name_column')
        if identity_strategy == 'customer_name_phone':
            required_fields.append('phone_column')

    if suggested_mapping['uses_locations']:
        required_fields.append('location_code_column')

    missing_fields = [field for field in required_fields if not suggested_mapping.get(field)]

    return {
        'suggested_mapping': suggested_mapping,
        'missing_fields': missing_fields,
    }


def _serialize_preview_rows(df: pd.DataFrame, limit: int = 5) -> List[Dict[str, Any]]:
    # Show the owner a few sample rows so they can visually confirm the mapping.
    preview_df = df.head(limit).where(pd.notnull(df.head(limit)), None)
    return preview_df.to_dict(orient='records')


def _get_business_data_summary(session: Session, business_id: int) -> Dict[str, Any]:
    # This summary gives the frontend a truthful picture of what the system
    # currently knows: date coverage, latest snapshot, and active location count.
    first_transaction_date, last_transaction_date = session.query(
        func.min(Transaction.purchase_date),
        func.max(Transaction.purchase_date),
    ).filter(Transaction.business_id == business_id).first()

    latest_snapshot_date = session.query(func.max(Prediction.reference_date)).filter(
        Prediction.business_id == business_id
    ).scalar()

    active_locations_count = session.query(func.count(Location.id)).filter(
        Location.business_id == business_id,
        Location.is_active == True,
    ).scalar() or 0

    total_customers = session.query(func.count(Customer.id)).filter(
        Customer.business_id == business_id,
    ).scalar() or 0

    total_transactions = session.query(func.count(Transaction.id)).filter(
        Transaction.business_id == business_id,
    ).scalar() or 0

    return {
        'first_transaction_date': first_transaction_date.date() if first_transaction_date else None,
        'last_transaction_date': last_transaction_date.date() if last_transaction_date else None,
        'latest_snapshot_date': latest_snapshot_date,
        'active_locations_count': int(active_locations_count),
        'total_customers': int(total_customers),
        'total_transactions': int(total_transactions),
    }


def _refresh_business_snapshots(session: Session, business: Business) -> Dict[str, Any]:
    # Threshold changes should not remain hidden configuration only. We use the
    # stored transactions to rebuild the business snapshots so the dashboard and
    # recommendation views immediately reflect the new scoring policy.
    from app.ml.ml_pipeline import full_pipeline

    active_locations = session.query(Location).filter(
        Location.business_id == business.id,
        Location.is_active == True,
    ).all()

    existing_reference_dates = [
        row[0]
        for row in session.query(Prediction.reference_date)
        .filter(Prediction.business_id == business.id)
        .distinct()
        .order_by(Prediction.reference_date.asc())
        .all()
    ]

    if not active_locations:
        return {
            'refreshed_snapshots': 0,
            'refresh_reference_dates': [],
        }

    if not existing_reference_dates:
        return {
            'refreshed_snapshots': 0,
            'refresh_reference_dates': [],
        }

    refreshed_snapshots = 0
    refresh_reference_dates: List[str] = []

    for reference_date in existing_reference_dates:
        refreshed_for_date = False

        for location in active_locations:
            pipeline_result = full_pipeline(
                business_id=business.id,
                location_id=location.id,
                reference_date=reference_date,
                session=session,
            )

            if 'error' in pipeline_result:
                logger.info(
                    'Skipping snapshot refresh for business %s, location %s, reference_date %s: %s',
                    business.id,
                    location.id,
                    reference_date,
                    pipeline_result['error'],
                )
                continue

            refreshed_snapshots += 1
            refreshed_for_date = True

        if refreshed_for_date:
            refresh_reference_dates.append(str(reference_date))
            session.commit()

    return {
        'refreshed_snapshots': refreshed_snapshots,
        'refresh_reference_dates': refresh_reference_dates,
    }


def _remove_duplicate_transactions_for_range(
    session: Session,
    business_id: int,
    start_date: datetime,
    end_date: datetime,
) -> int:
    # Repeat uploads are common in real operations: owners fix a column, retry,
    # or re-upload the same export after a failure. This cleanup keeps one copy
    # of each exact transaction signature so scores do not get inflated by
    # accidental duplicate imports.
    result = session.execute(
        text(
            """
            WITH ranked_transactions AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY business_id, location_id, customer_id, product_name, amount, quantity, purchase_date
                        ORDER BY id
                    ) AS row_num
                FROM transactions
                WHERE business_id = :business_id
                  AND purchase_date >= :start_date
                  AND purchase_date <= :end_date
            )
            DELETE FROM transactions t
            USING ranked_transactions ranked
            WHERE t.id = ranked.id
              AND ranked.row_num > 1
            RETURNING t.id
            """
        ),
        {
            "business_id": business_id,
            "start_date": start_date,
            "end_date": end_date,
        },
    )
    deleted_rows = result.fetchall()
    return len(deleted_rows)


# ===== PYDANTIC SCHEMAS =====

class ColumnMappingSchema(BaseModel):
    """Schema for column mapping configuration"""
    uses_locations: bool = False
    identity_strategy: Literal["customer_id", "customer_name", "customer_name_phone"] = "customer_id"
    agreed_identifier_label: Optional[str] = "Customer ID"
    customer_id_column: Optional[str] = None
    customer_name_column: Optional[str] = None
    phone_column: Optional[str] = None
    email_column: Optional[str] = None
    location_code_column: Optional[str] = None
    date_column: str
    amount_column: str
    product_column: str
    date_format: str = '%Y-%m-%d'
    
    class Config:
        json_schema_extra = {
            "example": {
                "uses_locations": True,
                "identity_strategy": "customer_id",
                "customer_id_column": "customer_id",
                "customer_name_column": None,
                "phone_column": None,
                "email_column": None,
                "location_code_column": "location_code",
                "date_column": "purchase_date",
                "amount_column": "amount",
                "product_column": "product_name",
                "date_format": "%Y-%m-%d"
            }
        }


class ConfigureColumnsRequest(BaseModel):
    """Request to configure column mapping"""
    mapping: ColumnMappingSchema


class MappingPreviewResponse(BaseModel):
    """Preview the uploaded file headers before saving mapping or scoring."""
    file_name: str
    columns: List[str]
    sample_rows: List[Dict[str, Any]]
    suggested_mapping: Dict[str, Any]
    missing_fields: List[str]


class BusinessResponseSchema(BaseModel):
    """Response with business info"""
    id: int
    name: str
    email: str
    country: str
    reference_period_days: int
    recency_threshold_days: int
    frequency_threshold: int
    monetary_threshold: float
    date_format: str
    column_mapping: Dict
    first_transaction_date: Optional[date] = None
    last_transaction_date: Optional[date] = None
    latest_snapshot_date: Optional[date] = None
    active_locations_count: int = 0
    total_customers: int = 0
    total_transactions: int = 0
    
    class Config:
        from_attributes = True


class LocationInviteInfo(BaseModel):
    id: int
    location_code: str
    name: str
    city: Optional[str] = None
    phone: Optional[str] = None


class PendingInvite(BaseModel):
    id: int
    email: str
    location_id: int
    expires_at: Optional[datetime] = None
    is_used: bool


class LocationsWithInvitesResponse(BaseModel):
    locations: List[LocationInviteInfo]
    pending_invites: List[PendingInvite]

    class Config:
        from_attributes = True


# ===== ENDPOINTS =====

@router.post("/{business_id}/preview-columns", response_model=MappingPreviewResponse)
async def preview_uploaded_columns(
    business_id: int,
    file: UploadFile,
    session: Session = Depends(get_db),
):
    """
    Inspect an uploaded file *before* full processing.

    This supports guided onboarding:
    1. Upload a sample file
    2. Show detected columns
    3. Suggest the mapping
    4. Let the owner confirm or correct it
    5. Save mapping, then run the full upload
    """

    business = session.query(Business).filter_by(id=business_id).first()

    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business {business_id} not found",
        )

    try:
        df = _read_uploaded_dataframe(file)

        if len(df) == 0:
            raise ValueError("File is empty")

        columns = [str(column) for column in df.columns]
        preview = _build_mapping_preview(columns)

        return MappingPreviewResponse(
            file_name=file.filename,
            columns=columns,
            sample_rows=_serialize_preview_rows(df),
            suggested_mapping=preview['suggested_mapping'],
            missing_fields=preview['missing_fields'],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

@router.post("/{business_id}/configure-columns", response_model=BusinessResponseSchema)
def configure_column_mapping(
    business_id: int,
    request: ConfigureColumnsRequest,
    session: Session = Depends(get_db)
):
    """
    Configure how THIS business records their data.
    
    Called ONCE during onboarding:
    - Business tells us which field identifies the customer
    - Business tells us: "I call customer ID 'Phone'"
    - Or: "I only have customer names"
    - Business tells us: "I call date 'Trans_Date'"
    - Business tells us: "I call amount 'Total Paid'"
    - Business tells us: "I call branch 'Outlet Code'"
    - Business tells us: "I format dates as DD/MM/YYYY"
    
    Then we remember forever and use this mapping for all future uploads.
    
    Example request:
    {
        "mapping": {
            "identity_strategy": "customer_name_phone",
            "customer_id_column": null,
            "customer_name_column": "Customer Name",
            "phone_column": "Phone Number",
            "location_code_column": "Branch Code",
            "date_column": "Date of Refill",
            "amount_column": "Total Paid",
            "product_column": "Drug Name",
            "date_format": "%d/%m/%Y"
        }
    }
    
    Args:
        business_id: Which business
        request: Their column mapping
        session: Database session
    
    Returns:
        Updated business info
    """
    
    # Find business
    business = session.query(Business).filter_by(id=business_id).first()
    
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business {business_id} not found"
        )

    if request.mapping.identity_strategy == "customer_id" and not request.mapping.customer_id_column:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="customer_id_column is required when identity_strategy is 'customer_id'"
        )

    if request.mapping.identity_strategy in {"customer_name", "customer_name_phone"} and not request.mapping.customer_name_column:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="customer_name_column is required when using a name-based identity strategy"
        )

    if request.mapping.identity_strategy == "customer_name_phone" and not request.mapping.phone_column:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="phone_column is required when identity_strategy is 'customer_name_phone'"
        )

    if request.mapping.uses_locations and not request.mapping.location_code_column:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="location_code_column is required when uses_locations is true"
        )
    
    try:
        # Save the business-specific vocabulary exactly once so future uploads
        # can be standardized automatically. This is what makes the product
        # practical for messy exports from POS systems and spreadsheets.
        business.column_mapping = {
            'uses_locations': request.mapping.uses_locations,
            'identity_strategy': request.mapping.identity_strategy,
            'agreed_identifier_label': request.mapping.agreed_identifier_label or 'Customer ID',
            'customer_id_column': request.mapping.customer_id_column,
            'customer_name_column': request.mapping.customer_name_column,
            'phone_column': request.mapping.phone_column,
            'email_column': request.mapping.email_column,
            'location_code_column': request.mapping.location_code_column if request.mapping.uses_locations else None,
            'date_column': request.mapping.date_column,
            'amount_column': request.mapping.amount_column,
            'product_column': request.mapping.product_column
        }
        
        # The date format is stored separately because the same column name can
        # still use different local conventions such as YYYY-MM-DD or DD/MM/YYYY.
        business.date_format = request.mapping.date_format
        
        # Save to database
        session.commit()
        
        logger.info(f"✅ Column mapping configured for business {business_id}")
        logger.info(f"   Mapping: {business.column_mapping}")
        logger.info(f"   Date format: {business.date_format}")

        coverage = _get_business_data_summary(session, business_id)
        for field, value in coverage.items():
            setattr(business, field, value)
        
        return business
    
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to configure columns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure columns: {str(e)}"
        )


@router.get("/{business_id}", response_model=BusinessResponseSchema)
def get_business(
    business_id: int,
    session: Session = Depends(get_db)
):
    """
    Get business details including current column mapping.
    
    Use this to CHECK what mapping they have configured.
    """
    
    business = session.query(Business).filter_by(id=business_id).first()
    
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business {business_id} not found"
        )

    business.column_mapping = _get_effective_column_mapping(business.column_mapping)

    coverage = _get_business_data_summary(session, business_id)
    for field, value in coverage.items():
        setattr(business, field, value)
    
    return business


@router.get("/{business_id}/locations-invites", response_model=LocationsWithInvitesResponse)
def get_locations_and_invites(
    business_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """
    Return all locations for a business and pending invites.

    Owner or platform admin only. The endpoint does NOT expose invite tokens,
    only metadata (email, expiry, used flag) so the owner can re-send or
    copy links from the UI.
    """
    # Only owners of this business or platform admins can view
    if not current_user.is_platform_admin and current_user.business_id != business_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    business = session.query(Business).filter_by(id=business_id).first()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    locations = session.query(Location).filter_by(business_id=business_id).all()
    invites = session.query(InviteToken).filter_by(business_id=business_id).all()

    loc_list = [LocationInviteInfo(
        id=loc.id,
        location_code=loc.location_code,
        name=loc.name,
        city=loc.city,
        phone=loc.phone
    ) for loc in locations]

    invite_list = [PendingInvite(
        id=inv.id,
        email=inv.email,
        location_id=inv.location_id,
        expires_at=inv.expires_at,
        is_used=inv.is_used
    ) for inv in invites]

    return LocationsWithInvitesResponse(locations=loc_list, pending_invites=invite_list)


@router.put("/{business_id}/update-config", response_model=BusinessResponseSchema)
def update_business_config(
    business_id: int,
    reference_period_days: Optional[int] = None,
    recency_threshold_days: Optional[int] = None,
    frequency_threshold: Optional[int] = None,
    monetary_threshold: Optional[float] = None,
    session: Session = Depends(get_db)
):
    """
    Update RFM thresholds or reference period.
    
    Business can change these settings anytime.
    They take effect on NEXT upload.
    
    Example: Business wants shorter review cycle
    - Change reference_period_days from 60 to 30
    - Next upload uses 30-day window
    """
    
    business = session.query(Business).filter_by(id=business_id).first()
    
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business {business_id} not found"
        )
    
    try:
        # Only update provided fields so owners can tune one threshold without
        # accidentally resetting the rest of their retention policy.
        if reference_period_days is not None:
            business.reference_period_days = reference_period_days
            logger.info(f"Updated reference_period_days to {reference_period_days}")
        
        if recency_threshold_days is not None:
            business.recency_threshold_days = recency_threshold_days
            logger.info(f"Updated recency_threshold_days to {recency_threshold_days}")
        
        if frequency_threshold is not None:
            business.frequency_threshold = frequency_threshold
            logger.info(f"Updated frequency_threshold to {frequency_threshold}")
        
        if monetary_threshold is not None:
            business.monetary_threshold = monetary_threshold
            logger.info(f"Updated monetary_threshold to {monetary_threshold}")

        session.commit()

        refresh_summary = _refresh_business_snapshots(session, business)
        logger.info(
            "Refreshed %s snapshots after config update for business %s",
            refresh_summary['refreshed_snapshots'],
            business_id,
        )
        
        logger.info(f"✅ Configuration updated for business {business_id}")

        business.column_mapping = _get_effective_column_mapping(business.column_mapping)
        coverage = _get_business_data_summary(session, business_id)
        for field, value in coverage.items():
            setattr(business, field, value)
        
        return business
    
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to update config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update config: {str(e)}"
        )
    


# ===== CSV UPLOAD =====

class UploadCSVRequest(BaseModel):
    """Request for CSV upload"""
    reference_date: Optional[str] = None  # "2024-05-01" (default = latest date in uploaded file)


@router.post("/{business_id}/upload-csv", response_model=CSVUploadResponse)
async def upload_csv(
    business_id: int,
    file: UploadFile,
    reference_date: Optional[str] = None,
    session: Session = Depends(get_db)
):
    """
    Upload CSV/Excel file and run the full retention scoring pipeline.
    
    This is the MAIN ENTRY POINT for production scoring.
    
    Steps:
    1. Load CSV/Excel file
    2. Use their saved column mapping to rename columns
    3. Parse dates using their saved format
    4. Validate data
    5. Store transactions in database
    6. Run the direct RFM scoring pipeline
    7. Store dated prediction snapshots
    8. Return results
    
    Args:
        business_id: Which business is uploading
        file: CSV or Excel file
        reference_date: When this snapshot was taken (e.g., "2024-05-01")
                   If not provided, defaults to the latest purchase_date in the uploaded file
        session: Database session
    
    Returns:
        {
            'reference_date': '2024-05-01',
            'business_id': 1,
            'total_customers': 523,
            'total_transactions': 1245,
            'segment_counts': {
                'churned': 45,
                'at_risk': 82,
                'active': 234,
                'loyal': 162
            },
            'model_metrics': {
                'engine': 'rule_based_rfm',
                'scoring_version': 'rfm_v1',
                'accuracy': null
            },
            'recommendations': [
                {
                    'customer_id': 'CUST001',
                    'segment': 'churned',
                    'churn_probability': 0.92,
                    'recommendation': {...}
                },
                ...
            ]
        }
    """
    
    from datetime import date as date_class
    from app.ml.ml_pipeline import full_pipeline
    
    try:
        # ===== STEP 1: Load file (CSV or Excel) =====
        logger.info(f"Loading file: {file.filename}")
        
        df = _read_uploaded_dataframe(file)
        logger.info(f"✅ Loaded file: {len(df)} rows")
        
        if len(df) == 0:
            raise ValueError("File is empty")
        
        # ===== STEP 2: Get business and their column mapping =====
        # Every upload is translated into the platform's internal language
        # before validation or scoring. That means downstream logic can always
        # rely on standard names like purchase_date, amount, and customer_id.
        business = session.query(Business).filter_by(id=business_id).first()
        
        if not business:
            raise ValueError(f"Business {business_id} not found")
        
        logger.info(f"Business: {business.name}")
        mapping = _get_effective_column_mapping(business.column_mapping)

        logger.info(f"Column mapping: {mapping}")
        logger.info(f"Date format: {business.date_format}")
        
        # ===== STEP 3: Rename columns using their mapping =====
        # First validate that the business-configured source columns really
        # exist in this file. This catches onboarding mistakes early and gives
        # the owner an understandable error before any database writes happen.
        required_cols = [
            mapping.get('date_column'),
            mapping.get('amount_column'),
            mapping.get('product_column'),
        ]

        if mapping.get('uses_locations'):
            required_cols.append(mapping.get('location_code_column'))

        if mapping.get('identity_strategy') == 'customer_id':
            required_cols.append(mapping.get('customer_id_column'))
        elif mapping.get('identity_strategy') in {'customer_name', 'customer_name_phone'}:
            required_cols.append(mapping.get('customer_name_column'))
            if mapping.get('identity_strategy') == 'customer_name_phone':
                required_cols.append(mapping.get('phone_column'))

        required_cols = [col for col in required_cols if col]
        
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not found in CSV. Available: {list(df.columns)}")

        if mapping.get('uses_locations') and not mapping.get('location_code_column'):
            raise ValueError("Business mapping says locations are enabled, but location_code_column is missing")
        
        # Rename source columns to the platform's internal schema. From this
        # point onward, every later step can work with a consistent dataframe
        # shape regardless of the original spreadsheet labels.
        df = df.rename(columns={
            mapping['date_column']: 'purchase_date',
            mapping['amount_column']: 'amount',
            mapping['product_column']: 'product_name',
        })

        if mapping.get('uses_locations'):
            df = df.rename(columns={
                mapping['location_code_column']: 'location_code'
            })
        else:
            df['location_code'] = DEFAULT_LOCATION_CODE

        if mapping.get('identity_strategy') == 'customer_id':
            df = df.rename(columns={
                mapping['customer_id_column']: 'customer_id'
            })
        elif mapping.get('identity_strategy') == 'customer_name':
            # Name-only identity is weaker than a true ID, but it is common in
            # owner-run businesses that know customers personally. We normalize
            # the name and use it as a repeatable internal grouping key.
            df['customer_name'] = df[mapping['customer_name_column']]
            df['customer_id'] = df['customer_name'].apply(_normalize_identity_part)
        elif mapping.get('identity_strategy') == 'customer_name_phone':
            # Name + phone gives a more stable identifier for markets where the
            # business may not issue loyalty IDs but often records phone numbers.
            df['customer_name'] = df[mapping['customer_name_column']]
            df['phone'] = df[mapping['phone_column']]
            df['customer_id'] = df.apply(
                lambda row: "|".join(
                    part
                    for part in [
                        _normalize_identity_part(row['customer_name']),
                        _normalize_identity_part(row['phone'])
                    ]
                    if part
                ) or None,
                axis=1
            )

        if mapping.get('email_column'):
            # Email is preserved as an optional outreach channel. It is not a
            # required identifier and should never block scoring when absent.
            df['email'] = df[mapping['email_column']]
        
        logger.info(f"✅ Renamed columns to standard format")
        
        # ===== STEP 4: Parse dates using their format =====
        # We parse using the business's saved format instead of guessing, which
        # avoids dangerous swaps like interpreting 03/04/2025 as either March 4
        # or April 3 depending on locale.
        try:
            df['purchase_date'] = pd.to_datetime(
                df['purchase_date'],
                format=business.date_format
            )
            logger.info(f"✅ Parsed dates using format: {business.date_format}")
        except Exception as e:
            raise ValueError(f"Failed to parse dates with format '{business.date_format}': {str(e)}")

        upload_min_date = df['purchase_date'].min().date()
        upload_max_date = df['purchase_date'].max().date()
        logger.info(f"Upload date range: {upload_min_date} -> {upload_max_date}")
        
        # ===== STEP 5: Validate data =====
        logger.info("Validating data...")
        
        # Null checks happen before scoring because a missing customer_id or
        # purchase_date would silently corrupt both aggregation and history.
        if df['customer_id'].isnull().any():
            raise ValueError("Found null values in customer_id column")
        if df['purchase_date'].isnull().any():
            raise ValueError("Found null values in purchase_date column")
        if df['amount'].isnull().any():
            raise ValueError("Found null values in amount column")
        
        # Monetary values must be numeric so revenue-at-risk and interventions
        # later remain financially trustworthy.
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        if df['amount'].isnull().any():
            raise ValueError("Some amount values are not numeric")
        
        # Negative amounts are rejected for now because the current product does
        # not yet model refunds/returns separately. Treating them as purchases
        # would distort customer value and segment logic.
        if (df['amount'] < 0).any():
            raise ValueError("Found negative amounts")
        
        logger.info(f"✅ Data validation passed")
        
        # ===== STEP 6: Determine reference_date =====
        # The reference date is the snapshot date. It answers the question:
        # "as of this day, what was the customer's status?" That same date is
        # what powers month-over-month and quarter-over-quarter comparisons.
        if reference_date:
            try:
                ref_date = pd.to_datetime(reference_date).date()
                logger.info(f"Using provided reference_date: {ref_date}")
            except:
                raise ValueError(f"Invalid reference_date format: {reference_date}. Use YYYY-MM-DD")
        else:
            # Historical uploads are common when onboarding African SMEs that
            # are backfilling old POS exports. Defaulting to today's date would
            # often create an empty scoring window, so we anchor the snapshot to
            # the latest date actually present in the uploaded file.
            ref_date = upload_max_date
            logger.info(f"Using latest upload date as reference_date: {ref_date}")
        
        # ===== STEP 7: Store transactions in database =====

        logger.info("Processing locations...")
        logger.info("Storing transactions...")
        
        # We upsert customers first so transactions can point to stable internal
        # customer records. The external file may repeat the same customer many
        # times, but the database should keep one customer row per identity key.
        unique_customers = df['customer_id'].unique()
        customers_dict = {}
        
        for cust_id in unique_customers:
            customer_rows = df[df['customer_id'] == cust_id]
            customer_name = None
            customer_phone = None
            customer_email = None
            if 'customer_name' in customer_rows.columns:
                first_name = customer_rows['customer_name'].dropna().astype(str)
                if not first_name.empty:
                    customer_name = first_name.iloc[0].strip() or None
            if 'phone' in customer_rows.columns:
                first_phone = customer_rows['phone'].dropna().astype(str)
                if not first_phone.empty:
                    customer_phone = _clean_optional_text(first_phone.iloc[0])
            if 'email' in customer_rows.columns:
                first_email = customer_rows['email'].dropna().astype(str)
                if not first_email.empty:
                    customer_email = _clean_optional_text(first_email.iloc[0])

            customer = session.query(Customer).filter_by(
                business_id=business_id,
                customer_id=str(cust_id)
            ).first()
            
            if not customer:
                customer = Customer(
                    business_id=business_id,
                    customer_id=str(cust_id),
                    name=customer_name,
                    phone=customer_phone,
                    email=customer_email,
                )
                session.add(customer)
            elif customer_name and not customer.name:
                customer.name = customer_name
            if customer_phone and not customer.phone:
                customer.phone = customer_phone
            if customer_email and not customer.email:
                customer.email = customer_email
            
            customers_dict[cust_id] = customer
            
        
        # Flush assigns database IDs without committing yet. That lets us create
        # related transactions in the same unit of work.
        session.flush()
        
        unique_locations = df['location_code'].unique()
        locations_dict = {}

        for loc in unique_locations:
            # Single-location businesses are normalized to the synthetic "main"
            # location so the rest of the system can use one location-aware path
            # for both simple and multi-branch businesses.
            location = session.query(Location).filter_by(
                business_id=business_id,
                location_code=str(loc)
            ).first()
            
            if not location:
                location_name = DEFAULT_LOCATION_NAME if str(loc) == DEFAULT_LOCATION_CODE else str(loc)
                location = Location(
                    business_id=business_id,
                    location_code=str(loc),
                    name=location_name
                )
                session.add(location)
            
            locations_dict[loc] = location

        session.flush()

        if not mapping.get('uses_locations'):
            # Older databases may still carry a legacy DEFAULT location from an
            # earlier schema version. Once the canonical synthetic main location
            # exists, hide the legacy one so single-location businesses do not
            # see two branches in the dashboard filter.
            legacy_default_location = session.query(Location).filter_by(
                business_id=business_id,
                location_code='DEFAULT'
            ).first()
            canonical_main_location = session.query(Location).filter_by(
                business_id=business_id,
                location_code=DEFAULT_LOCATION_CODE
            ).first()

            if (
                legacy_default_location
                and canonical_main_location
                and legacy_default_location.id != canonical_main_location.id
                and legacy_default_location.is_active
            ):
                legacy_default_location.is_active = False
                logger.info(
                    f"Deactivated legacy DEFAULT location for single-location business {business_id}"
                )
        
        logger.info(f"Found {len(locations_dict)} locations: {list(locations_dict.keys())}")
        
        # Store the raw transactional truth first. Snapshots and interventions
        # are built on top of these rows, so transactions remain the durable
        # source of customer behavior for later rescoring or ML preparation.
        for idx, row in df.iterrows():
            customer = customers_dict[row['customer_id']]
            location=locations_dict[row['location_code']]
            
            transaction = Transaction(
                business_id=business_id,
                customer_id=customer.id,
                location_id=location.id,
                product_name=str(row['product_name']),
                amount=float(row['amount']),
                quantity=1,
                purchase_date=row['purchase_date'],
                category=None  # Not in CSV
            )
            session.add(transaction)
        
        session.commit()

        duplicate_count = _remove_duplicate_transactions_for_range(
            session=session,
            business_id=business_id,
            start_date=df['purchase_date'].min().to_pydatetime(),
            end_date=df['purchase_date'].max().to_pydatetime(),
        )
        if duplicate_count:
            logger.warning(
                f"Removed {duplicate_count} duplicate transactions for business {business_id} in uploaded date range"
            )
        session.commit()
        
        logger.info("Running retention scoring pipeline for each location...")

        all_recommendations = []
        all_segment_counts = {}
        last_successful_pipeline = None

        # Each location gets its own snapshot because return cycles and customer
        # health can differ significantly across branches.
        for loc_code, location in locations_dict.items():
            logger.info(f"Processing location: {loc_code} ({location.name})")
            
            pipeline_result = full_pipeline(
                business_id=business_id,
                location_id=location.id,  # ← NEW: Process per location
                reference_date=ref_date,
                session=session
            )
            
            if 'error' in pipeline_result:
                logger.warning(f"Pipeline error for location {loc_code}: {pipeline_result['error']}")
                continue

            last_successful_pipeline = pipeline_result
            
            all_recommendations.extend(pipeline_result['recommendations'])
    
            # The response keeps segment counts grouped by location so the UI can
            # show both business-wide and branch-specific health at the same time.
            all_segment_counts[loc_code] = {
                'location_name': location.name,
                'segments': pipeline_result['segment_counts']
            }

        logger.info(f"✅ Pipeline complete for all {len(locations_dict)} locations!")

        if last_successful_pipeline is None:
            window_start = ref_date - pd.Timedelta(days=business.reference_period_days)
            raise ValueError(
                f"No transactions were found inside the scoring window [{window_start}, {ref_date}] "
                f"for uploaded data dated [{upload_min_date}, {upload_max_date}]. "
                f"Use a reference_date near the latest upload date or increase reference_period_days."
            )
        
        
        # ===== STEP 9: Store predictions in database =====
        # The scoring pipeline already persisted dated predictions and history.
        # We keep this step as a logging marker so the upload flow remains easy
        # to read from top to bottom.
        logger.info("Prediction snapshots already stored by scoring pipeline...")
        
        for pred_dict in pipeline_result.get('predictions', []):
            # Predictions already stored in full_pipeline()
            pass
        
        session.commit()
        
        # ===== STEP 10: Return results =====
        # The response is intentionally business-facing: counts, scope, scoring
        # engine, and top recommendations. It avoids pretending we trained a
        # validated supervised model during upload.
        scoring_window_start = ref_date - timedelta(days=business.reference_period_days)

        response = {
            'status': 'success',
            'message': f"Upload complete. Snapshot scored for {ref_date} using {business.reference_period_days}-day lookback window.",
            'reference_date': str(ref_date),
            'upload_start_date': str(upload_min_date),
            'upload_end_date': str(upload_max_date),
            'scoring_window_start': str(scoring_window_start),
            'scoring_window_end': str(ref_date),
            'business_id': business_id,
            'business_name': business.name,
            'file_name': file.filename,
            'total_transactions_uploaded': len(df),
            'total_customers': last_successful_pipeline['total_customers'],
            'upload_date_range': {
                'start_date': str(upload_min_date),
                'end_date': str(upload_max_date),
            },
            'scoring_window': {
                'start_date': str(ref_date - timedelta(days=business.reference_period_days)),
                'end_date': str(ref_date),
                'reference_period_days': business.reference_period_days,
            },
            'segment_counts': all_segment_counts,
            'model_metrics': last_successful_pipeline['model_metrics'],
            'recommendations_count': len(all_recommendations),
            'top_recommendations': all_recommendations[:10],
            'scoring_engine': last_successful_pipeline['model_metrics'].get('engine', 'rule_based_rfm'),
            'scoring_version': last_successful_pipeline['model_metrics'].get('scoring_version'),
        }

        response.update(_get_business_data_summary(session, business_id))
        
        logger.info(f"✅ UPLOAD COMPLETE!")
        logger.info(f"   Segments: {response['segment_counts']}")
        logger.info(f"   Scoring engine: {response['model_metrics'].get('engine', 'unknown')}")
        
        return response
    
    except ValueError as e:
        logger.error(f"❌ Validation error: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )