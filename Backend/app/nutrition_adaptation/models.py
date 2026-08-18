from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.nutrition_adaptation.constants import (
    AdaptationDecision,
    AdjustmentReviewDomain,
    DataSufficiencyStatus,
    WeightTrendDirection,
    AdherenceContextCategory,
    EvaluationConfidence,
    DayEvidenceQuality,
    EvaluationReasonCode,
    AdaptationEvaluationPolicy,
)
from app.nutrition_adherence.constants import (
    ReportingCompleteness,
    DeviationReason,
    MealCompletionState,
)
from app.daily_nutrition_plan.constants import MacroCompleteness, DailyPlanStatus
from app.meal_structure.constants import MealStructureState


class WeightObservationDTO(BaseModel):
    measured_at: str
    weight_kg: float
    source: str = "USER_LOG"
    context: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NutritionEvidenceDayDTO(BaseModel):
    logical_day_id: str
    date: str
    plan_status: DailyPlanStatus = DailyPlanStatus.READY
    reporting_completeness: ReportingCompleteness
    nutrition_completeness: MacroCompleteness
    planned_energy_kcal: float
    actual_energy_kcal: Optional[float] = None
    meal_completion_counts: Dict[str, int] = Field(default_factory=dict)
    deviation_reasons: List[DeviationReason] = Field(default_factory=list)
    evidence_quality: DayEvidenceQuality

    model_config = ConfigDict(from_attributes=True)


class EvidenceWindowDTO(BaseModel):
    start_date: str
    end_date: str
    total_days: int
    usable_adherence_days: int
    weight_measurement_count: int

    model_config = ConfigDict(from_attributes=True)


class DataSufficiencyDTO(BaseModel):
    status: DataSufficiencyStatus
    usable_days_count: int
    weight_count: int
    is_sufficient: bool
    reasons: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class WeightTrendSummaryDTO(BaseModel):
    measurement_count: int
    start_weight_kg: Optional[float] = None
    end_weight_kg: Optional[float] = None
    slope_kg_per_day: Optional[float] = None
    direction: WeightTrendDirection
    confidence: EvaluationConfidence
    is_interpretable: bool
    outlier_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ReasonPatternSummaryDTO(BaseModel):
    reason_counts: Dict[str, int] = Field(default_factory=dict)
    dominant_reasons: List[DeviationReason] = Field(default_factory=list)
    pattern_confidence: EvaluationConfidence

    model_config = ConfigDict(from_attributes=True)


class AdherencePatternSummaryDTO(BaseModel):
    category: AdherenceContextCategory
    reporting_coverage_ratio: float
    full_completion_ratio: float
    confidence: EvaluationConfidence

    model_config = ConfigDict(from_attributes=True)


class NutritionAdaptationEvaluationInputDTO(BaseModel):
    user_id: Optional[str] = None
    nutrition_goal_type: str = "NUTRITION_WEIGHT_GAIN"
    target_energy_kcal: float
    meal_structure_state: MealStructureState = MealStructureState.BASELINE
    step_index: int = 0
    assessment_eligibility_status: str = "ELIGIBLE"
    evidence_days: List[NutritionEvidenceDayDTO] = Field(default_factory=list)
    weight_measurements: List[WeightObservationDTO] = Field(default_factory=list)
    last_adaptation_at: Optional[str] = None
    evaluation_reference_time: Optional[str] = None
    policy_versions: Dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class NutritionAdaptationEvaluationResultDTO(BaseModel):
    evaluation_id: str
    evaluated_at: str
    decision: AdaptationDecision
    review_domain: AdjustmentReviewDomain
    confidence: EvaluationConfidence
    evidence_window: EvidenceWindowDTO
    data_sufficiency: DataSufficiencyDTO
    adherence_summary: AdherencePatternSummaryDTO
    weight_trend: WeightTrendSummaryDTO
    reason_patterns: ReasonPatternSummaryDTO
    reason_codes: List[EvaluationReasonCode] = Field(default_factory=list)
    explanations: List[str] = Field(default_factory=list)
    policy_version: str = AdaptationEvaluationPolicy.VERSION

    model_config = ConfigDict(from_attributes=True)
