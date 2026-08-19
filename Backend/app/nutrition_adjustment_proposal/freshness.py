from datetime import datetime, timezone
from typing import Tuple, List, Optional
from app.nutrition_adjustment_proposal.constants import (
    ProposalStatus,
    AdjustmentProposalReasonCode,
    RiskFlag,
    ProposalPolicy,
)


def evaluate_freshness_and_cooldown_gate(
    evaluated_at_str: str,
    last_applied_adjustment_at: Optional[str] = None,
    last_evidence_updated_at: Optional[str] = None,
    reference_time_str: Optional[str] = None,
) -> Tuple[Optional[ProposalStatus], List[AdjustmentProposalReasonCode], List[RiskFlag]]:
    """
    Enforces NUTRITION_EVALUATION_FRESHNESS_V01 and adaptation cooldown.
    """
    reasons: List[AdjustmentProposalReasonCode] = []
    risks: List[RiskFlag] = []

    ref_dt = datetime.fromisoformat(reference_time_str) if reference_time_str else datetime.now(timezone.utc)

    # 1. Cooldown Re-check
    if last_applied_adjustment_at:
        try:
            last_adj_dt = datetime.fromisoformat(last_applied_adjustment_at)
            days_since = (ref_dt - last_adj_dt).total_seconds() / 86400.0
            if days_since < ProposalPolicy.COOLDOWN_DAYS:
                reasons.append(AdjustmentProposalReasonCode.COOLDOWN_ACTIVE)
                risks.append(RiskFlag.COOLDOWN_ACTIVE)
                return ProposalStatus.BLOCKED_BY_COOLDOWN, reasons, risks
        except Exception:
            pass

    # 2. Evaluation Freshness Check (New Evidence invalidates old evaluation)
    if last_evidence_updated_at and evaluated_at_str:
        try:
            eval_dt = datetime.fromisoformat(evaluated_at_str)
            evid_dt = datetime.fromisoformat(last_evidence_updated_at)
            if evid_dt > eval_dt:
                reasons.append(AdjustmentProposalReasonCode.NEW_EVIDENCE_AVAILABLE)
                risks.append(RiskFlag.NEW_EVIDENCE_AVAILABLE)
                return ProposalStatus.NEEDS_NEW_EVALUATION, reasons, risks
        except Exception:
            pass

    return None, [], []
