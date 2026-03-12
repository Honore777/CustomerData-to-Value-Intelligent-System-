from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.ml.churn_utils import generate_recommendations
from app.models import Business, BusinessAction, Customer, Location, Prediction, Transaction, User
from app.routers.auth import get_current_user
from app.schemas import (
	BusinessActionCreateRequest,
	BusinessActionOutcomeUpdateRequest,
	BusinessActionResponse,
	CustomerRecommendation,
	DashboardMetrics,
	DashboardLocationOption,
    DashboardLocationsResponse,
	InterventionListResponse,
	RecommendationsResponse,
	SegmentCustomerSummary,
	SegmentCustomersResponse,
	SegmentComparisonDelta,
	SegmentSummary,
	SnapshotComparisonResponse,
	VipConcentrationResponse,
	VipCustomerSummary,
)
from app.schemas.common import SegmentEnum

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

SEGMENT_RANK = {
	SegmentEnum.CHURNED.value: 0,
	SegmentEnum.AT_RISK.value: 1,
	SegmentEnum.ACTIVE.value: 2,
	SegmentEnum.LOYAL.value: 3,
}


def _get_accessible_location_ids(current_user: User, requested_location_id: Optional[int]) -> Optional[list[int]]:
	# This helper centralizes location access control so every dashboard endpoint
	# follows the same tenancy rule. Owners can usually see all their business
	# locations, while managers may be limited to a subset.
	assigned_location_ids = current_user.assigned_location_ids

	if requested_location_id is not None:
		if assigned_location_ids is not None and requested_location_id not in assigned_location_ids:
			raise HTTPException(
				status_code=status.HTTP_403_FORBIDDEN,
				detail="You do not have access to that location.",
			)
		return [requested_location_id]

	return assigned_location_ids


def _get_effective_business_config(
	business: Business,
	session: Session,
	location_id: Optional[int],
) -> dict:
	# Start from business defaults, then apply location overrides when present.
	# This matters because one branch may have a faster purchase cycle than
	# another branch, even within the same company.
	config = {
		"reference_period_days": business.reference_period_days,
		"recency_threshold": business.recency_threshold_days,
		"frequency_threshold": business.frequency_threshold,
		"monetary_threshold": business.monetary_threshold,
		"currency": business.currency,
	}

	if location_id is None:
		return config

	location = session.query(Location).filter_by(
		id=location_id,
		business_id=business.id,
	).first()

	if not location:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Location not found for this business.",
		)

	if location.reference_period_days is not None:
		config["reference_period_days"] = location.reference_period_days
	if location.recency_threshold_days is not None:
		config["recency_threshold"] = location.recency_threshold_days
	if location.frequency_threshold is not None:
		config["frequency_threshold"] = location.frequency_threshold
	if location.monetary_threshold is not None:
		config["monetary_threshold"] = location.monetary_threshold

	return config


def _get_latest_reference_date(
	session: Session,
	business_id: int,
	accessible_location_ids: Optional[list[int]],
):
	# Dashboards should always read from the newest stored snapshot available
	# for the user’s current scope. We read from stored predictions rather than
	# recalculating live so comparisons remain stable and auditable.
	query = session.query(func.max(Prediction.reference_date)).filter(
		Prediction.business_id == business_id,
	)

	if accessible_location_ids is not None:
		query = query.filter(Prediction.location_id.in_(accessible_location_ids))

	return query.scalar()


def _get_historical_reference_dates(
	session: Session,
	business_id: int,
	accessible_location_ids: Optional[list[int]],
) -> list[date]:
	query = session.query(Prediction.reference_date).filter(
		Prediction.business_id == business_id,
	)

	if accessible_location_ids is not None:
		query = query.filter(Prediction.location_id.in_(accessible_location_ids))

	rows = query.distinct().order_by(Prediction.reference_date.desc()).all()
	return [reference_date for reference_date, in rows]


