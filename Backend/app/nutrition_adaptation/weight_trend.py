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


def calculate_linear_regression(points: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Computes standard ordinary least squares linear regression slope and intercept:
    y = intercept + slope * x
    """
    n = len(points)
    if n < 2:
        return 0.0, points[0][1] if points else 0.0

    mean_x = sum(p[0] for p in points) / n
    mean_y = sum(p[1] for p in points) / n

    numerator = sum((p[0] - mean_x) * (p[1] - mean_y) for p in points)
    denominator = sum((p[0] - mean_x) ** 2 for p in points)

    if denominator == 0.0:
        return 0.0, mean_y

    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    return slope, intercept


def evaluate_measurement_context_consistency(measurements: List[WeightObservationDTO]) -> Tuple[bool, bool]:
    """
    Evaluates whether measurements were taken under compatible context (e.g., wake morning vs post-meal).
    Returns (is_consistent, is_severely_inconsistent).
    """
    contexts = [m.context.upper().strip() for m in measurements if m.context]
    if not contexts or len(contexts) < 2:
        # If context not specified, treat as neutral/unknown without severe penalty
        return True, False

    from collections import Counter
    counts = Counter(contexts)
    most_common_count = counts.most_common(1)[0][1]
    ratio = most_common_count / len(contexts)

    if ratio >= 0.75:
        return True, False
    elif ratio >= 0.50:
        return False, False  # Mixed context, moderate penalty
    else:
        return False, True   # Severely inconsistent context


def evaluate_weight_trend(measurements: List[WeightObservationDTO]) -> WeightTrendSummaryDTO:
    """
    Evaluates weight trend slope, direction, interpretability, and confidence using
    WEIGHT_TREND_CLASSIFICATION_V01, residual outlier detection, and measurement context consistency.
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
        points = [(float(i), m.weight_kg) for i, m in enumerate(sorted_m)]

    slope, intercept = calculate_linear_regression(points)

    # Residual-based and gap-aware outlier detection
    outlier_count = 0
    residuals = [abs(p[1] - (intercept + slope * p[0])) for p in points]
    for r in residuals:
        if r > 2.0:  # Deviates > 2.0 kg from linear trendline
            outlier_count += 1

    # Also detect short-interval (< 36 hours) extreme jump (> 2.0 kg)
    for i in range(1, len(points)):
        delta_t_days = points[i][0] - points[i - 1][0]
        delta_w = abs(points[i][1] - points[i - 1][1])
        if delta_t_days <= 1.5 and delta_w > 2.0:
            if residuals[i] <= 2.0 and residuals[i - 1] <= 2.0:
                outlier_count += 1

    threshold = AdaptationEvaluationPolicy.WEIGHT_STABLE_DAILY_SLOPE_THRESHOLD_KG

    if slope > threshold:
        direction = WeightTrendDirection.INCREASING
    elif slope < -threshold:
        direction = WeightTrendDirection.DECREASING
    else:
        direction = WeightTrendDirection.STABLE

    # Context consistency evaluation
    is_consistent_context, is_severely_inconsistent = evaluate_measurement_context_consistency(sorted_m)

    # Confidence derivation
    if is_severely_inconsistent:
        confidence = EvaluationConfidence.LOW
        is_interpretable = False
    elif len(measurements) >= AdaptationEvaluationPolicy.MIN_ADJUSTMENT_WEIGHT_MEASUREMENTS and outlier_count == 0 and is_consistent_context:
        confidence = EvaluationConfidence.HIGH
        is_interpretable = True
    elif len(measurements) >= AdaptationEvaluationPolicy.MIN_WEIGHT_MEASUREMENTS and outlier_count <= 1:
        confidence = EvaluationConfidence.MEDIUM
        is_interpretable = True
    elif len(measurements) >= 2:
        confidence = EvaluationConfidence.LOW
        is_interpretable = False
    else:
        confidence = EvaluationConfidence.UNKNOWN
        is_interpretable = False

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
