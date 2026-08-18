from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
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
    AdherencePolicy,
)
from app.price_knowledge.constants import CostCompleteness
from app.daily_nutrition_plan.constants import MacroCompleteness
from app.daily_nutrition_plan.models import DailyNutritionPlanDTO, DailyMealEntryDTO


class ActualFoodItemDTO(BaseModel):
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

    model_config = ConfigDict(from_attributes=True)


class MealCheckinDTO(BaseModel):
    checkin_id: Optional[str] = None
    plan_id: str
    logical_day_id: str
    slot_id: str
    status: MealCheckinStatus
    meal_occurred_at: Optional[str] = None
    checked_in_at: str
    actual_items: List[ActualFoodItemDTO] = []
    actual_spend_idr: Optional[int] = None
    deviation_reason: Optional[DeviationReason] = None
    notes: Optional[str] = None
    certainty: ActualIntakeCertainty = ActualIntakeCertainty.EXACT
    revision: int = 1

    model_config = ConfigDict(from_attributes=True)


class UnplannedIntakeDTO(BaseModel):
    intake_id: Optional[str] = None
    logical_day_id: str
    occurred_at: str
    recorded_at: str
    items: List[ActualFoodItemDTO]
    actual_spend_idr: Optional[int] = None
    reason: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ActualNutritionSummaryDTO(BaseModel):
    energy_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    carbohydrate_g: Optional[float] = None
    completeness: MacroCompleteness
    resolved_item_count: int
    unresolved_item_count: int

    model_config = ConfigDict(from_attributes=True)


class ActualSpendSummaryDTO(BaseModel):
    known_spend_idr: Optional[int] = None
    completeness: CostCompleteness
    reported_meal_count: int
    missing_spend_count: int

    model_config = ConfigDict(from_attributes=True)


class SlotAdherenceDTO(BaseModel):
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

    model_config = ConfigDict(from_attributes=True)


class DailyNutritionAdherenceDTO(BaseModel):
    logical_day_id: str
    date: str
    plan_id: Optional[str] = None
    reporting_completeness: ReportingCompleteness
    planned_energy_kcal: float
    actual_nutrition_summary: ActualNutritionSummaryDTO
    energy_difference_kcal: Optional[float] = None
    planned_cost_idr: Optional[int] = None
    actual_spend_summary: ActualSpendSummaryDTO
    slot_adherences: List[SlotAdherenceDTO] = []
    unplanned_intakes: List[UnplannedIntakeDTO] = []
    explanations: List[str] = []
    policy_version: str = AdherencePolicy.VERSION

    model_config = ConfigDict(from_attributes=True)