def _get_nth_previous_reference_date(
	session: Session,
	business_id: int,
	accessible_location_ids: Optional[list[int]],
	snapshot_offset: int,
) -> Optional[date]:
	reference_dates = _get_historical_reference_dates(
		session,
		business_id,
		accessible_location_ids,
	)

	if len(reference_dates) <= snapshot_offset:
		return None

	return reference_dates[snapshot_offset]


def _get_previous_reference_date(
	session: Session,
	business_id: int,
	accessible_location_ids: Optional[list[int]],
	latest_reference_date: date,
	period: str,
	snapshot_offset: int,
):
	if period == "month":
		return _get_nth_previous_reference_date(
			session,
			business_id,
			accessible_location_ids,
			snapshot_offset,
		)

	# We prefer a snapshot at least one month or one quarter earlier.
	# If no exact earlier period exists, we gracefully fall back to the latest
	# earlier snapshot instead of failing hard. This is practical for SMEs that
	# may upload irregularly rather than on perfect monthly schedules.
	days_back = 90 * snapshot_offset
	target_date = latest_reference_date - timedelta(days=days_back)

	query = session.query(func.max(Prediction.reference_date)).filter(
		Prediction.business_id == business_id,
		Prediction.reference_date <= target_date,
	)

	if accessible_location_ids is not None:
		query = query.filter(Prediction.location_id.in_(accessible_location_ids))

	previous_reference_date = query.scalar()
	if previous_reference_date is not None:
		return previous_reference_date

	fallback_query = session.query(func.max(Prediction.reference_date)).filter(
		Prediction.business_id == business_id,
		Prediction.reference_date < latest_reference_date,
	)

	if accessible_location_ids is not None:
		fallback_query = fallback_query.filter(Prediction.location_id.in_(accessible_location_ids))

	fallback_reference_date = fallback_query.scalar()
	if fallback_reference_date is not None:
		return fallback_reference_date

	return _get_nth_previous_reference_date(
		session,
		business_id,
		accessible_location_ids,
		snapshot_offset,
	)


def _load_predictions_for_scope(
	session: Session,
	business_id: int,
	reference_date: date,
	accessible_location_ids: Optional[list[int]],
):
	# This loads one stored snapshot for either the whole business or the
	# currently selected location set. It is reused by comparison views so all
	# metrics come from the same persisted source of truth.
	query = session.query(Prediction).filter(
		Prediction.business_id == business_id,
		Prediction.reference_date == reference_date,
	)

	if accessible_location_ids is not None:
		query = query.filter(Prediction.location_id.in_(accessible_location_ids))

	return query.all()


def _calculate_revenue_at_risk(predictions: list[Prediction]) -> float:
	# Revenue at risk is intentionally estimated from customers already marked
	# as churned or at risk. This gives owners a business-facing number to
	# prioritize, not just a technical segment count.
	return float(
		sum(
			float(prediction.monetary or 0.0)
			for prediction in predictions
			if prediction.segment in {SegmentEnum.CHURNED.value, SegmentEnum.AT_RISK.value}
		)
	)


def _calculate_window_revenue(
	session: Session,
	business_id: int,
	reference_date: date,
	reference_period_days: int,
	accessible_location_ids: Optional[list[int]],
) -> float:
	window_start = datetime.combine(reference_date, datetime.min.time()) - timedelta(
		days=reference_period_days
	)
	window_end = datetime.combine(reference_date, datetime.max.time())

	query = session.query(func.coalesce(func.sum(Transaction.amount), 0.0)).filter(
		Transaction.business_id == business_id,
		Transaction.purchase_date >= window_start,
		Transaction.purchase_date <= window_end,
	)

	if accessible_location_ids is not None:
		query = query.filter(Transaction.location_id.in_(accessible_location_ids))

	return float(query.scalar() or 0.0)


