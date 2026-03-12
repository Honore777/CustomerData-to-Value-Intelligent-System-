"""
Churn Prediction Utilities - RFM Calculation and Segmentation
Handles all business logic for identifying customer segments
"""

from datetime import datetime, timedelta, date
import pandas as pd
import numpy as np
from typing import Tuple, List, Dict
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


def calculate_rfm_metrics(
    transactions_df: pd.DataFrame,
    reference_date: date = None,
    reference_period_days: int = 60
) -> pd.DataFrame:
    """
    Convert raw transactions into RFM metrics using a lookback window.
    
    KEY: The lookback window determines which purchases "count"
    - Window = [reference_date - reference_period_days, reference_date]
    - Only purchases in this window affect RFM
    - Old purchases outside window are ignored (aged out)
    
    Example:
      reference_date = May 1
      reference_period_days = 60
      Window = [Mar 2 - May 1]
      - Feb 15 purchase: IGNORED (too old)
      - Mar 10 purchase: COUNTED
      - Apr 25 purchase: COUNTED
      - May 5 purchase: NOT COUNTED (after reference_date)
    
    Args:
        transactions_df: DataFrame with columns: customer_id, purchase_date, amount
        reference_date: Snapshot date (default = today). Purchases must be <= this date
        reference_period_days: Lookback window in days (60 = last 2 months)
    
    Returns:
        DataFrame with RFM columns: customer_id, recency, frequency, monetary, last_purchase_date
    """
    
    # If the caller does not pass a snapshot date, we score relative to today.
    # In production uploads we usually pass an explicit reference date so the
    # snapshot can be compared later against other months or quarters.
    if reference_date is None:
        reference_date = date.today()

    # Keep dates in pandas datetime format for vectorized calculations.
    # Earlier code converted purchase_date into plain Python date objects,
    # which broke the later `.dt.days` accessor because `.dt` only works on
    # pandas datetimelike series.
    reference_ts = pd.Timestamp(reference_date).normalize()

    df = transactions_df.copy()
    df['purchase_date'] = pd.to_datetime(df['purchase_date']).dt.normalize()
    
    # Calculate window boundaries using pandas timestamps so filtering and
    # recency math stay in one consistent date type.
    window_start = reference_ts - pd.Timedelta(days=reference_period_days)
    
    # CRITICAL: Only include purchases in [window_start, reference_date]
    df_windowed = df[
        (df['purchase_date'] >= window_start) & 
        (df['purchase_date'] <= reference_ts)
    ].copy()

    if df_windowed.empty:
        logger.info(f"No transactions in window [{window_start.date()}, {reference_ts.date()}]")
        return pd.DataFrame(columns=['customer_id', 'recency', 'frequency', 'monetary', 'last_purchase_date'])
    
    # Group many transaction rows into one customer snapshot row.
    # This is the moment where raw purchases become retention features.
    rfm = df_windowed.groupby('customer_id').agg({
        'purchase_date': ['max', 'count'],  # last_purchase_date and frequency
        'amount': 'sum'                      # monetary value
    }).reset_index()
    
    # Flatten column names
    rfm.columns = ['customer_id', 'last_purchase_date', 'frequency', 'monetary']
    
    # Recency is the strongest short-term retention signal in most retail and
    # service businesses: the longer a customer stays away beyond expectation,
    # the more attention they usually need.
    rfm['recency'] = (reference_ts - rfm['last_purchase_date']).dt.days
    
    logger.info(f"RFM calculated for {len(rfm)} customers using window [{window_start.date()}, {reference_ts.date()}]")
    
    return rfm[['customer_id', 'recency', 'frequency', 'monetary', 'last_purchase_date']]


