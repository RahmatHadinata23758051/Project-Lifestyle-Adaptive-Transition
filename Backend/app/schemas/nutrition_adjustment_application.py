from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.nutrition_adjustment_application.constants import (
    ApplicationStatus,
    StateRevisionSourceType,
    ApplicationReasonCode,
)


class ApplyNutritionAdjustmentRequest(BaseModel):
    expected_current_target_kcal: int
    expected_state_revision: int
    idempotency_key: str
    current_eligibility_status: Optional[str] = "ELIGIBLE"
    last_evidence_updated_at: Optional[str] = None
    reference_time: Optional[str] = None


class DownstreamInvalidationResponse(BaseModel):
    source_revision: int
    target_revision: int
    meal_structure_invalidated: bool = True
    food_candidates_invalidated: bool = True
    budget_selection_invalidated: bool = True
    daily_plan_invalidated: bool = True
    requires_downstream_regeneration: bool = True
    reason: str

    model_config = ConfigDict(from_attributes=True)


class NutritionAdjustmentApplicationResponse(BaseModel):
    application_id: str
    proposal_id: str
    status: ApplicationStatus
    previous_target_kcal: int
    applied_target_kcal: int
    delta_kcal: int
    previous_state_revision: int
    new_state_revision: int
    downstream_invalidation: DownstreamInvalidationResponse
    applied_at: str
    audit_reference: str
    reason_codes: List[ApplicationReasonCode] = []
    explanations: List[str] = []
    policy_versions: Dict[str, str] = {}

    model_config = ConfigDict(from_attributes=True)


class NutritionStateRevisionResponse(BaseModel):
    id: str
    owner_user_id: str
    revision_number: int
    previous_revision_id: Optional[str] = None
    source_type: str
    source_reference_id: Optional[str] = None
    target_energy_kcal: int
    goal_type: str
    effective_from: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
