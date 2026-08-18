from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.daily_nutrition_plan.constants import (
    DailyPlanStatus,
    DailyPlanWarningSeverity,
    DailyPlanWarningCode,
    MacroCompleteness,
)
from app.food_candidates.constants import (
    FoodPlannerRole,
    CandidateMatchStatus,
)
from app.meal_structure.constants import MealSlotType
from app.price_knowledge.constants import (
    PriceConfidence,
    CostCompleteness,
)
from app.budget_selection.constants import (
    BudgetSelectionStatus,
    BudgetSource,
)
from app.food_candidates.models import FoodCandidateSetDTO
from app.price_knowledge.models import CandidateCostEstimateDTO
from app.budget_selection.models import BudgetAwareSelectionResultDTO


class DailyMealFoodItemDTO(BaseModel):
    food_item_id: str
    canonical_name: str
    role: FoodPlannerRole
    serving_name: str
    grams: float
    energy_kcal: float
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    carbohydrate_g: Optional[float] = None


class DailyMealEntryDTO(BaseModel):
    slot_id: str
    slot_type: MealSlotType
    scheduled_time: str
    earliest_time: Optional[str] = None
    latest_time: Optional[str] = None
    candidate_id: str
    foods: List[DailyMealFoodItemDTO]
    planned_energy_kcal: float
    planned_protein_g: Optional[float] = None
    planned_fat_g: Optional[float] = None
    planned_carbohydrate_g: Optional[float] = None
    nutrition_fit_status: CandidateMatchStatus
    estimated_cost_idr: Optional[int] = None
    cost_completeness: CostCompleteness
    price_confidence: PriceConfidence
    uses_stale_prices: bool
    location_context: Optional[str] = None
    preparation_context: Optional[str] = None
    explanations: List[str] = []


class DailyNutritionSummaryDTO(BaseModel):
    target_energy_kcal: float
    planned_energy_kcal: float
    energy_difference_kcal: float
    planned_protein_g: Optional[float] = None
    planned_fat_g: Optional[float] = None
    planned_carbohydrate_g: Optional[float] = None
    macro_completeness: MacroCompleteness
    strict_match_slot_count: int
    near_match_slot_count: int


class DailyBudgetSummaryDTO(BaseModel):
    budget_envelope_idr: Optional[int] = None
    planned_cost_idr: Optional[int] = None
    remaining_after_plan_idr: Optional[int] = None
    cost_completeness: CostCompleteness
    price_confidence: PriceConfidence
    uses_stale_prices: bool
    budget_source: BudgetSource


class DailyPlanWarningDTO(BaseModel):
    code: DailyPlanWarningCode
    severity: DailyPlanWarningSeverity
    message: str


class DailyPlanProvenanceDTO(BaseModel):
    assessment_snapshot_id: Optional[str] = None
    nutrition_policy_version: str
    meal_structure_policy_version: str
    food_candidate_policy_version: str
    price_policy_version: str
    budget_selection_policy_version: str
    assembly_policy_version: str


class DailyNutritionPlanAssemblyInputDTO(BaseModel):
    date: str
    logical_day_id: str
    target_energy_kcal: float
    nutrition_eligibility_status: str
    meal_schedule: Any  # Validated MealStructurePlanResponse or dict/DTO
    budget_selection_result: BudgetAwareSelectionResultDTO
    selected_candidates_by_slot: Dict[str, FoodCandidateSetDTO]
    candidate_costs_by_candidate_id: Dict[str, CandidateCostEstimateDTO]
    policy_versions: Optional[Dict[str, str]] = None
    assessment_snapshot_id: Optional[str] = None


class DailyNutritionPlanDTO(BaseModel):
    plan_id: str
    date: str
    logical_day_id: str
    status: DailyPlanStatus
    nutrition_summary: Optional[DailyNutritionSummaryDTO] = None
    budget_summary: Optional[DailyBudgetSummaryDTO] = None
    meal_entries: List[DailyMealEntryDTO] = []
    warnings: List[DailyPlanWarningDTO] = []
    provenance: DailyPlanProvenanceDTO
    policy_versions: Dict[str, str] = {}
