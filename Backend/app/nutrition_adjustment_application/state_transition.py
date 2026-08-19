import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple
from app.nutrition_adjustment_application.constants import (
    ApplicationStatus,
    StateRevisionSourceType,
    ApplicationReasonCode,
)
from app.nutrition_adjustment_application.models import (
    ApplyNutritionAdjustmentCommand,
    NutritionStateRevisionDTO,
    NutritionAdjustmentApplicationResultDTO,
)
from app.nutrition_adjustment_proposal.models import NutritionAdjustmentProposalDTO
from app.nutrition_adjustment_application.invalidation import build_downstream_invalidation
from app.nutrition_adjustment_application.audit import generate_audit_reference


def build_applied_state_transition(
    command: ApplyNutritionAdjustmentCommand,
    proposal: NutritionAdjustmentProposalDTO,
    owner_user_id: str,
    previous_revision_number: int,
    previous_revision_id: Optional[str] = None,
    reference_time_str: Optional[str] = None,
) -> Tuple[NutritionStateRevisionDTO, NutritionAdjustmentApplicationResultDTO]:
    """
    Pure zero-I/O transition builder creating the new immutable state revision DTO
    and the application record DTO.
    """
    app_id = f"app_{uuid.uuid4().hex[:16]}"
    rev_id = f"rev_{uuid.uuid4().hex[:16]}"
    new_revision_number = int(previous_revision_number) + 1

    ref_dt = (
        datetime.fromisoformat(reference_time_str)
        if reference_time_str
        else datetime.now(timezone.utc)
    )
    applied_at_str = ref_dt.isoformat()

    # 1. Build new immutable state revision
    new_revision = NutritionStateRevisionDTO(
        id=rev_id,
        owner_user_id=owner_user_id,
        revision_number=new_revision_number,
        previous_revision_id=previous_revision_id,
        source_type=StateRevisionSourceType.USER_CONFIRMED_ADJUSTMENT,
        source_reference_id=proposal.proposal_id,
        target_energy_kcal=int(proposal.proposed_target_kcal),
        goal_type="NUTRITION_WEIGHT_GAIN",
        effective_from=applied_at_str,
        created_at=applied_at_str,
    )

    # 2. Build downstream invalidation descriptor
    invalidation_dto = build_downstream_invalidation(
        source_revision=previous_revision_number,
        target_revision=new_revision_number,
    )

    # 3. Generate cryptographic audit reference
    audit_ref = generate_audit_reference(
        owner_user_id=owner_user_id,
        proposal_id=proposal.proposal_id,
        previous_revision=previous_revision_number,
        new_revision=new_revision_number,
        applied_at=applied_at_str,
    )

    # 4. Build application result DTO
    application_result = NutritionAdjustmentApplicationResultDTO(
        application_id=app_id,
        proposal_id=proposal.proposal_id,
        status=ApplicationStatus.APPLIED,
        previous_target_kcal=int(proposal.current_target_kcal),
        applied_target_kcal=int(proposal.proposed_target_kcal),
        delta_kcal=int(proposal.delta_kcal),
        previous_state_revision=previous_revision_number,
        new_state_revision=new_revision_number,
        downstream_invalidation=invalidation_dto,
        applied_at=applied_at_str,
        audit_reference=audit_ref,
        reason_codes=[ApplicationReasonCode.USER_CONFIRMED_ENERGY_INCREASE],
        explanations=[
            f"Successfully applied confirmed +{proposal.delta_kcal} kcal energy target adjustment ({proposal.current_target_kcal} -> {proposal.proposed_target_kcal} kcal/day).",
            "Downstream meal plan artifacts have been marked stale and will be regenerated under the new nutrition revision.",
        ],
    )

    return new_revision, application_result