def _serialize_action(action: BusinessAction, customer: Customer) -> BusinessActionResponse:
	# The frontend needs human-usable intervention data in one object: who was
	# contacted, which snapshot triggered the action, what happened afterward,
	# and whether any money was recovered.
	return BusinessActionResponse(
		id=action.id,
		prediction_id=action.prediction_id,
		customer_id=customer.customer_id,
		customer_name=customer.name,
		location_id=action.location_id,
		segment_when_actioned=SegmentEnum(action.segment_when_actioned),
		action_type=action.action_type,
		action_description=action.action_description,
		action_date=action.action_date,
		reference_date=action.reference_date,
		status=action.status,
		outcome_recorded=action.outcome_recorded,
		customer_returned=action.customer_returned,
		days_to_return=action.days_to_return,
		revenue_recovered=float(action.revenue_recovered) if action.revenue_recovered is not None else None,
	)


@router.get("/metrics", response_model=DashboardMetrics)
def get_dashboard_metrics(
	location_id: Optional[int] = Query(default=None),
	session: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	accessible_location_ids = _get_accessible_location_ids(current_user, location_id)
	business = session.query(Business).filter_by(id=current_user.business_id).first()

	if not business:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Business not found.",
		)

	latest_reference_date = _get_latest_reference_date(
		session,
		business.id,
		accessible_location_ids,
	)

	if latest_reference_date is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="No prediction snapshot found yet. Upload data first.",
		)

	config = _get_effective_business_config(business, session, location_id)
	# Metrics use the scoring window anchored to the latest snapshot date.
	# That keeps revenue and top-product figures aligned with the same period
	# that produced the risk segments the user is looking at.
	window_start = datetime.combine(latest_reference_date, datetime.min.time()) - timedelta(
		days=config["reference_period_days"]
	)
	window_end = datetime.combine(latest_reference_date, datetime.max.time())

	prediction_query = session.query(Prediction).filter(
		Prediction.business_id == business.id,
		Prediction.reference_date == latest_reference_date,
	)

	if accessible_location_ids is not None:
		prediction_query = prediction_query.filter(Prediction.location_id.in_(accessible_location_ids))

	predictions = prediction_query.all()
	if not predictions:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="No predictions found for the selected scope.",
		)

	transaction_query = session.query(Transaction).filter(
		Transaction.business_id == business.id,
		Transaction.purchase_date >= window_start,
		Transaction.purchase_date <= window_end,
	)
	if accessible_location_ids is not None:
		transaction_query = transaction_query.filter(Transaction.location_id.in_(accessible_location_ids))

	available_data_start, available_data_end = session.query(
		func.min(Transaction.purchase_date),
		func.max(Transaction.purchase_date),
	).filter(
		Transaction.business_id == business.id,
	).filter(
		Transaction.location_id.in_(accessible_location_ids)
		if accessible_location_ids is not None
		else True
	).first()

	total_revenue = transaction_query.with_entities(func.coalesce(func.sum(Transaction.amount), 0.0)).scalar() or 0.0

	top_products_query = session.query(
		Transaction.product_name,
		func.coalesce(func.sum(Transaction.quantity), 0).label("total_quantity_sold"),
		func.coalesce(func.sum(Transaction.amount), 0.0).label("total_revenue"),
		func.count(Transaction.id).label("times_purchased"),
	).filter(
		Transaction.business_id == business.id,
		Transaction.purchase_date >= window_start,
		Transaction.purchase_date <= window_end,
	)
	if accessible_location_ids is not None:
		top_products_query = top_products_query.filter(Transaction.location_id.in_(accessible_location_ids))

	top_products = [
		{
			"product_name": row.product_name,
			"total_quantity_sold": int(row.total_quantity_sold or 0),
			"total_revenue": float(row.total_revenue or 0.0),
			"times_purchased": int(row.times_purchased or 0),
		}
		for row in top_products_query.group_by(Transaction.product_name).order_by(func.sum(Transaction.amount).desc()).limit(5).all()
	]

	segment_summary = []
	revenue_at_risk = 0.0

	for segment in SegmentEnum:
		# We aggregate by stored snapshot segment so the dashboard shows the
		# current customer mix and its financial exposure in a form owners can
		# act on immediately.
		segment_predictions = [prediction for prediction in predictions if prediction.segment == segment.value]
		count = len(segment_predictions)
		total_segment_monetary = sum(float(prediction.monetary or 0.0) for prediction in segment_predictions)
		avg_monetary = total_segment_monetary / count if count else 0.0
		at_risk_value = total_segment_monetary if segment in {SegmentEnum.CHURNED, SegmentEnum.AT_RISK} else 0.0
		revenue_at_risk += at_risk_value
		segment_summary.append(
			SegmentSummary(
				segment=segment,
				count=count,
				total_at_risk_value=at_risk_value,
				avg_monetary=avg_monetary,
			)
		)

	total_customers = len(predictions)
	avg_customer_value = total_revenue / total_customers if total_customers else 0.0

	return DashboardMetrics(
		current_reference_date=latest_reference_date,
		scoring_window_start=window_start.date(),
		scoring_window_end=window_end.date(),
		first_transaction_date=available_data_start.date() if available_data_start else None,
		last_transaction_date=available_data_end.date() if available_data_end else None,
		total_customers=total_customers,
		total_revenue=float(total_revenue),
		revenue_at_risk=float(revenue_at_risk),
		avg_customer_value=float(avg_customer_value),
		segment_summary=segment_summary,
		top_products=top_products,
	)


