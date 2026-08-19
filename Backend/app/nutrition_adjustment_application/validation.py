from datetime import datetime, timezone
from typing import Optional, Tuple, List
from app.nutrition_adjustment_application.constants import (
    ApplicationStatus,
    ApplicationReasonCode,
    ApplicationPolicy,
)
from app.nutrition_adjustment_application.models import ApplyNutritionAdjustmentCommand
from app.nutrition_adjustment_proposal.models import NutritionAdjustmentProposalDTO
from app.nutrition_adjustment_proposal.constants import (
    ProposalStatus,
    ProposalLifecycleState,
)


def _to_utc_dt(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        dt = datetime.fromisoformat(val)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def validate_application_prerequisites(
    command: ApplyNutritionAdjustmentCommand,
    command_user_id: str,
    proposal: NutritionAdjustmentProposalDTO,
    proposal_owner_user_id: str,
    current_authoritative_target_kcal: int,
    current_authoritative_revision: int,
    current_cumulative_adaptive_delta_kcal: int,
    current_eligibility_status: str = "ELIGIBLE",
    last_evidence_updated_at: Optional[str] = None,
    reference_time_str: Optional[str] = None,
) -> Tuple[Optional[ApplicationStatus], List[ApplicationReasonCode], List[str]]:
    """
    Pure zero-I/O validation of all application prerequisites before mutation.
    Returns (status, reason_codes, explanations). If valid, status is None.
    """
    reasons: List[ApplicationReasonCode] = []
    explanations: List[str] = []

    # 1. Ownership validation
    if command_user_id != proposal_owner_user_id:
        return (
            ApplicationStatus.OUT_OF_SCOPE,
            [ApplicationReasonCode.PROPOSAL_NOT_ACCEPTED],
            ["Proposal does not belong to the authenticated user."],
        )

    # 2. Proposal Readiness & Lifecycle State
    if proposal.status != ProposalStatus.PROPOSAL_READY:
        return (
            ApplicationStatus.PROPOSAL_NOT_ACCEPTED,
            [ApplicationReasonCode.PROPOSAL_NOT_ACCEPTED],
            [f"Proposal status is '{proposal.status}', which is not ready for application."],
        )

    if proposal.lifecycle_state == ProposalLifecycleState.APPLIED:
        return (
            ApplicationStatus.ALREADY_APPLIED,
            [ApplicationReasonCode.IDEMPOTENT_REPLAY],
            ["Proposal has already been applied."],
        )

    if proposal.lifecycle_state != ProposalLifecycleState.ACCEPTED:
        return (
            ApplicationStatus.PROPOSAL_NOT_ACCEPTED,
            [ApplicationReasonCode.PROPOSAL_NOT_ACCEPTED],
            [f"Proposal lifecycle state is '{proposal.lifecycle_state}', but must be 'ACCEPTED' to apply."],
        )

    # 3. Expiration Check at Apply Time
    ref_dt = _to_utc_dt(reference_time_str) or datetime.now(timezone.utc)
    if proposal.expires_at:
        exp_dt = _to_utc_dt(proposal.expires_at)
        if exp_dt and ref_dt > exp_dt:
            return (
                ApplicationStatus.PROPOSAL_EXPIRED,
                [ApplicationReasonCode.PROPOSAL_EXPIRED],
                ["Proposal validity window has expired before application."],
            )

    # 4. Clinical Safety Eligibility Recheck
    norm_elig = str(current_eligibility_status).upper().strip()
    if any(k in norm_elig for k in ("OUT_OF_SCOPE", "NOT_ELIGIBLE", "BLOCKED")):
        return (
            ApplicationStatus.ELIGIBILITY_CHANGED,
            [ApplicationReasonCode.ELIGIBILITY_CHANGED],
            ["Current nutrition safety eligibility has changed; application is blocked."],
        )

    # 5. Domain and Goal Gates
    if getattr(proposal, "proposal_domain", "ENERGY_TARGET") != ApplicationPolicy.SUPPORTED_DOMAIN:
        return (
            ApplicationStatus.OUT_OF_SCOPE,
            [ApplicationReasonCode.UNSUPPORTED_POLICY_VERSION],
            [f"Unsupported proposal domain: {getattr(proposal, 'proposal_domain', 'UNKNOWN')}"],
        )

    # 6. Proposal Arithmetic Integrity Verification
    if (proposal.proposed_target_kcal - proposal.current_target_kcal) != proposal.delta_kcal:
        return (
            ApplicationStatus.PROPOSAL_STALE,
            [ApplicationReasonCode.ARITHMETIC_CORRUPTION],
            ["Proposal delta does not match proposed minus current target arithmetic."],
        )

    if proposal.delta_kcal <= 0 or proposal.delta_kcal > ApplicationPolicy.MAX_SINGLE_ENERGY_ADJUSTMENT_KCAL:
        return (
            ApplicationStatus.PROPOSAL_STALE,
            [ApplicationReasonCode.ARITHMETIC_CORRUPTION],
            [f"Proposal delta {proposal.delta_kcal} kcal is outside allowed bounds (0, {ApplicationPolicy.MAX_SINGLE_ENERGY_ADJUSTMENT_KCAL}]."],
        )

    # 7. Target Conflict Gate (Authoritative Target vs Proposal Source Target vs Command Target)
    if int(current_authoritative_target_kcal) != int(proposal.current_target_kcal):
        return (
            ApplicationStatus.TARGET_CONFLICT,
            [ApplicationReasonCode.TARGET_CONFLICT],
            [f"Current authoritative target ({current_authoritative_target_kcal} kcal) does not match proposal source target ({proposal.current_target_kcal} kcal)."],
        )

    if int(command.expected_current_target_kcal) != int(proposal.current_target_kcal):
        return (
            ApplicationStatus.TARGET_CONFLICT,
            [ApplicationReasonCode.TARGET_CONFLICT],
            [f"Client expected target ({command.expected_current_target_kcal} kcal) does not match authoritative proposal target ({proposal.current_target_kcal} kcal)."],
        )

    # 8. State Revision Conflict Gate
    if int(current_authoritative_revision) != int(command.expected_state_revision):
        return (
            ApplicationStatus.REVISION_CONFLICT,
            [ApplicationReasonCode.REVISION_CONFLICT],
            [f"Current authoritative nutrition state revision ({current_authoritative_revision}) does not match expected revision ({command.expected_state_revision})."],
        )

    # 9. Cumulative Adaptive Ceiling Guardrail Recheck
    new_cumulative = int(current_cumulative_adaptive_delta_kcal) + int(proposal.delta_kcal)
    if new_cumulative > ApplicationPolicy.MAX_CUMULATIVE_ADAPTIVE_ADJUSTMENT_KCAL:
        return (
            ApplicationStatus.ADAPTIVE_LIMIT_REACHED,
            [ApplicationReasonCode.ADAPTIVE_LIMIT_REACHED],
            [f"Applying this proposal would result in cumulative adjustment of {new_cumulative} kcal, exceeding the maximum limit of {ApplicationPolicy.MAX_CUMULATIVE_ADAPTIVE_ADJUSTMENT_KCAL} kcal."],
        )

    # 10. Evidence Watermark Freshness Recheck
    if last_evidence_updated_at and proposal.created_at:
        evid_dt = _to_utc_dt(last_evidence_updated_at)
        prop_dt = _to_utc_dt(proposal.created_at)
        if evid_dt and prop_dt and evid_dt > prop_dt:
            return (
                ApplicationStatus.EVIDENCE_CHANGED,
                [ApplicationReasonCode.EVIDENCE_CHANGED],
                ["New check-in or weight measurements have been logged since proposal generation. A fresh evaluation is required."],
            )

    return None, [], []