def generate_churn_labels(
    rfm_df: pd.DataFrame,
    recency_threshold: int = 7,
    frequency_threshold: int = 5,
    monetary_threshold: float = 500
) -> pd.DataFrame:
    """
    Assign segment labels based on RFM thresholds.
    
    Business rules:
    - CHURNED: No recent activity + low engagement
    - AT_RISK: No recent activity + some engagement
    - ACTIVE: Recent activity + normal engagement
    - LOYAL: Recent activity + high engagement
    
    Args:
        rfm_df: DataFrame with RFM metrics
        recency_threshold: Days without purchase = inactive
        frequency_threshold: Minimum purchases to be considered engaged
        monetary_threshold: Minimum amount spent to be considered valuable
    
    Returns:
        DataFrame with added 'segment' column
    """
    
    rfm_copy = rfm_df.copy()
    
    def assign_segment(row):
        """
        Assign segment based on RFM thresholds.
        """
        recency = row['recency']
        frequency = row['frequency']
        monetary = row['monetary']
        
        # Priority order matters. We classify the clearest risk states first,
        # then fall back to healthier states. This keeps segment definitions
        # stable and easy to explain to a non-technical business owner.
        if recency > recency_threshold and frequency < frequency_threshold:
            return 'churned'  # Inactive + low engagement = CHURNED
        
        elif recency > recency_threshold and frequency >= frequency_threshold:
            return 'at_risk'  # Inactive but was engaged = AT_RISK
        
        elif recency <= recency_threshold and frequency >= (frequency_threshold * 2):
            return 'loyal'  # Very recent + high engagement = LOYAL
        
        else:
            return 'active'  # Recent activity = ACTIVE (default)
    
    rfm_copy['segment'] = rfm_copy.apply(assign_segment, axis=1)
    
    return rfm_copy


def calculate_churn_score(
    recency: int,
    frequency: int,
    monetary: float,
    recency_threshold: int,
    frequency_threshold: int,
    monetary_threshold: float
) -> float:
    """
    Convert RFM metrics into a churn probability (0.0 to 1.0).

    In the current production design, this is a direct business risk score,
    not a supervised machine-learning label. We keep the 0.0-1.0 scale because
    it is intuitive for ranking and easy to surface as a percentage in the UI.
    
    Scoring logic:
    - recency_score: Days inactive / threshold → normalized impact
    - frequency_score: How far below engagement level
    - monetary_score: How far below value level
    
    Weights (configurable):
    - 60% recency (most important - recent = most reliable indicator)
    - 25% frequency (engaged + active = loyal)
    - 15% monetary (high spenders = more valuable)
    
    Args:
        recency, frequency, monetary: RFM metrics
        *_threshold: Business's thresholds
    
    Returns:
        Risk score between 0.0 (healthy) and 1.0 (critical churn risk)
    """
    
    # Normalize recency into a comparable 0-1 scale.
    # If a business says 7 inactive days is already risky, then hitting 7 days
    # should contribute the maximum recency pressure to the score.
    recency_score = min(recency / max(recency_threshold, 1), 1.0)
    
    # Frequency is inverted because lower activity means higher risk.
    # A customer with very few purchases relative to expectation contributes
    # more churn pressure than a consistently engaged customer.
    frequency_score = max(1.0 - (frequency / max(frequency_threshold, 1)), 0.0)
    
    # Monetary is also inverted. Lower recent spend can signal fading customer
    # value or weakening engagement, especially when it drops below the business
    # threshold for a meaningful customer relationship.
    monetary_score = max(1.0 - (monetary / max(monetary_threshold, 1)), 0.0)
    
    # Weighted combination: recency dominates because "time since last visit"
    # is usually the fastest early warning sign in local retail settings.
    # Frequency and monetary still matter, but they support the picture rather
    # than override a long absence.
    churn_score = (
        recency_score * 0.60 +    # 60% weight on recency (most predictive)
        frequency_score * 0.25 +  # 25% weight on frequency (engagement)
        monetary_score * 0.15     # 15% weight on monetary (value)
    )
    
    # Clamp the score so API consumers can always treat it as a percentage-ready
    # value without worrying about boundary overflow.
    churn_score = min(max(churn_score, 0.0), 1.0)
    
    return churn_score


