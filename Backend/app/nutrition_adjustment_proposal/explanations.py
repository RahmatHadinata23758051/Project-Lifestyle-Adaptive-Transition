from typing import List
from app.nutrition_adjustment_proposal.constants import (
    ProposalStatus,
    AdjustmentProposalReasonCode,
)


def generate_proposal_explanations(
    status: ProposalStatus,
    current_target_kcal: float,
    proposed_target_kcal: float,
    delta_kcal: float,
    reason_codes: List[AdjustmentProposalReasonCode],
) -> List[str]:
    """
    Generates deterministic, non-judgmental explanations for proposal status and proposed change.
    """
    explanations: List[str] = []

    if status == ProposalStatus.PROPOSAL_READY:
        explanations.append(
            f"Recent multi-week evidence is sufficiently complete, reported adherence is consistently high, and weight trend remains stable. "
            f"Chronos proposes adjusting your daily planning target by +{int(delta_kcal)} kcal/day (from {int(current_target_kcal)} to {int(proposed_target_kcal)} kcal/day)."
        )
        explanations.append("This is a bounded planning proposal and will not be applied without your explicit confirmation.")

    elif status == ProposalStatus.BLOCKED_BY_CONFIDENCE:
        explanations.append("Recent weight measurements or evaluation evidence do not meet the confidence threshold required for an adjustment proposal.")

    elif status == ProposalStatus.BLOCKED_BY_COOLDOWN:
        explanations.append("A previous target adjustment was applied recently. Adaptation cooldown is active to allow your body and lifestyle to stabilize.")

    elif status == ProposalStatus.UNSUPPORTED_REVIEW_DOMAIN:
        explanations.append("Recent deviation patterns appear related to non-energy factors (e.g., food cost, meal availability, or scheduling) rather than a calorie target mismatch.")

    elif status == ProposalStatus.ADAPTIVE_LIMIT_REACHED:
        explanations.append(f"Cumulative adaptive adjustment limit has been reached (+{int(delta_kcal)} kcal). Further automated increases are paused for safety.")

    elif status == ProposalStatus.NEEDS_NEW_EVALUATION:
        explanations.append("New adherence or weight data was logged after the last evaluation. A fresh evaluation is required before proposing changes.")

    elif status == ProposalStatus.OUT_OF_SCOPE:
        explanations.append("User is outside supported automated nutrition adaptation scope.")

    elif status == ProposalStatus.NO_PROPOSAL_NEEDED:
        explanations.append("Current plan is progressing well and no target adjustment proposal is needed at this time.")

    return explanations
