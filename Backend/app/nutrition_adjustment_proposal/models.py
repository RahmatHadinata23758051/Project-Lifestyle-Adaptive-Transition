from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.nutrition_adjustment_proposal.constants import (
    ProposalStatus,
    ProposalLifecycleState,
    ProposalType,
    AdjustmentProposalReasonCode,
    RiskFlag,
    ProposalPolicy,
)
from app.nutrition_adaptation.constants import (
    AdaptationDecision,
    AdjustmentReviewDomain,
    WeightTrendDirection,
    AdherenceContextCategory,
    EvaluationConfidence,
    EvaluationReasonCode,
)
from app.nutrition_adaptation.models import (
    NutritionAdaptationEvaluationResultDTO,
)


class EvidenceSnapshotDTO(BaseModel):
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
    reason_codes: List[EvaluationReasonCode] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class NutritionAdjustmentProposalInputDTO(BaseModel):
    user_id: Optional[str] = None
    evaluation: NutritionAdaptationEvaluationResultDTO
    current_target_energy_kcal: float
    initial_baseline_target_energy_kcal: Optional[float] = None
    cumulative_adaptive_adjustment_kcal: float = 0.0
    nutrition_goal_type: str = "NUTRITION_WEIGHT_GAIN"
    current_eligibility_status: str = "ELIGIBLE"
    last_applied_adjustment_at: Optional[str] = None
    last_evidence_updated_at: Optional[str] = None
    reference_time: Optional[str] = None
    policy_versions: Dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class NutritionAdjustmentProposalDTO(BaseModel):
    proposal_id: str
    status: ProposalStatus
    lifecycle_state: ProposalLifecycleState = ProposalLifecycleState.PENDING
    proposal_type: ProposalType
    current_target_kcal: float
    proposed_target_kcal: float
    delta_kcal: float
    confidence: EvaluationConfidence
    evidence_summary: EvidenceSnapshotDTO
    risk_flags: List[RiskFlag] = Field(default_factory=list)
    reason_codes: List[AdjustmentProposalReasonCode] = Field(default_factory=list)
    explanations: List[str] = Field(default_factory=list)
    fingerprint: str
    created_at: str
    expires_at: str
    resolved_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    requires_user_confirmation: bool = True
    downstream_budget_recheck_required: bool = True
    policy_versions: Dict[str, str] = Field(
        default_factory=lambda: {
            "proposal_policy": ProposalPolicy.VERSION,
            "energy_adjustment_policy": ProposalPolicy.ENERGY_ADJUSTMENT_POLICY,
            "confidence_policy": ProposalPolicy.CONFIDENCE_POLICY,
            "validity_policy": ProposalPolicy.VALIDITY_POLICY,
            "freshness_policy": ProposalPolicy.FRESHNESS_POLICY,
        }
    )

    model_config = ConfigDict(from_attributes=True)