@router.get("/recommendations", response_model=RecommendationsResponse)
def get_dashboard_recommendations(
	location_id: Optional[int] = Query(default=None),
	limit: int = Query(default=20, ge=1, le=100),
	session: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	accessible_location_ids = _get_accessible_location_ids(current_user, location_id)
	business = session.query(Business).filter_by(id=current_user.business_id).first()

	if not business:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Business not found.",
		)

	latest_reference_date = _get_latest_reference_date(
		session,
		business.id,
		accessible_location_ids,
	)

	if latest_reference_date is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="No prediction snapshot found yet. Upload data first.",
		)

	config = _get_effective_business_config(business, session, location_id)
	prediction_query = session.query(Prediction, Customer).join(
		Customer,
		Customer.id == Prediction.customer_id,
	).filter(
		Prediction.business_id == business.id,
		Prediction.reference_date == latest_reference_date,
		Prediction.segment.in_([SegmentEnum.CHURNED.value, SegmentEnum.AT_RISK.value]),
	)

	if accessible_location_ids is not None:
		prediction_query = prediction_query.filter(Prediction.location_id.in_(accessible_location_ids))

	rows = prediction_query.order_by(Prediction.churn_probability.desc()).limit(limit).all()

	recommendations = []
	churned_count = 0
	at_risk_count = 0

	for prediction, customer in rows:
		# Recommendations are generated from the stored snapshot values so the
		# action text matches the exact risk state that was saved for that date.
		recommendation = generate_recommendations(
			customer_id=customer.customer_id,
			segment=prediction.segment,
			churn_probability=prediction.churn_probability,
			recency=prediction.recency,
			frequency=prediction.frequency,
			monetary=prediction.monetary,
			recency_threshold=config["recency_threshold"],
			frequency_threshold=config["frequency_threshold"],
			monetary_threshold=config["monetary_threshold"],
			reference_period_days=config["reference_period_days"],
			currency=config["currency"],
		)

		if prediction.segment == SegmentEnum.CHURNED.value:
			churned_count += 1
		elif prediction.segment == SegmentEnum.AT_RISK.value:
			at_risk_count += 1

		recommendations.append(
			CustomerRecommendation(
				customer_id=customer.customer_id,
				segment=SegmentEnum(prediction.segment),
				churn_probability=float(prediction.churn_probability),
				recommended_action=recommendation["recommendation"]["action_type"],
				urgency="immediate" if recommendation["recommendation"]["urgency"] >= 9 else "high" if recommendation["recommendation"]["urgency"] >= 7 else "medium" if recommendation["recommendation"]["urgency"] >= 4 else "low",
				reasoning=recommendation["recommendation"]["priority_reason"],
			)
		)

	return RecommendationsResponse(
		churned_count=churned_count,
		at_risk_count=at_risk_count,
		recommendations=recommendations,
	)


