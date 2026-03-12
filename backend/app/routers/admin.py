from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Business, InviteToken, Location, User
from app.routers.auth import require_platform_admin
from app.schemas import (
    AdminBusinessesResponse,
    AdminBusinessSummary,
    AdminBusinessUpdateRequest,
    AdminReminderResponse,
)
import logging
from app.utils.mailer import send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _days_until(target_date: date | None) -> int | None:
    if target_date is None:
        return None

    return (target_date - date.today()).days


def _needs_payment_reminder(business: Business) -> bool:
    trial_days = _days_until(business.trial_ends_at)
    billing_days = _days_until(business.billing_due_date)

    if business.subscription_status == "past_due":
        return True

    if business.subscription_status == "trial" and trial_days is not None and trial_days <= 3:
        return True

    if billing_days is not None and billing_days <= 3:
        return True

    return False


def _serialize_business_summary(
    business: Business,
    total_locations: int,
    total_users: int,
) -> AdminBusinessSummary:
    return AdminBusinessSummary(
        id=business.id,
        name=business.name,
        email=business.email,
        phone=business.phone,
        country=business.country,
        currency=business.currency,
        is_active=business.is_active,
        subscription_status=business.subscription_status,
        trial_started_at=business.trial_started_at,
        trial_ends_at=business.trial_ends_at,
        billing_due_date=business.billing_due_date,
        last_payment_reminder_sent_at=business.last_payment_reminder_sent_at,
        monthly_price=business.monthly_price,
        created_at=business.created_at,
        updated_at=business.updated_at,
        total_locations=total_locations,
        total_users=total_users,
        days_until_trial_end=_days_until(business.trial_ends_at),
        days_until_billing_due=_days_until(business.billing_due_date),
        needs_payment_reminder=_needs_payment_reminder(business),
    )


def _get_business_or_404(session: Session, business_id: int) -> Business:
    business = session.query(Business).filter(Business.id == business_id).first()
    if business is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found.",
        )

    return business


@router.get("/businesses", response_model=AdminBusinessesResponse)
def list_businesses(
    session: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    rows = session.query(
        Business,
        func.count(distinct(Location.id)).label("total_locations"),
        func.count(distinct(User.id)).label("total_users"),
    ).outerjoin(
        Location,
        Location.business_id == Business.id,
    ).outerjoin(
        User,
        User.business_id == Business.id,
    ).group_by(
        Business.id,
    ).order_by(
        Business.created_at.desc(),
    ).all()

    return AdminBusinessesResponse(
        businesses=[
            _serialize_business_summary(business, total_locations, total_users)
            for business, total_locations, total_users in rows
        ]
    )


@router.patch("/businesses/{business_id}", response_model=AdminBusinessSummary)
def update_business(
    business_id: int,
    payload: AdminBusinessUpdateRequest,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    business = _get_business_or_404(session, business_id)
    updates = payload.dict(exclude_unset=True)

    for field_name, value in updates.items():
        setattr(business, field_name, value)

    if business.subscription_status == "trial" and business.trial_started_at is None:
        business.trial_started_at = business.created_at.date()

    session.add(business)
    session.commit()
    session.refresh(business)

    total_locations = session.query(func.count(Location.id)).filter(Location.business_id == business.id).scalar() or 0
    total_users = session.query(func.count(User.id)).filter(User.business_id == business.id).scalar() or 0
    return _serialize_business_summary(business, total_locations, total_users)


@router.post("/businesses/{business_id}/payment-reminder", response_model=AdminReminderResponse)
def send_payment_reminder(
    business_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    business = _get_business_or_404(session, business_id)

    if business.subscription_status == "trial" and business.trial_ends_at is not None:
        subject = f"Your trial ends on {business.trial_ends_at.isoformat()}"
        message = (
            f"Hello {business.name}, your 14-day trial ends on {business.trial_ends_at.isoformat()}. "
            "Please confirm whether you want to continue on a paid plan so service stays active."
        )
    elif business.billing_due_date is not None:
        subject = f"Payment due on {business.billing_due_date.isoformat()}"
        message = (
            f"Hello {business.name}, your next platform payment is due on {business.billing_due_date.isoformat()}. "
            "Please settle the invoice to avoid service interruption."
        )
    else:
        subject = "Platform account follow-up"
        message = (
            f"Hello {business.name}, this is a follow-up on your platform account status. "
            "Please reply so we can confirm your subscription and keep your business active."
        )

    sent_at = datetime.utcnow()
    business.last_payment_reminder_sent_at = sent_at
    session.add(business)
    session.commit()

    # Attempt to send email if SMTP is configured. Failures are logged but do not break the API.
    try:
        send_email(subject, message, business.email)
        logger.info(f"Payment reminder email sent to {business.email}")
    except Exception:
        logger.exception(f"Failed to send payment reminder to {business.email}")

    return AdminReminderResponse(
        business_id=business.id,
        recipient_email=business.email,
        subject=subject,
        message=message,
        sent_at=sent_at,
    )


@router.delete("/businesses/{business_id}")
def delete_business(
    business_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    business = _get_business_or_404(session, business_id)

    if current_user.business_id == business.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delete your own admin-linked business from another admin account.",
        )

    session.query(InviteToken).filter(InviteToken.business_id == business.id).delete(synchronize_session=False)
    session.query(User).filter(User.business_id == business.id).delete(synchronize_session=False)
    session.delete(business)
    session.commit()

    return {"message": "Business deleted successfully."}