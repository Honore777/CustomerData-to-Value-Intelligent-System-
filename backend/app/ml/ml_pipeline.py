"""
Retention Scoring Pipeline
==========================

This pipeline intentionally avoids training a model during CSV upload.
Instead it:
1. loads transactions for a business and location
2. calculates RFM metrics for a snapshot date
3. generates direct churn-risk scores from business rules
4. stores those results as historical prediction snapshots
5. records segment history so month/quarter comparisons stay reliable

This is the professional foundation for SME retention products:
clear scores now, clean snapshots for future supervised ML later.
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy.orm import Session

from app.ml.churn_utils import (
    calculate_rfm_metrics,
    generate_churn_labels,
    generate_churn_scores,
    generate_recommendations,
)
from app.models import Business, Prediction, PredictionHistory, Transaction

logger = logging.getLogger(__name__)

SEGMENT_RANK = {
    # Lower numbers represent weaker customer health.
    # This lets us compare two snapshots and answer a business question
    # that owners care about directly: "did this customer improve or worsen
    # after our follow-up efforts?"
    "churned": 0,
    "at_risk": 1,
    "active": 2,
    "loyal": 3,
}


def load_transactions_for_business(
    business_id: int,
    reference_date: date,
    location_id: int,
    reference_period_days: int,
    session: Session,
) -> pd.DataFrame:
    """Load only the transactions that belong to the requested scoring window."""

    # The scoring window is the business-defined observation period.
    # Example: if reference_date is July 18 and the business uses 60 days,
    # we only score behavior inside the last 60 days. This keeps the score
    # aligned with how often that business expects customers to return.
    window_start = reference_date - timedelta(days=reference_period_days)

    transactions = session.query(Transaction).filter(
        Transaction.business_id == business_id,
        Transaction.location_id == location_id,
        Transaction.purchase_date >= window_start,
        Transaction.purchase_date <= reference_date,
    ).all()

    data = [
        {
            "customer_id": transaction.customer_id,
            "purchase_date": transaction.purchase_date,
            "amount": transaction.amount,
        }
        for transaction in transactions
    ]

    dataframe = pd.DataFrame(data)
    logger.info("Loaded %s transactions for business %s", len(dataframe), business_id)
    return dataframe


def score_customers_with_rfm(
    transactions_df: pd.DataFrame,
    reference_date: date,
    business_config: Dict[str, Any],
) -> pd.DataFrame:
    """Turn transactions into direct churn-risk scores and segments."""

    # Step 1: summarize raw transactions into RFM features per customer.
    # This converts many rows of purchases into one row per customer,
    # which becomes the canonical snapshot record for that date.
    rfm_df = calculate_rfm_metrics(
        transactions_df,
        reference_date=reference_date,
        reference_period_days=business_config["reference_period_days"],
    )

    if rfm_df.empty:
        return rfm_df

    # Step 2: generate a direct churn-risk score from business rules.
    # We are intentionally NOT training a model here. The score is a
    # transparent business risk estimate derived from RFM behavior.
    scored_df = generate_churn_scores(
        rfm_df,
        recency_threshold=business_config["recency_threshold"],
        frequency_threshold=business_config["frequency_threshold"],
        monetary_threshold=business_config["monetary_threshold"],
    )

    # Step 3: convert the numeric score into explainable business segments.
    # These labels are what owners, managers, and intervention workflows use
    # on the dashboard because they are easy to act on operationally.
    labeled_df = generate_churn_labels(
        scored_df,
        recency_threshold=business_config["recency_threshold"],
        frequency_threshold=business_config["frequency_threshold"],
        monetary_threshold=business_config["monetary_threshold"],
    )

    logger.info("Generated direct churn scores for %s customers", len(labeled_df))
    return labeled_df


def _delete_existing_snapshot(
    business_id: int,
    location_id: int,
    reference_date: date,
    session: Session,
) -> None:
    """Replace the same snapshot date cleanly so history stays deterministic."""

    # A reference date should produce one authoritative snapshot per customer
    # and location. If we upload the same date again after fixing data,
    # we replace the old snapshot so month/quarter comparisons do not mix
    # duplicate or conflicting records.
    existing_predictions = session.query(Prediction).filter(
        Prediction.business_id == business_id,
        Prediction.location_id == location_id,
        Prediction.reference_date == reference_date,
    ).all()

    for prediction in existing_predictions:
        session.delete(prediction)

    if existing_predictions:
        session.flush()
        logger.info(
            "Replaced %s existing predictions for location %s on %s",
            len(existing_predictions),
            location_id,
            reference_date,
        )


def _get_previous_predictions_by_customer(
    business_id: int,
    location_id: int,
    reference_date: date,
    customer_ids: List[int],
    session: Session,
) -> Dict[int, Prediction]:
    """Load the most recent earlier snapshot per customer for comparisons."""

    if not customer_ids:
        return {}

    # We fetch older rows ordered by customer then newest-first date.
    # The setdefault trick below keeps only the first row per customer,
    # which is therefore the latest snapshot before the current one.
    previous_rows = session.query(Prediction).filter(
        Prediction.business_id == business_id,
        Prediction.location_id == location_id,
        Prediction.customer_id.in_(customer_ids),
        Prediction.reference_date < reference_date,
    ).order_by(
        Prediction.customer_id.asc(),
        Prediction.reference_date.desc(),
    ).all()

    previous_by_customer: Dict[int, Prediction] = {}
    for row in previous_rows:
        previous_by_customer.setdefault(row.customer_id, row)

    return previous_by_customer


def _segment_improved(previous_segment: str, current_segment: str) -> bool | None:
    """Higher rank means healthier customer status."""

    # Returning None instead of False is important here.
    # None means "we cannot judge improvement yet" rather than
    # incorrectly marking the change as negative.
    if previous_segment not in SEGMENT_RANK or current_segment not in SEGMENT_RANK:
        return None

    return SEGMENT_RANK[current_segment] > SEGMENT_RANK[previous_segment]


def store_prediction_snapshot(
    business_id: int,
    location_id: int,
    reference_date: date,
    rfm_predictions: pd.DataFrame,
    session: Session,
) -> List[Prediction]:
    """Persist the scored snapshot and its customer-by-customer history."""

    # First clear any previous version of the same snapshot date so the
    # stored history remains auditable and deterministic.
    _delete_existing_snapshot(
        business_id=business_id,
        location_id=location_id,
        reference_date=reference_date,
        session=session,
    )

    customer_ids = [int(customer_id) for customer_id in rfm_predictions["customer_id"].tolist()]
    previous_predictions = _get_previous_predictions_by_customer(
        business_id=business_id,
        location_id=location_id,
        reference_date=reference_date,
        customer_ids=customer_ids,
        session=session,
    )

    prediction_objects: List[Prediction] = []
    for _, row in rfm_predictions.iterrows():
        # Each Prediction row is the stored "state of this customer at this
        # exact snapshot date." This is the foundation for trend analysis now
        # and supervised ML later, because future labels can be attached back
        # to these dated snapshots.
        prediction = Prediction(
            business_id=business_id,
            location_id=location_id,
            customer_id=int(row["customer_id"]),
            reference_date=reference_date,
            segment=str(row["segment"]),
            churn_probability=float(row["churn_probability"]),
            recency=int(row["recency"]),
            frequency=int(row["frequency"]),
            monetary=float(row["monetary"]),
        )
        session.add(prediction)
        prediction_objects.append(prediction)

    session.flush()

    for prediction in prediction_objects:
        previous_prediction = previous_predictions.get(prediction.customer_id)
        # PredictionHistory records movement between snapshots.
        # This is what allows month-over-month or quarter-over-quarter
        # comparisons to answer questions like:
        # - how many customers worsened?
        # - how many improved after interventions?
        # - how long were they stuck in a risky segment?
        history = PredictionHistory(
            business_id=business_id,
            location_id=location_id,
            customer_id=prediction.customer_id,
            prediction_id=prediction.id,
            previous_segment=previous_prediction.segment if previous_prediction else None,
            current_segment=prediction.segment,
            previous_reference_date=previous_prediction.reference_date if previous_prediction else None,
            current_reference_date=reference_date,
            segment_improved=_segment_improved(previous_prediction.segment, prediction.segment) if previous_prediction else None,
            days_in_previous_segment=(reference_date - previous_prediction.reference_date).days if previous_prediction else None,
        )
        session.add(history)

    logger.info(
        "Stored %s prediction snapshots and matching history rows for location %s",
        len(prediction_objects),
        location_id,
    )

    return prediction_objects


def _serialize_predictions(prediction_objects: List[Prediction]) -> List[Dict[str, Any]]:
    """Return plain dicts for upload responses and debugging."""

    return [
        {
            "customer_id": prediction.customer_id,
            "reference_date": prediction.reference_date,
            "segment": prediction.segment,
            "churn_probability": prediction.churn_probability,
            "recency": prediction.recency,
            "frequency": prediction.frequency,
            "monetary": prediction.monetary,
            "location_id": prediction.location_id,
        }
        for prediction in prediction_objects
    ]


def full_pipeline(
    business_id: int,
    reference_date: date,
    location_id: int,
    session: Session,
) -> Dict[str, Any]:
    """Score one business-location snapshot and persist it for future comparisons."""

    logger.info("Starting full pipeline for business %s, reference_date=%s", business_id, reference_date)

    try:
        business = session.query(Business).filter_by(id=business_id).first()
        if not business:
            raise ValueError(f"Business {business_id} not found")

        business_config = {
            "reference_period_days": business.reference_period_days,
            "recency_threshold": business.recency_threshold_days,
            "frequency_threshold": business.frequency_threshold,
            "monetary_threshold": business.monetary_threshold,
            "currency": business.currency,
        }
        # These settings are business-specific because customer behavior is
        # local. A pharmacy, salon, supermarket, or boutique in Africa can
        # have very different visit cycles, basket sizes, and inactivity norms.
        logger.info("Business config: %s", business_config)

        transactions_df = load_transactions_for_business(
            business_id=business_id,
            reference_date=reference_date,
            location_id=location_id,
            reference_period_days=business_config["reference_period_days"],
            session=session,
        )

        if transactions_df.empty:
            logger.warning("No transactions found for business %s in window", business_id)
            return {
                "error": "No transactions found",
                "business_id": business_id,
                "reference_date": reference_date,
            }

        rfm_predictions = score_customers_with_rfm(
            transactions_df=transactions_df,
            reference_date=reference_date,
            business_config=business_config,
        )

        if rfm_predictions.empty:
            logger.warning("No customers produced RFM rows for business %s", business_id)
            return {
                "error": "No customer snapshots generated",
                "business_id": business_id,
                "reference_date": reference_date,
            }

        prediction_objects = store_prediction_snapshot(
            business_id=business_id,
            location_id=location_id,
            reference_date=reference_date,
            rfm_predictions=rfm_predictions,
            session=session,
        )

        recommendations = []
        for prediction in prediction_objects:
            # Recommendations are generated from the stored snapshot, not from
            # transient in-memory calculations. That keeps dashboard actions,
            # intervention records, and later audits aligned to the same data.
            recommendations.append(
                generate_recommendations(
                    customer_id=str(prediction.customer_id),
                    segment=prediction.segment,
                    churn_probability=prediction.churn_probability,
                    recency=prediction.recency,
                    frequency=prediction.frequency,
                    monetary=prediction.monetary,
                    recency_threshold=business_config["recency_threshold"],
                    frequency_threshold=business_config["frequency_threshold"],
                    monetary_threshold=business_config["monetary_threshold"],
                    reference_period_days=business_config["reference_period_days"],
                    currency=business_config["currency"],
                )
            )

        segment_counts = rfm_predictions["segment"].value_counts().to_dict()
        scoring_metadata = {
            # We keep this metadata block because the frontend already expects
            # structured scoring details from the upload response. The values
            # now describe a rule-based scoring engine instead of fake model
            # accuracy, which is more honest and more stable for deployment.
            "engine": "rule_based_rfm",
            "scoring_version": "rfm_v1",
            "accuracy": None,
            "source": "direct_scoring",
        }

        logger.info("Scoring complete for location %s. Segments: %s", location_id, segment_counts)

        return {
            "reference_date": reference_date,
            "business_id": business_id,
            "total_customers": len(rfm_predictions),
            "segment_counts": segment_counts,
            "predictions": _serialize_predictions(prediction_objects),
            "recommendations": recommendations,
            "model_metrics": scoring_metadata,
            "business_config": business_config,
        }

    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        raise