@router.get("/segments/{segment}/customers", response_model=SegmentCustomersResponse)
def get_segment_customers(
	segment: SegmentEnum,
	location_id: Optional[int] = Query(default=None),
	limit: int = Query(default=100, ge=1, le=500),
	session: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	accessible_location_ids = _get_accessible_location_ids(current_user, location_id)
	business = session.query(Business).filter_by(id=current_user.business_id).first()

	if not business:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Business not found.",
		)

	latest_reference_date = _get_latest_reference_date(
		session,
		business.id,
		accessible_location_ids,
	)

	if latest_reference_date is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="No prediction snapshot found yet. Upload data first.",
		)

	config = _get_effective_business_config(business, session, location_id)
	query = session.query(Prediction, Customer, Location).join(
		Customer,
		Customer.id == Prediction.customer_id,
	).join(
		Location,
		Location.id == Prediction.location_id,
	).filter(
		Prediction.business_id == business.id,
		Prediction.reference_date == latest_reference_date,
		Prediction.segment == segment.value,
	)

	if accessible_location_ids is not None:
		query = query.filter(Prediction.location_id.in_(accessible_location_ids))

	rows = query.order_by(
		Prediction.churn_probability.desc(),
		Prediction.monetary.desc(),
		Customer.last_purchase_date.desc(),
	).limit(limit).all()

	customers = []
	for prediction, customer, location in rows:
		recommendation = generate_recommendations(
			customer_id=customer.customer_id,
			segment=prediction.segment,
			churn_probability=prediction.churn_probability,
			recency=prediction.recency,
			frequency=prediction.frequency,
			monetary=prediction.monetary,
			recency_threshold=config["recency_threshold"],
			frequency_threshold=config["frequency_threshold"],
			monetary_threshold=config["monetary_threshold"],
			reference_period_days=config["reference_period_days"],
			currency=config["currency"],
		)

		customers.append(
			SegmentCustomerSummary(
				customer_id=customer.customer_id,
				customer_name=customer.name,
				phone=customer.phone,
				email=customer.email,
				location_id=location.id,
				location_name=location.name,
				location_code=location.location_code,
				reference_date=prediction.reference_date,
				segment=SegmentEnum(prediction.segment),
				churn_probability=float(prediction.churn_probability),
				recency=int(prediction.recency),
				frequency=int(prediction.frequency),
				monetary=float(prediction.monetary),
				total_spent=float(customer.total_spent or 0.0),
				total_purchases=int(customer.total_purchases or 0),
				last_purchase_date=customer.last_purchase_date.date() if customer.last_purchase_date else None,
				recommended_action=recommendation["recommendation"]["action_type"],
				urgency="immediate" if recommendation["recommendation"]["urgency"] >= 9 else "high" if recommendation["recommendation"]["urgency"] >= 7 else "medium" if recommendation["recommendation"]["urgency"] >= 4 else "low",
				reasoning=recommendation["recommendation"]["priority_reason"],
			)
		)

	return SegmentCustomersResponse(
		segment=segment,
		current_reference_date=latest_reference_date,
		total_customers=len(customers),
		customers=customers,
	)


