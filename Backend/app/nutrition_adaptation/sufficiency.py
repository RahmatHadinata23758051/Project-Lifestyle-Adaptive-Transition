from typing import List
from app.nutrition_adaptation.constants import (
    DataSufficiencyStatus,
    AdaptationEvaluationPolicy,
)
from app.nutrition_adaptation.models import (
    EvidenceWindowDTO,
    DataSufficiencyDTO,
)


def evaluate_data_sufficiency(window: EvidenceWindowDTO) -> DataSufficiencyDTO:
    """
    Evaluates whether evidence window satisfies minimum observation thresholds.
    """
    reasons: List[str] = []

    if window.total_days < AdaptationEvaluationPolicy.MIN_EVALUATION_DAYS:
        reasons.append(
            f"Observation window ({window.total_days} days) is less than policy minimum ({AdaptationEvaluationPolicy.MIN_EVALUATION_DAYS} days)."
        )

    if window.usable_adherence_days < AdaptationEvaluationPolicy.MIN_USABLE_ADHERENCE_DAYS:
        reasons.append(
            f"Usable adherence days ({window.usable_adherence_days}) is less than policy minimum ({AdaptationEvaluationPolicy.MIN_USABLE_ADHERENCE_DAYS})."
        )

    if window.weight_measurement_count < AdaptationEvaluationPolicy.MIN_WEIGHT_MEASUREMENTS:
        reasons.append(
            f"Weight measurements count ({window.weight_measurement_count}) is less than policy minimum ({AdaptationEvaluationPolicy.MIN_WEIGHT_MEASUREMENTS})."
        )

    if not reasons:
        return DataSufficiencyDTO(
            status=DataSufficiencyStatus.SUFFICIENT,
            usable_days_count=window.usable_adherence_days,
            weight_count=window.weight_measurement_count,
            is_sufficient=True,
            reasons=[],
        )
    elif window.usable_adherence_days >= 3 and window.weight_measurement_count >= 2:
        return DataSufficiencyDTO(
            status=DataSufficiencyStatus.PARTIAL,
            usable_days_count=window.usable_adherence_days,
            weight_count=window.weight_measurement_count,
            is_sufficient=False,
            reasons=reasons,
        )
    else:
        return DataSufficiencyDTO(
            status=DataSufficiencyStatus.INSUFFICIENT,
            usable_days_count=window.usable_adherence_days,
            weight_count=window.weight_measurement_count,
            is_sufficient=False,
            reasons=reasons,
        )
