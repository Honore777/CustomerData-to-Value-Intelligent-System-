from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Customer, Prediction, Transaction, User
from app.routers.auth import get_current_user
from app.schemas import (
    CustomerDetailResponse,
    CustomerPredictionSummary,
    CustomerTransactionSummary,
)

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/{customer_code}", response_model=CustomerDetailResponse)
def get_customer_detail(
    customer_code: str,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = session.query(Customer).filter(
        Customer.business_id == current_user.business_id,
        Customer.customer_id == customer_code,
    ).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )

    prediction_query = session.query(Prediction).filter(
        Prediction.business_id == current_user.business_id,
        Prediction.customer_id == customer.id,
    )

    if current_user.assigned_location_ids is not None:
        prediction_query = prediction_query.filter(
            Prediction.location_id.in_(current_user.assigned_location_ids)
        )

    current_prediction = prediction_query.order_by(desc(Prediction.reference_date)).first()

    transaction_query = session.query(Transaction).filter(
        Transaction.business_id == current_user.business_id,
        Transaction.customer_id == customer.id,
    )

    if current_user.assigned_location_ids is not None:
        transaction_query = transaction_query.filter(
            Transaction.location_id.in_(current_user.assigned_location_ids)
        )

    recent_transactions = transaction_query.order_by(
        desc(Transaction.purchase_date)
    ).limit(10).all()

    return CustomerDetailResponse(
        id=customer.id,
        customer_id=customer.customer_id,
        name=customer.name,
        phone=customer.phone,
        email=customer.email,
        business_id=customer.business_id,
        last_purchase_date=customer.last_purchase_date,
        total_spent=customer.total_spent,
        total_purchases=customer.total_purchases,
        current_prediction=CustomerPredictionSummary(
            reference_date=current_prediction.reference_date,
            segment=current_prediction.segment,
            churn_probability=current_prediction.churn_probability,
            recency=current_prediction.recency,
            frequency=current_prediction.frequency,
            monetary=current_prediction.monetary,
        ) if current_prediction else None,
        recent_transactions=[
            CustomerTransactionSummary(
                id=transaction.id,
                product_name=transaction.product_name,
                amount=transaction.amount,
                quantity=transaction.quantity,
                purchase_date=transaction.purchase_date,
                category=transaction.category,
            )
            for transaction in recent_transactions
        ],
    )