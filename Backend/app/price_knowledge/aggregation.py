from typing import List
from decimal import Decimal
import statistics


def aggregate_normalized_rates_decimal(rates: List[Decimal]) -> Decimal:
    """
    Deterministic price aggregation policy (PRICE_AGGREGATION_V01) using Decimal.
    Uses median of normalized unit rates to provide outlier robustness.
    """
    if not rates:
        raise ValueError("Cannot aggregate empty rate list.")
    # Sorted median
    sorted_rates = sorted(rates)
    n = len(sorted_rates)
    mid = n // 2
    if n % 2 == 1:
        return sorted_rates[mid]
    else:
        return (sorted_rates[mid - 1] + sorted_rates[mid]) / Decimal("2")


def aggregate_normalized_rates(rates: List[float]) -> float:
    dec_rates = [Decimal(str(r)) for r in rates]
    med_dec = aggregate_normalized_rates_decimal(dec_rates)
    return float(round(med_dec, 4))
