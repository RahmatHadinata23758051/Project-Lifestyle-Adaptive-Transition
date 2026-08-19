from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, ConfigDict
from app.nutrition_adjustment_proposal.constants import (
    ProposalStatus,
    ProposalLifecycleState,
    ProposalType,
    AdjustmentProposalReasonCode,
    RiskFlag,
)
from app.nutrition_adaptation.constants import (
    AdaptationDecision,
    AdjustmentReviewDomain,
    WeightTrendDirection,
    AdherenceContextCategory,
    EvaluationConfidence,
    EvaluationReasonCode,
)
from app.schemas.nutrition_adaptation import NutritionAdaptationEvaluationResponse


class EvidenceSnapshotResponse(BaseModel):
    evaluation_id: str
    decision: AdaptationDecision
    review_domain: AdjustmentReviewDomain
    evaluation_confidence: EvaluationConfidence
    weight_trend_direction: WeightTrendDirection
    weight_trend_confidence: EvaluationConfidence
    slope_kg_per_day: Optional[float] = None
    usable_days: int
    weight_measurements_count: int
    adherence_category: AdherenceContextCategory
    reason_codes: List[EvaluationReasonCode] = []


class NutritionAdjustmentProposalRequest(BaseModel):
    evaluation: NutritionAdaptationEvaluationResponse
    current_target_energy_kcal: int
    initial_baseline_target_energy_kcal: Optional[int] = None
    cumulative_adaptive_adjustment_kcal: int = 0
    nutrition_goal_type: str = "NUTRITION_WEIGHT_GAIN"
    current_eligibility_status: str = "ELIGIBLE"
    last_applied_adjustment_at: Optional[str] = None
    last_evidence_updated_at: Optional[str] = None
    reference_time: Optional[str] = None


class AcceptProposalRequest(BaseModel):
    current_target_energy_kcal: Optional[int] = None
    current_eligibility_status: Optional[str] = None
    last_evidence_updated_at: Optional[str] = None


class RejectProposalRequest(BaseModel):
    rejection_reason: Optional[str] = None


class NutritionAdjustmentProposalResponse(BaseModel):
    proposal_id: str
    proposal_domain: str = "ENERGY_TARGET"
    status: ProposalStatus
    lifecycle_state: ProposalLifecycleState
    proposal_type: ProposalType
    current_target_kcal: int
    proposed_target_kcal: int
    delta_kcal: int
    confidence: EvaluationConfidence
    evidence_summary: Optional[Union[EvidenceSnapshotResponse, Dict[str, Any]]] = None
    risk_flags: List[RiskFlag] = []
    reason_codes: List[AdjustmentProposalReasonCode] = []
    explanations: List[str] = []
    fingerprint: str
    created_at: str
    expires_at: str
    resolved_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    requires_user_confirmation: bool = True
    downstream_budget_recheck_required: bool = True
    policy_versions: Dict[str, str] = {}

    model_config = ConfigDict(from_attributes=True)
