from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.food_candidates.constants import (
    FoodPlannerRole,
    CandidateMatchStatus,
    CandidateGenerationStatus,
    CandidatePolicy,
)
from app.meal_structure.constants import MealSlotType


class FoodCandidateItemResponse(BaseModel):
    food_item_id: str
    canonical_name: str
    role: FoodPlannerRole
    serving_id: Optional[str] = None
    serving_name: str
    grams: float
    energy_kcal: float
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    carbohydrate_g: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class FoodCandidateSetResponse(BaseModel):
    candidate_id: str
    slot_id: str
    items: List[FoodCandidateItemResponse]
    total_energy_kcal: float
    total_protein_g: Optional[float] = None
    total_fat_g: Optional[float] = None
    total_carbohydrate_g: Optional[float] = None
    energy_deviation_kcal: float
    absolute_energy_deviation: float
    match_status: CandidateMatchStatus
    explanations: List[str] = []
    preparation_complexity: str = "VERY_SIMPLE"
    source_quality: str = "VERIFIED_OFFICIAL"
    macro_data_partial: bool = False

    model_config = ConfigDict(from_attributes=True)


class FoodCandidatePreviewInput(BaseModel):
    slot_id: str = "slot_1"
    slot_type: MealSlotType = MealSlotType.MAIN_MEAL
    target_kcal: float = Field(..., gt=0)
    min_kcal: Optional[float] = None
    max_kcal: Optional[float] = None
    nutrition_eligible: bool = True
    nutrition_eligibility_status: str = "ELIGIBLE"
    user_allergies: List[str] = []
    user_restrictions: List[str] = []
    cooking_capability: Optional[str] = None
    user_equipment: Optional[List[str]] = None


class FoodCandidateGenerationResponse(BaseModel):
    slot_id: str
    status: CandidateGenerationStatus
    candidate_count: int
    candidates: List[FoodCandidateSetResponse]
    evaluated_candidate_count: int = 0
    eligible_candidate_count: int = 0
    returned_candidate_count: int = 0
    rejected_counts_by_reason: Dict[str, int] = {}
    search_truncated: bool = False
    policy_version: str = CandidatePolicy.VERSION
    ranking_policy_version: str = CandidatePolicy.RANKING_POLICY_VERSION

    model_config = ConfigDict(from_attributes=True)
