from app.nutrition_adaptation.constants import (
    EvaluationConfidence,
    DataSufficiencyStatus,
)
from app.nutrition_adaptation.models import (
    DataSufficiencyDTO,
    AdherencePatternSummaryDTO,
    WeightTrendSummaryDTO,
)


def derive_overall_evaluation_confidence(
    sufficiency: DataSufficiencyDTO,
    adherence: AdherencePatternSummaryDTO,
    trend: WeightTrendSummaryDTO,
) -> EvaluationConfidence:
    """
    Synthesizes overall evaluation confidence categorically without false precision.
    """
    if sufficiency.status == DataSufficiencyStatus.INSUFFICIENT:
        return EvaluationConfidence.LOW

    if sufficiency.status == DataSufficiencyStatus.SUFFICIENT and trend.confidence == EvaluationConfidence.HIGH and adherence.confidence == EvaluationConfidence.HIGH:
        return EvaluationConfidence.HIGH

    if sufficiency.status in (DataSufficiencyStatus.SUFFICIENT, DataSufficiencyStatus.PARTIAL) and trend.confidence in (EvaluationConfidence.HIGH, EvaluationConfidence.MEDIUM):
        return EvaluationConfidence.MEDIUM

    return EvaluationConfidence.LOW