@router.get("/locations", response_model=DashboardLocationsResponse)
def get_dashboard_locations(
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = session.query(Location).filter(
        Location.business_id == current_user.business_id,
        Location.is_active == True,
    )

    if current_user.assigned_location_ids is not None:
        query = query.filter(Location.id.in_(current_user.assigned_location_ids))

    locations = query.order_by(Location.name.asc()).all()

    return DashboardLocationsResponse(
        locations=[
            DashboardLocationOption(
                id=location.id,
                location_code=location.location_code,
                name=location.name,
            )
            for location in locations
        ]
    )


@router.get("/comparison", response_model=SnapshotComparisonResponse)
def get_dashboard_comparison(
	period: str = Query(default="month"),
	snapshot_offset: int = Query(default=1, ge=1, le=6),
	location_id: Optional[int] = Query(default=None),
	session: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	if period not in {"month", "quarter"}:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="period must be either 'month' or 'quarter'.",
		)

	accessible_location_ids = _get_accessible_location_ids(current_user, location_id)
	business = session.query(Business).filter_by(id=current_user.business_id).first()

	if not business:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Business not found.",
		)

	latest_reference_date = _get_latest_reference_date(session, business.id, accessible_location_ids)
	if latest_reference_date is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="No prediction snapshot found yet. Upload data first.",
		)

	previous_reference_date = _get_previous_reference_date(
		session,
		business.id,
		accessible_location_ids,
		latest_reference_date,
		period,
		snapshot_offset,
	)
	if previous_reference_date is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="No earlier snapshot found for comparison yet.",
		)

	config = _get_effective_business_config(business, session, location_id)

	current_predictions = _load_predictions_for_scope(
		session,
		business.id,
		latest_reference_date,
		accessible_location_ids,
	)
	previous_predictions = _load_predictions_for_scope(
		session,
		business.id,
		previous_reference_date,
		accessible_location_ids,
	)

	current_counts = {segment.value: 0 for segment in SegmentEnum}
	previous_counts = {segment.value: 0 for segment in SegmentEnum}
	for prediction in current_predictions:
		current_counts[prediction.segment] = current_counts.get(prediction.segment, 0) + 1
	for prediction in previous_predictions:
		previous_counts[prediction.segment] = previous_counts.get(prediction.segment, 0) + 1

	# The comparison response is designed for business storytelling:
	# "Are we improving or worsening since last month / quarter?"
	# We compare customer totals, revenue at risk, and each segment count.
	segment_changes = [
		SegmentComparisonDelta(
			segment=segment,
			current_count=current_counts.get(segment.value, 0),
			previous_count=previous_counts.get(segment.value, 0),
			delta=current_counts.get(segment.value, 0) - previous_counts.get(segment.value, 0),
		)
		for segment in SegmentEnum
	]

	current_revenue_at_risk = _calculate_revenue_at_risk(current_predictions)
	previous_revenue_at_risk = _calculate_revenue_at_risk(previous_predictions)
	current_window_revenue = _calculate_window_revenue(
		session,
		business.id,
		latest_reference_date,
		config["reference_period_days"],
		accessible_location_ids,
	)
	previous_window_revenue = _calculate_window_revenue(
		session,
		business.id,
		previous_reference_date,
		config["reference_period_days"],
		accessible_location_ids,
	)

	previous_by_customer = {prediction.customer_id: prediction for prediction in previous_predictions}
	improved_customers = 0
	worsened_customers = 0
	unchanged_customers = 0
	recovered_customers = 0
	slipped_customers = 0

	for current_prediction in current_predictions:
		previous_prediction = previous_by_customer.get(current_prediction.customer_id)
		if previous_prediction is None:
			continue

		current_rank = SEGMENT_RANK.get(current_prediction.segment)
		previous_rank = SEGMENT_RANK.get(previous_prediction.segment)
		if current_rank is None or previous_rank is None:
			continue

		if current_rank > previous_rank:
			improved_customers += 1
		elif current_rank < previous_rank:
			worsened_customers += 1
		else:
			unchanged_customers += 1

		if previous_prediction.segment in {SegmentEnum.CHURNED.value, SegmentEnum.AT_RISK.value} and current_prediction.segment in {SegmentEnum.ACTIVE.value, SegmentEnum.LOYAL.value}:
			recovered_customers += 1

		if previous_prediction.segment in {SegmentEnum.ACTIVE.value, SegmentEnum.LOYAL.value} and current_prediction.segment in {SegmentEnum.AT_RISK.value, SegmentEnum.CHURNED.value}:
			slipped_customers += 1

	return SnapshotComparisonResponse(
		period=period,
		snapshot_offset=snapshot_offset,
		current_reference_date=latest_reference_date,
		previous_reference_date=previous_reference_date,
		current_total_customers=len(current_predictions),
		previous_total_customers=len(previous_predictions),
		total_customers_delta=len(current_predictions) - len(previous_predictions),
		current_window_revenue=current_window_revenue,
		previous_window_revenue=previous_window_revenue,
		window_revenue_delta=current_window_revenue - previous_window_revenue,
		current_revenue_at_risk=current_revenue_at_risk,
		previous_revenue_at_risk=previous_revenue_at_risk,
		revenue_at_risk_delta=current_revenue_at_risk - previous_revenue_at_risk,
		improved_customers=improved_customers,
		worsened_customers=worsened_customers,
		unchanged_customers=unchanged_customers,
		recovered_customers=recovered_customers,
		slipped_customers=slipped_customers,
		segment_changes=segment_changes,
	)


