from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.nutrition_adaptation.constants import (
    AdaptationDecision,
    AdjustmentReviewDomain,
    DataSufficiencyStatus,
    WeightTrendDirection,
    AdherenceContextCategory,
    EvaluationConfidence,
    DayEvidenceQuality,
    EvaluationReasonCode,
)
from app.nutrition_adherence.constants import (
    ReportingCompleteness,
    DeviationReason,
)
from app.daily_nutrition_plan.constants import MacroCompleteness, DailyPlanStatus
from app.meal_structure.constants import MealStructureState


class WeightObservationRequest(BaseModel):
    measured_at: str
    weight_kg: float
    source: str = "USER_LOG"
    context: Optional[str] = None


class NutritionEvidenceDayRequest(BaseModel):
    logical_day_id: str
    date: str
    plan_status: DailyPlanStatus = DailyPlanStatus.READY
    reporting_completeness: ReportingCompleteness
    nutrition_completeness: MacroCompleteness
    planned_energy_kcal: float
    actual_energy_kcal: Optional[float] = None
    meal_completion_counts: Dict[str, int] = {}
    deviation_reasons: List[DeviationReason] = []
    evidence_quality: Optional[DayEvidenceQuality] = None


class NutritionAdaptationEvaluationRequest(BaseModel):
    nutrition_goal_type: str = "NUTRITION_WEIGHT_GAIN"
    target_energy_kcal: float
    meal_structure_state: MealStructureState = MealStructureState.BASELINE
    step_index: int = 0
    assessment_eligibility_status: str = "ELIGIBLE"
    evidence_days: List[NutritionEvidenceDayRequest] = []
    weight_measurements: List[WeightObservationRequest] = []
    last_adaptation_at: Optional[str] = None
    evaluation_reference_time: Optional[str] = None
    persist: bool = False


class EvidenceWindowResponse(BaseModel):
    start_date: str
    end_date: str
    total_days: int
    usable_adherence_days: int
    weight_measurement_count: int


class DataSufficiencyResponse(BaseModel):
    status: DataSufficiencyStatus
    usable_days_count: int
    weight_count: int
    is_sufficient: bool
    reasons: List[str]


class WeightTrendSummaryResponse(BaseModel):
    measurement_count: int
    start_weight_kg: Optional[float] = None
    end_weight_kg: Optional[float] = None
    slope_kg_per_day: Optional[float] = None
    direction: WeightTrendDirection
    confidence: EvaluationConfidence
    is_interpretable: bool
    outlier_count: int


class ReasonPatternSummaryResponse(BaseModel):
    reason_counts: Dict[str, int]
    dominant_reasons: List[DeviationReason]
    pattern_confidence: EvaluationConfidence


class AdherencePatternSummaryResponse(BaseModel):
    category: AdherenceContextCategory
    reporting_coverage_ratio: float
    full_completion_ratio: float
    confidence: EvaluationConfidence


class NutritionAdaptationEvaluationResponse(BaseModel):
    evaluation_id: str
    evaluated_at: str
    decision: AdaptationDecision
    review_domain: AdjustmentReviewDomain
    confidence: EvaluationConfidence
    evidence_window: EvidenceWindowResponse
    data_sufficiency: DataSufficiencyResponse
    adherence_summary: AdherencePatternSummaryResponse
    weight_trend: WeightTrendSummaryResponse
    reason_patterns: ReasonPatternSummaryResponse
    reason_codes: List[EvaluationReasonCode]
    explanations: List[str]
    policy_version: str

    model_config = ConfigDict(from_attributes=True)
