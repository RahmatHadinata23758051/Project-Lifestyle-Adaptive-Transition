from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.nutrition_adherence.constants import (
    MealCheckinStatus,
    MealCompletionState,
    TimingAdherenceStatus,
    FoodChoiceAdherence,
    EnergyAdherenceStatus,
    ReportingCompleteness,
    ActualIntakeCertainty,
    ActualFoodSourceType,
    DeviationReason,
)
from app.price_knowledge.constants import CostCompleteness
from app.daily_nutrition_plan.constants import MacroCompleteness
from app.schemas.daily_nutrition_plan import DailyNutritionPlanResponse


class ActualFoodItemRequest(BaseModel):
    food_item_id: Optional[str] = None
    display_name: str
    serving_id: Optional[str] = None
    serving_name: Optional[str] = None
    grams: Optional[float] = None
    quantity: float = 1.0
    energy_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    carbohydrate_g: Optional[float] = None
    source_type: ActualFoodSourceType = ActualFoodSourceType.USER_REPORTED_UNRESOLVED
    certainty: ActualIntakeCertainty = ActualIntakeCertainty.EXACT


class MealCheckinRequest(BaseModel):
    plan_id: str
    logical_day_id: str
    slot_id: str
    status: MealCheckinStatus
    meal_occurred_at: Optional[str] = None
    checked_in_at: Optional[str] = None
    actual_items: List[ActualFoodItemRequest] = []
    actual_spend_idr: Optional[int] = None
    deviation_reason: Optional[DeviationReason] = None
    notes: Optional[str] = None
    certainty: ActualIntakeCertainty = ActualIntakeCertainty.EXACT


class UnplannedIntakeRequest(BaseModel):
    logical_day_id: str
    occurred_at: str
    recorded_at: Optional[str] = None
    items: List[ActualFoodItemRequest]
    actual_spend_idr: Optional[int] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


class ActualFoodItemResponse(BaseModel):
    food_item_id: Optional[str] = None
    display_name: str
    serving_id: Optional[str] = None
    serving_name: Optional[str] = None
    grams: Optional[float] = None
    quantity: float
    energy_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    carbohydrate_g: Optional[float] = None
    source_type: ActualFoodSourceType
    certainty: ActualIntakeCertainty

    model_config = ConfigDict(from_attributes=True)


class MealCheckinResponse(BaseModel):
    checkin_id: Optional[str] = None
    plan_id: str
    logical_day_id: str
    slot_id: str
    status: MealCheckinStatus
    meal_occurred_at: Optional[str] = None
    checked_in_at: str
    actual_items: List[ActualFoodItemResponse] = []
    actual_spend_idr: Optional[int] = None
    deviation_reason: Optional[DeviationReason] = None
    notes: Optional[str] = None
    certainty: ActualIntakeCertainty
    revision: int = 1

    model_config = ConfigDict(from_attributes=True)


class UnplannedIntakeResponse(BaseModel):
    intake_id: Optional[str] = None
    logical_day_id: str
    occurred_at: str
    recorded_at: str
    items: List[ActualFoodItemResponse]
    actual_spend_idr: Optional[int] = None
    reason: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ActualNutritionSummaryResponse(BaseModel):
    energy_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    carbohydrate_g: Optional[float] = None
    completeness: MacroCompleteness
    resolved_item_count: int
    unresolved_item_count: int


class ActualSpendSummaryResponse(BaseModel):
    known_spend_idr: Optional[int] = None
    completeness: CostCompleteness
    reported_meal_count: int
    missing_spend_count: int


class SlotAdherenceResponse(BaseModel):
    slot_id: str
    slot_type: str
    scheduled_time: str
    meal_completion: MealCompletionState
    timing_adherence: TimingAdherenceStatus
    food_choice_adherence: FoodChoiceAdherence
    energy_adherence: EnergyAdherenceStatus
    planned_energy_kcal: float
    actual_energy_kcal: Optional[float] = None
    planned_cost_idr: Optional[int] = None
    actual_spend_idr: Optional[int] = None
    deviation_reason: Optional[DeviationReason] = None
    explanations: List[str] = []


class DailyNutritionAdherenceResponse(BaseModel):
    logical_day_id: str
    date: str
    plan_id: Optional[str] = None
    reporting_completeness: ReportingCompleteness
    planned_energy_kcal: float
    actual_nutrition_summary: ActualNutritionSummaryResponse
    energy_difference_kcal: Optional[float] = None
    planned_cost_idr: Optional[int] = None
    actual_spend_summary: ActualSpendSummaryResponse
    slot_adherences: List[SlotAdherenceResponse] = []
    unplanned_intakes: List[UnplannedIntakeResponse] = []
    explanations: List[str] = []
    policy_version: str


class EvaluateAdherencePreviewRequest(BaseModel):
    plan: DailyNutritionPlanResponse
    checkins: List[MealCheckinRequest] = []
    unplanned_intakes: List[UnplannedIntakeRequest] = []