@router.get("/vip-concentration", response_model=VipConcentrationResponse)
def get_dashboard_vip_concentration(
	location_id: Optional[int] = Query(default=None),
	vip_share_threshold: float = Query(default=0.2, ge=0.05, le=0.5),
	limit: int = Query(default=10, ge=1, le=500),
	session: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	accessible_location_ids = _get_accessible_location_ids(current_user, location_id)
	business = session.query(Business).filter_by(id=current_user.business_id).first()

	if not business:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Business not found.",
		)

	latest_reference_date = _get_latest_reference_date(session, business.id, accessible_location_ids)
	if latest_reference_date is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="No prediction snapshot found yet. Upload data first.",
		)

	rows = session.query(Prediction, Customer, Location).join(
		Customer,
		Customer.id == Prediction.customer_id,
	).join(
		Location,
		Location.id == Prediction.location_id,
	).filter(
		Prediction.business_id == business.id,
		Prediction.reference_date == latest_reference_date,
	)

	if accessible_location_ids is not None:
		rows = rows.filter(Prediction.location_id.in_(accessible_location_ids))

	ordered_rows = rows.order_by(Prediction.monetary.desc(), Prediction.churn_probability.desc()).all()
	if not ordered_rows:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="No predictions found for the selected scope.",
		)

	total_customers = len(ordered_rows)
	vip_customer_count = max(1, int(total_customers * vip_share_threshold))
	if vip_customer_count < total_customers * vip_share_threshold:
		vip_customer_count += 1

	vip_rows = ordered_rows[:vip_customer_count]
	total_revenue = float(sum(float(prediction.monetary or 0.0) for prediction, _, _ in ordered_rows))
	vip_revenue = float(sum(float(prediction.monetary or 0.0) for prediction, _, _ in vip_rows))
	non_vip_revenue = float(total_revenue - vip_revenue)
	vip_revenue_share = float(vip_revenue / total_revenue) if total_revenue else 0.0

	top_customers = [
		VipCustomerSummary(
			customer_id=customer.customer_id,
			customer_name=customer.name,
			phone=customer.phone,
			email=customer.email,
			segment=SegmentEnum(prediction.segment),
			location_name=location.name,
			location_code=location.location_code,
			churn_probability=float(prediction.churn_probability),
			monetary=float(prediction.monetary or 0.0),
			total_spent=float(customer.total_spent or 0.0),
			total_purchases=int(customer.total_purchases or 0),
		)
		for prediction, customer, location in vip_rows[:limit]
	]

	return VipConcentrationResponse(
		current_reference_date=latest_reference_date,
		total_customers=total_customers,
		vip_customer_count=vip_customer_count,
		vip_share_threshold=vip_share_threshold,
		vip_revenue=vip_revenue,
		total_revenue=total_revenue,
		vip_revenue_share=vip_revenue_share,
		non_vip_revenue=non_vip_revenue,
		top_customers=top_customers,
	)


