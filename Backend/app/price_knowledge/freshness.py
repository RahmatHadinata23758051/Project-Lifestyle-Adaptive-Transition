from typing import Optional
from datetime import datetime, timezone
from app.price_knowledge.constants import PriceFreshness, PricePolicy


def determine_price_freshness(
    observed_at: datetime,
    reference_date: Optional[datetime] = None,
) -> PriceFreshness:
    """
    Evaluates price observation freshness based on PRICE_FRESHNESS_V01:
    - <= 30 days: FRESH
    - 31..90 days: AGING
    - > 90 days: STALE
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)

    # Ensure timezone awareness compatibility
    if observed_at.tzinfo is None and reference_date.tzinfo is not None:
        reference_date = reference_date.replace(tzinfo=None)
    elif observed_at.tzinfo is not None and reference_date.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=None)

    age_days = (reference_date - observed_at).days

    if age_days <= PricePolicy.FRESH_DAYS:
        return PriceFreshness.FRESH
    elif age_days <= PricePolicy.AGING_DAYS:
        return PriceFreshness.AGING
    else:
        return PriceFreshness.STALE
