from typing import List, Optional, Tuple
from datetime import datetime
from app.nutrition_adaptation.constants import (
    WeightTrendDirection,
    EvaluationConfidence,
    AdaptationEvaluationPolicy,
)
from app.nutrition_adaptation.models import (
    WeightObservationDTO,
    WeightTrendSummaryDTO,
)


def calculate_linear_slope(points: List[Tuple[float, float]]) -> float:
    """
    Computes standard ordinary least squares linear regression slope: sum((x - mx)(y - my)) / sum((x - mx)^2).
    """
    n = len(points)
    if n < 2:
        return 0.0

    mean_x = sum(p[0] for p in points) / n
    mean_y = sum(p[1] for p in points) / n

    numerator = sum((p[0] - mean_x) * (p[1] - mean_y) for p in points)
    denominator = sum((p[0] - mean_x) ** 2 for p in points)

    if denominator == 0.0:
        return 0.0

    return numerator / denominator


def evaluate_weight_trend(measurements: List[WeightObservationDTO]) -> WeightTrendSummaryDTO:
    """
    Evaluates weight trend slope, direction, interpretability, and confidence.
    """
    if len(measurements) < 2:
        return WeightTrendSummaryDTO(
            measurement_count=len(measurements),
            start_weight_kg=measurements[0].weight_kg if measurements else None,
            end_weight_kg=measurements[-1].weight_kg if measurements else None,
            slope_kg_per_day=None,
            direction=WeightTrendDirection.INDETERMINATE,
            confidence=EvaluationConfidence.UNKNOWN,
            is_interpretable=False,
            outlier_count=0,
        )

    # Sort measurements chronologically
    sorted_m = sorted(measurements, key=lambda m: m.measured_at)

    try:
        t0 = datetime.fromisoformat(sorted_m[0].measured_at)
        points: List[Tuple[float, float]] = []
        for m in sorted_m:
            dt = datetime.fromisoformat(m.measured_at)
            days_diff = (dt - t0).total_seconds() / 86400.0
            points.append((days_diff, m.weight_kg))
    except Exception:
        # Fallback to sequential index
        points = [(float(i), m.weight_kg) for i, m in enumerate(sorted_m)]

    # Outlier detection: day-to-day jump > 2.0 kg
    outlier_count = 0
    for i in range(1, len(points)):
        time_delta_days = max(points[i][0] - points[i - 1][0], 0.5)
        weight_jump = abs(points[i][1] - points[i - 1][1])
        if (weight_jump / time_delta_days) > 2.5:
            outlier_count += 1

    slope = calculate_linear_slope(points)
    threshold = AdaptationEvaluationPolicy.WEIGHT_STABLE_DAILY_SLOPE_THRESHOLD_KG

    if slope > threshold:
        direction = WeightTrendDirection.INCREASING
    elif slope < -threshold:
        direction = WeightTrendDirection.DECREASING
    else:
        direction = WeightTrendDirection.STABLE

    # Confidence derivation
    if len(measurements) >= 4 and outlier_count == 0:
        confidence = EvaluationConfidence.HIGH
    elif len(measurements) >= AdaptationEvaluationPolicy.MIN_WEIGHT_MEASUREMENTS and outlier_count <= 1:
        confidence = EvaluationConfidence.MEDIUM
    elif len(measurements) >= 2:
        confidence = EvaluationConfidence.LOW
    else:
        confidence = EvaluationConfidence.UNKNOWN

    is_interpretable = len(measurements) >= AdaptationEvaluationPolicy.MIN_WEIGHT_MEASUREMENTS and outlier_count <= 1

    return WeightTrendSummaryDTO(
        measurement_count=len(measurements),
        start_weight_kg=round(sorted_m[0].weight_kg, 2),
        end_weight_kg=round(sorted_m[-1].weight_kg, 2),
        slope_kg_per_day=round(slope, 4),
        direction=direction,
        confidence=confidence,
        is_interpretable=is_interpretable,
        outlier_count=outlier_count,
    )
