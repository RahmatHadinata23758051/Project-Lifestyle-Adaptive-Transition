from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.nutrition_adjustment_application.constants import (
    ApplicationStatus,
    StateRevisionSourceType,
    ApplicationReasonCode,
    ApplicationPolicy,
)
from app.nutrition_adjustment_proposal.models import NutritionAdjustmentProposalDTO


class DownstreamInvalidationDTO(BaseModel):
    source_revision: int
    target_revision: int
    meal_structure_invalidated: bool = True
    food_candidates_invalidated: bool = True
    budget_selection_invalidated: bool = True
    daily_plan_invalidated: bool = True
    requires_downstream_regeneration: bool = True
    reason: str = "Energy target mutated; downstream plan artifacts are stale and require regeneration."

    model_config = ConfigDict(from_attributes=True)


class ApplyNutritionAdjustmentCommand(BaseModel):
    proposal_id: str
    expected_current_target_kcal: int
    expected_state_revision: int
    idempotency_key: str
    reference_time: Optional[str] = None
    policy_versions: Dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class NutritionStateRevisionDTO(BaseModel):
    id: str
    owner_user_id: str
    revision_number: int
    previous_revision_id: Optional[str] = None
    source_type: StateRevisionSourceType = StateRevisionSourceType.USER_CONFIRMED_ADJUSTMENT
    source_reference_id: Optional[str] = None
    target_energy_kcal: int
    goal_type: str = "NUTRITION_WEIGHT_GAIN"
    effective_from: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class NutritionAdjustmentApplicationResultDTO(BaseModel):
    application_id: str
    proposal_id: str
    status: ApplicationStatus
    previous_target_kcal: int
    applied_target_kcal: int
    delta_kcal: int
    previous_state_revision: int
    new_state_revision: int
    downstream_invalidation: DownstreamInvalidationDTO
    applied_at: str
    audit_reference: str
    reason_codes: List[ApplicationReasonCode] = Field(default_factory=list)
    explanations: List[str] = Field(default_factory=list)
    policy_versions: Dict[str, str] = Field(
        default_factory=lambda: {
            "application_policy": ApplicationPolicy.VERSION,
            "revision_policy": ApplicationPolicy.REVISION_POLICY,
            "invalidation_policy": ApplicationPolicy.INVALIDATION_POLICY,
            "idempotency_policy": ApplicationPolicy.IDEMPOTENCY_POLICY,
        }
    )

    model_config = ConfigDict(from_attributes=True)