@router.get("/interventions", response_model=InterventionListResponse)
def list_dashboard_interventions(
	location_id: Optional[int] = Query(default=None),
	status_filter: Optional[str] = Query(default=None, alias="status"),
	limit: int = Query(default=50, ge=1, le=200),
	session: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	accessible_location_ids = _get_accessible_location_ids(current_user, location_id)

	query = session.query(BusinessAction, Customer).join(
		Customer,
		Customer.id == BusinessAction.customer_id,
	).filter(
		BusinessAction.business_id == current_user.business_id,
	)

	if accessible_location_ids is not None:
		query = query.filter(BusinessAction.location_id.in_(accessible_location_ids))

	if status_filter:
		query = query.filter(BusinessAction.status == status_filter)

	rows = query.order_by(BusinessAction.action_date.desc(), BusinessAction.id.desc()).all()
	actions = [action for action, _ in rows]
	# These summary numbers are the beginning of intervention ROI tracking.
	# They answer basic operational questions first: how many actions were
	# taken, how many were completed, who returned, and what value came back.
	returned_customers = sum(1 for action in actions if action.customer_returned)
	completed_actions = sum(1 for action in actions if action.status == "completed")
	total_revenue_recovered = float(sum(float(action.revenue_recovered or 0.0) for action in actions))

	return InterventionListResponse(
		total_actions=len(actions),
		completed_actions=completed_actions,
		returned_customers=returned_customers,
		total_revenue_recovered=total_revenue_recovered,
		actions=[_serialize_action(action, customer) for action, customer in rows[:limit]],
	)


@router.post("/interventions", response_model=BusinessActionResponse, status_code=status.HTTP_201_CREATED)
def create_dashboard_intervention(
	payload: BusinessActionCreateRequest,
	session: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	prediction = session.query(Prediction).filter(
		Prediction.id == payload.prediction_id,
		Prediction.business_id == current_user.business_id,
	).first()

	if not prediction:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Prediction not found for this business.",
		)

	accessible_location_ids = _get_accessible_location_ids(current_user, prediction.location_id)
	if accessible_location_ids is not None and prediction.location_id not in accessible_location_ids:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="You do not have access to that prediction.",
		)

	customer = session.query(Customer).filter(
		Customer.id == prediction.customer_id,
		Customer.business_id == current_user.business_id,
	).first()
	if not customer:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Customer not found for this prediction.",
		)

	# An intervention is attached to the exact prediction snapshot that caused
	# the business to act. This is critical later when we want to analyze which
	# actions worked for which segment and snapshot conditions.
	action = BusinessAction(
		business_id=current_user.business_id,
		location_id=prediction.location_id,
		customer_id=prediction.customer_id,
		prediction_id=prediction.id,
		segment_when_actioned=prediction.segment,
		action_type=payload.action_type,
		action_description=payload.action_description,
		action_date=payload.action_date or date.today(),
		reference_date=prediction.reference_date,
		status="pending",
	)
	session.add(action)
	session.commit()
	session.refresh(action)

	return _serialize_action(action, customer)


@router.patch("/interventions/{action_id}", response_model=BusinessActionResponse)
def update_dashboard_intervention(
	action_id: int,
	payload: BusinessActionOutcomeUpdateRequest,
	session: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	row = session.query(BusinessAction, Customer).join(
		Customer,
		Customer.id == BusinessAction.customer_id,
	).filter(
		BusinessAction.id == action_id,
		BusinessAction.business_id == current_user.business_id,
	).first()

	if not row:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Intervention not found for this business.",
		)

	action, customer = row
	accessible_location_ids = _get_accessible_location_ids(current_user, action.location_id)
	if accessible_location_ids is not None and action.location_id not in accessible_location_ids:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="You do not have access to that intervention.",
		)

	# Outcome recording is what turns a dashboard into a learning system.
	# Once businesses record returns and recovered revenue, we can later build
	# real supervised labels from these historical outcomes.
	action.status = payload.status
	action.outcome_recorded = payload.outcome_recorded
	action.customer_returned = payload.customer_returned
	action.days_to_return = payload.days_to_return
	action.revenue_recovered = payload.revenue_recovered

	session.commit()
	session.refresh(action)

	return _serialize_action(action, customer)