def generate_recommendations(
    customer_id: str,
    segment: str,
    churn_probability: float,
    recency: int,
    frequency: int,
    monetary: float,
    recency_threshold: int,
    frequency_threshold: int,
    monetary_threshold: float,
    reference_period_days: int = 60,
    currency: str = "RWF"
) -> Dict:
    """
    Generate DETAILED business-specific recommendations with actual data.
    
    Shows the business EXACTLY why we're recommending an action:
    - What's the churn probability?
    - How long have they NOT purchased? (recency vs threshold)
    - How many purchases? (frequency vs threshold)
    - How much spent? (monetary vs threshold)
    - In what timeframe? (last 60 days, last 30 days, etc.)
    
    Example output:
    {
        'customer_id': 'CUST001',
        'segment': 'at_risk',
        'churn_probability': 0.78,
        'analysis': {
            'days_inactive': 18,
            'threshold_days': 7,
            'status': 'No purchase for 18 days (threshold: 7 days) ⚠️',
            'purchase_frequency': '2 purchases',
            'frequency_threshold': 5,
            'status': 'Below engagement level (2 vs 5 threshold) ⚠️',
            'total_spent': 2500,
            'monetary_status': '2,500 RWF in last 60 days (threshold: 500 RWF) ✓',
            'timeframe': 'Last 60 days'
        },
        'recommendation': {
            'action_type': 'loyalty_reward_sms',
            'description': 'Customer CUST001 is at high risk (78% churn probability). They haven\'t purchased in 18 days (7-day threshold exceeded by 11 days). With only 2 purchases in the last 60 days, they\'re below the engagement level (5+ needed). However, they spent 2,500 RWF. Send personalized SMS with loyalty reward to encourage return visit.',
            'urgency': 8,
            'discount_percent': 15,
            'priority_reason': 'High churn probability + extended inactivity'
        }
    }
    
    Args:
        customer_id: Unique customer identifier
        segment: Segment ('churned', 'at_risk', 'active', 'loyal')
        churn_probability: Predicted churn (0.0-1.0)
        recency, frequency, monetary: RFM metrics
        *_threshold: Business thresholds
        reference_period_days: Lookback window (e.g., 60 days)
        currency: Currency code (RWF, UGX, KES, etc.)
    
    Returns:
        Dictionary with detailed analysis and recommendation
    """
    
    # The analysis block is written for humans, not just machines. It gives the
    # owner the operational reasoning behind the score so they can trust and act
    # on it without reading raw RFM numbers only.
    days_over_threshold = recency - recency_threshold
    frequency_deficit = frequency_threshold - frequency
    monetary_deficit = monetary_threshold - monetary
    
    analysis = {
        'reference_period': f"{reference_period_days} days",
        'days_inactive': recency,
        'threshold_days': recency_threshold,
        'inactivity_status': f"No purchase for {recency} days (threshold: {recency_threshold} days)",
        'inactivity_severity': "🔴 CRITICAL" if days_over_threshold > recency_threshold * 2 else "⚠️ WARNING" if recency > recency_threshold else "✓ OK",
        
        'purchase_frequency': f"{frequency} purchases",
        'frequency_threshold': frequency_threshold,
        'engagement_status': f"{frequency} purchases in last {reference_period_days} days (need {frequency_threshold}+)",
        'engagement_severity': "🔴 LOW" if frequency_deficit > 5 else "⚠️ BELOW" if frequency < frequency_threshold else "✓ GOOD",
        
        'total_spent': f"{monetary:,.0f} {currency}",
        'monetary_threshold': f"{monetary_threshold:,.0f} {currency}",
        'spending_status': f"{monetary:,.0f} {currency} in last {reference_period_days} days (threshold: {monetary_threshold:,.0f})",
        'spending_severity': "⚠️ BELOW" if monetary < monetary_threshold else "✓ GOOD",
    }
    
    # Recommendation logic is intentionally tied to the segment language the
    # business sees on the dashboard. That makes the system easier to adopt:
    # segment first, recommended action second.
    if segment == 'churned':
        recommendation = {
            'action_type': 'reengagement_campaign',
            'discount_percent': 25,
            'urgency': 10,
            'priority_reason': f'CHURNED: {recency} days inactive (vs {recency_threshold} threshold). Only {frequency} purchases. {churn_probability:.0%} churn probability.',
            'detailed_action': f'Customer {customer_id} has churned. They haven\'t made a purchase in {recency} days (threshold: {recency_threshold} days), and made only {frequency} purchases in the last {reference_period_days} days. With {churn_probability:.0%} churn probability, immediate action needed. Recommend: Send personalized reengagement SMS + 25% discount with limited time offer (3-5 days).',
            'followup': 'If no response after 7 days, send email with exclusive offer'
        }
    
    elif segment == 'at_risk':
        recommendation = {
            'action_type': 'loyalty_intervention',
            'discount_percent': 15,
            'urgency': 8,
            'priority_reason': f'AT_RISK: {recency} days inactive (vs {recency_threshold} threshold). Frequency: {frequency}/{frequency_threshold}. {churn_probability:.0%} risk.',
            'detailed_action': f'Customer {customer_id} is at risk. Extended inactivity: {recency} days (threshold: {recency_threshold} days). Purchase pattern: {frequency} purchases in {reference_period_days} days (below {frequency_threshold} target). Spending: {monetary:,.0f} {currency}. With {churn_probability:.0%} churn probability, send personalized SMS acknowledging their value, offering loyalty reward or time-limited incentive (10-15% discount).',
            'followup': 'Monitor for return purchase within 14 days'
        }
    
    elif segment == 'active':
        recommendation = {
            'action_type': 'engagement_maintenance',
            'discount_percent': 5,
            'urgency': 3,
            'priority_reason': f'ACTIVE: Recent activity ({recency} days). Frequency: {frequency}. Low churn risk ({churn_probability:.0%}).',
            'detailed_action': f'Customer {customer_id} is actively engaged. Recent purchase: {recency} days ago. Activity: {frequency} purchases in {reference_period_days} days. Spending: {monetary:,.0f} {currency}. Continue regular communication with standard offers and updates.',
            'followup': 'Continue standard nurturing communications'
        }
    
    elif segment == 'loyal':
        recommendation = {
            'action_type': 'vip_retention',
            'discount_percent': 0,  # Loyal customers don't need discounts
            'urgency': 4,
            'priority_reason': f'LOYAL: Very active ({recency} days). High frequency: {frequency}. High value: {monetary:,.0f} {currency}. {churn_probability:.0%} churn risk.',
            'detailed_action': f'Customer {customer_id} is a valued loyal customer. Very active: purchased {recency} days ago. Frequent purchaser: {frequency} transactions in {reference_period_days} days. High lifetime value: {monetary:,.0f} {currency} spent. Use VIP treatment: exclusive early access to promotions, loyalty points bonus, personalized service, premium customer support.',
            'followup': 'Schedule monthly VIP exclusives; maintain premium relationship'
        }
    
    else:
        # Fallback keeps the API resilient if a future segment name arrives.
        # We prefer a safe standard action over breaking the recommendation feed.
        recommendation = {
            'action_type': 'standard_communication',
            'discount_percent': 0,
            'urgency': 2,
            'priority_reason': f'Unknown segment: {segment}',
            'detailed_action': f'Standard treatment for customer {customer_id}',
            'followup': 'Continue standard communications'
        }
    
    return {
        'customer_id': customer_id,
        'segment': segment,
        'churn_probability': churn_probability,
        'churn_probability_percent': f"{churn_probability:.0%}",
        'analysis': analysis,
        'recommendation': recommendation
    }




def generate_churn_scores(
    rfm_df: pd.DataFrame,
    recency_threshold: int = 7,
    frequency_threshold: int = 5,
    monetary_threshold: float = 500
) -> pd.DataFrame:
    """
    Generate churn probabilities for every customer in the RFM dataframe.

    This is the batch version of calculate_churn_score(...):
    - input: many customers
    - output: same dataframe plus churn_probability
    """

    rfm_copy = rfm_df.copy()

    # Apply the same direct scoring logic to every customer row in the current
    # snapshot. This produces a rankable risk value that later drives segment
    # assignment, recommendations, and intervention prioritization.
    rfm_copy["churn_probability"] = rfm_copy.apply(
        lambda row: calculate_churn_score(
            recency=row["recency"],
            frequency=row["frequency"],
            monetary=row["monetary"],
            recency_threshold=recency_threshold,
            frequency_threshold=frequency_threshold,
            monetary_threshold=monetary_threshold,
        ),
        axis=1,
    )

    return rfm_copy