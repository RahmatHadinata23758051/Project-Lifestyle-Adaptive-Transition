from typing import List
from app.nutrition_adaptation.constants import (
    AdherenceContextCategory,
    EvaluationConfidence,
)
from app.nutrition_adaptation.models import (
    NutritionEvidenceDayDTO,
    AdherencePatternSummaryDTO,
)
from app.nutrition_adherence.constants import ReportingCompleteness, MealCompletionState


def evaluate_adherence_context(days: List[NutritionEvidenceDayDTO]) -> AdherencePatternSummaryDTO:
    """
    Evaluates multi-day adherence pattern without punitive framing.
    """
    if not days:
        return AdherencePatternSummaryDTO(
            category=AdherenceContextCategory.INSUFFICIENT_REPORTING,
            reporting_coverage_ratio=0.0,
            full_completion_ratio=0.0,
            confidence=EvaluationConfidence.UNKNOWN,
        )

    total_days = len(days)
    reported_days = sum(1 for d in days if d.reporting_completeness in (ReportingCompleteness.COMPLETE, ReportingCompleteness.PARTIAL))
    reporting_ratio = reported_days / total_days

    total_meals = 0
    full_meals = 0
    for d in days:
        full_meals += d.meal_completion_counts.get("FULL", 0) + d.meal_completion_counts.get(MealCompletionState.FULL.value, 0)
        for state_key, count in d.meal_completion_counts.items():
            total_meals += count

    full_ratio = (full_meals / total_meals) if total_meals > 0 else (1.0 if reporting_ratio >= 0.8 else 0.0)

    if reporting_ratio < 0.5:
        category = AdherenceContextCategory.INSUFFICIENT_REPORTING
        confidence = EvaluationConfidence.LOW
    elif reporting_ratio >= 0.75 and full_ratio >= 0.7:
        category = AdherenceContextCategory.HIGH_CONFIDENCE_ADHERENCE
        confidence = EvaluationConfidence.HIGH
    elif full_ratio < 0.4:
        category = AdherenceContextCategory.LOW_ADHERENCE
        confidence = EvaluationConfidence.MEDIUM
    else:
        category = AdherenceContextCategory.MIXED_ADHERENCE
        confidence = EvaluationConfidence.MEDIUM

    return AdherencePatternSummaryDTO(
        category=category,
        reporting_coverage_ratio=round(reporting_ratio, 2),
        full_completion_ratio=round(full_ratio, 2),
        confidence=confidence,
    )
