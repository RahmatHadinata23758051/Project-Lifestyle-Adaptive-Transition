from typing import Optional, Tuple
from app.nutrition_adjustment_application.constants import (
    ApplicationStatus,
    ApplicationReasonCode,
)
from app.nutrition_adjustment_application.models import (
    ApplyNutritionAdjustmentCommand,
    NutritionAdjustmentApplicationResultDTO,
)


def evaluate_idempotent_replay(
    command: ApplyNutritionAdjustmentCommand,
    existing_application_by_proposal: Optional[NutritionAdjustmentApplicationResultDTO],
    existing_application_by_idempotency_key: Optional[NutritionAdjustmentApplicationResultDTO],
) -> Tuple[Optional[ApplicationStatus], Optional[NutritionAdjustmentApplicationResultDTO], Optional[ApplicationReasonCode]]:
    """
    Evaluates idempotency without side effects:
    1. If the proposal has already been applied:
       - If the idempotency key matches: safe idempotent replay (ALREADY_APPLIED).
       - If the idempotency key differs: proposal was already applied via a different request (ALREADY_APPLIED).
    2. If the idempotency key was used for a DIFFERENT proposal: IDEMPOTENCY_CONFLICT.
    3. If new apply: returns (None, None, None).
    """
    # Check if idempotency key was previously bound to another proposal
    if (
        existing_application_by_idempotency_key is not None
        and existing_application_by_idempotency_key.proposal_id != command.proposal_id
    ):
        return (
            ApplicationStatus.IDEMPOTENCY_CONFLICT,
            None,
            ApplicationReasonCode.IDEMPOTENCY_KEY_MISMATCH,
        )

    # Check if proposal has already been applied
    if existing_application_by_proposal is not None:
        return (
            ApplicationStatus.ALREADY_APPLIED,
            existing_application_by_proposal,
            ApplicationReasonCode.IDEMPOTENT_REPLAY,
        )

    return None, None, None
