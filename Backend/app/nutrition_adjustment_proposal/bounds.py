from typing import Tuple, List, Optional
from app.nutrition_adjustment_proposal.constants import (
    ProposalStatus,
    AdjustmentProposalReasonCode,
    RiskFlag,
    ProposalPolicy,
)


def calculate_bounded_energy_adjustment(
    current_target_kcal: int,
    cumulative_adaptive_adjustment_kcal: int = 0,
) -> Tuple[ProposalStatus, int, int, List[AdjustmentProposalReasonCode], List[RiskFlag]]:
    """
    Calculates bounded energy target adjustment using NUTRITION_ENERGY_ADJUSTMENT_V01.
    Returns (status, delta_kcal, proposed_target_kcal, reasons, risks).
    """
    step = int(ProposalPolicy.DEFAULT_ENERGY_ADJUSTMENT_STEP_KCAL)
    new_cumulative = int(cumulative_adaptive_adjustment_kcal) + step

    reasons: List[AdjustmentProposalReasonCode] = []
    risks: List[RiskFlag] = []

    # Check cumulative adaptive limit guardrail
    if new_cumulative > ProposalPolicy.MAX_CUMULATIVE_ADAPTIVE_ADJUSTMENT_KCAL:
        reasons.append(AdjustmentProposalReasonCode.ADAPTIVE_LIMIT_REACHED)
        risks.append(RiskFlag.ADAPTIVE_LIMIT_NEAR)
        return (
            ProposalStatus.ADAPTIVE_LIMIT_REACHED,
            0,
            int(current_target_kcal),
            reasons,
            risks,
        )

    if new_cumulative >= (ProposalPolicy.MAX_CUMULATIVE_ADAPTIVE_ADJUSTMENT_KCAL - step):
        risks.append(RiskFlag.ADAPTIVE_LIMIT_NEAR)

    reasons.extend([
        AdjustmentProposalReasonCode.SUFFICIENT_MULTI_WEEK_EVIDENCE,
        AdjustmentProposalReasonCode.FLAT_WEIGHT_TREND_WITH_HIGH_ADHERENCE,
        AdjustmentProposalReasonCode.ENERGY_TARGET_REVIEW_RECOMMENDED,
    ])

    proposed_target = int(current_target_kcal) + step

    return (
        ProposalStatus.PROPOSAL_READY,
        step,
        proposed_target,
        reasons,
        risks,
    )
