from typing import Tuple, List, Optional
from app.nutrition_adjustment_proposal.constants import (
    ProposalStatus,
    AdjustmentProposalReasonCode,
)
from app.nutrition_adaptation.constants import (
    AdaptationDecision,
    AdjustmentReviewDomain,
    DataSufficiencyStatus,
)
from app.nutrition_adaptation.models import NutritionAdaptationEvaluationResultDTO


def evaluate_proposal_eligibility_and_decision_gate(
    evaluation: NutritionAdaptationEvaluationResultDTO,
    current_eligibility_status: str,
    goal_type: str,
) -> Tuple[Optional[ProposalStatus], List[AdjustmentProposalReasonCode]]:
    """
    Validates upstream P1.7 evaluation decision, review domain, data sufficiency, and clinical safety eligibility.
    Returns (None, []) if gate passes, or (blocked_status, reason_codes) if blocked.
    """
    # 1. Safety & Clinical Eligibility Gate
    norm_elig = str(current_eligibility_status).upper().strip()
    if any(k in norm_elig for k in ("OUT_OF_SCOPE", "NOT_ELIGIBLE", "BLOCKED")):
        return ProposalStatus.OUT_OF_SCOPE, [AdjustmentProposalReasonCode.ELIGIBILITY_NOT_VALID]

    # 2. Supported Goal Gate (v0.1: NUTRITION_WEIGHT_GAIN)
    if "WEIGHT_GAIN" not in str(goal_type).upper():
        return ProposalStatus.OUT_OF_SCOPE, [AdjustmentProposalReasonCode.UNSUPPORTED_GOAL]

    # 3. Upstream Decision Gate
    if evaluation.decision != AdaptationDecision.CONSIDER_ADJUSTMENT:
        return ProposalStatus.NO_PROPOSAL_NEEDED, []

    # 4. Review Domain Gate
    if evaluation.review_domain != AdjustmentReviewDomain.ENERGY_TARGET_REVIEW:
        return ProposalStatus.UNSUPPORTED_REVIEW_DOMAIN, [AdjustmentProposalReasonCode.UNSUPPORTED_REVIEW_DOMAIN]

    # 5. Data Sufficiency Gate
    if evaluation.data_sufficiency.status != DataSufficiencyStatus.SUFFICIENT:
        return ProposalStatus.NEEDS_MORE_DATA, [AdjustmentProposalReasonCode.INSUFFICIENT_EVALUATION_WINDOW]

    return None, []
