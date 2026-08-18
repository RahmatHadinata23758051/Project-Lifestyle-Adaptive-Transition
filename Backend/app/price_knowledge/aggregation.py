import statistics
from typing import List


def aggregate_normalized_rates(rates: List[float]) -> float:
    """
    Deterministic price aggregation policy (PRICE_AGGREGATION_V01).
    Uses median of normalized unit rates to provide outlier robustness.
    """
    if not rates:
        raise ValueError("Cannot aggregate empty rate list.")
    return round(float(statistics.median(rates)), 4)
