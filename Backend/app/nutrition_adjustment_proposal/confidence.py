from typing import Tuple, List, Optional
from app.nutrition_adjustment_proposal.constants import (
    ProposalStatus,
    AdjustmentProposalReasonCode,
    RiskFlag,
)
from app.nutrition_adaptation.constants import (
    EvaluationConfidence,
)
from app.nutrition_adaptation.models import NutritionAdaptationEvaluationResultDTO


def evaluate_proposal_confidence_gate(
    evaluation: NutritionAdaptationEvaluationResultDTO,
) -> Tuple[Optional[ProposalStatus], List[AdjustmentProposalReasonCode], List[RiskFlag]]:
    """
    Enforces NUTRITION_ADJUSTMENT_CONFIDENCE_V01:
    Requires both evaluation and weight trend confidence to be HIGH or MEDIUM, and trend must be interpretable.
    """
    reasons: List[AdjustmentProposalReasonCode] = []
    risks: List[RiskFlag] = []

    if evaluation.confidence not in (EvaluationConfidence.HIGH, EvaluationConfidence.MEDIUM):
        reasons.append(AdjustmentProposalReasonCode.LOW_EVALUATION_CONFIDENCE)

    if (
        evaluation.weight_trend.confidence not in (EvaluationConfidence.HIGH, EvaluationConfidence.MEDIUM)
        or not evaluation.weight_trend.is_interpretable
    ):
        reasons.append(AdjustmentProposalReasonCode.LOW_WEIGHT_TREND_CONFIDENCE)
        risks.append(RiskFlag.LOW_WEIGHT_TREND_CONFIDENCE)

    if reasons:
        return ProposalStatus.BLOCKED_BY_CONFIDENCE, reasons, risks

    return None, [], []
