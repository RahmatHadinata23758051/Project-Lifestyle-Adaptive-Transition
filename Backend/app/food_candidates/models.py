from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from app.food_candidates.constants import (
    FoodPlannerRole,
    CandidateMatchStatus,
    CandidateGenerationStatus,
    CandidateRejectionReason,
    CandidatePolicy,
)
from app.food_knowledge.models import FoodKnowledgeItemDTO
from app.meal_structure.models import MealSlotDTO


@dataclass
class FoodCandidateItemDTO:
    food_item_id: str
    canonical_name: str
    role: FoodPlannerRole
    serving_id: Optional[str]
    serving_name: str
    grams: float
    energy_kcal: float
    protein_g: Optional[float]
    fat_g: Optional[float]
    carbohydrate_g: Optional[float]


@dataclass
class FoodCandidateSetDTO:
    candidate_id: str
    slot_id: str
    items: List[FoodCandidateItemDTO]
    total_energy_kcal: float
    total_protein_g: Optional[float]
    total_fat_g: Optional[float]
    total_carbohydrate_g: Optional[float]
    energy_deviation_kcal: float
    absolute_energy_deviation: float
    match_status: CandidateMatchStatus
    explanations: List[str] = field(default_factory=list)
    preparation_complexity: str = "VERY_SIMPLE"
    source_quality: str = "VERIFIED_OFFICIAL"
    macro_data_partial: bool = False


@dataclass
class CandidateGenerationInputDTO:
    slot: MealSlotDTO
    food_pool: List[FoodKnowledgeItemDTO]
    nutrition_eligible: bool = True
    nutrition_eligibility_status: str = "ELIGIBLE"
    user_allergies: List[str] = field(default_factory=list)
    user_restrictions: List[str] = field(default_factory=list)
    cooking_capability: Optional[str] = "CAN_COOK"  # CAN_COOK, LIMITED, BUY_ONLY, UNKNOWN
    user_equipment: Optional[List[str]] = None  # None/UNKNOWN -> equipment unknown
    preferred_foods: List[str] = field(default_factory=list)
    disliked_foods: List[str] = field(default_factory=list)


@dataclass
class FoodCandidateGenerationResultDTO:
    slot_id: str
    status: CandidateGenerationStatus
    candidate_count: int
    candidates: List[FoodCandidateSetDTO]
    evaluated_candidate_count: int = 0
    eligible_candidate_count: int = 0
    returned_candidate_count: int = 0
    rejected_counts_by_reason: Dict[str, int] = field(default_factory=dict)
    search_truncated: bool = False
    policy_version: str = CandidatePolicy.VERSION
    ranking_policy_version: str = CandidatePolicy.RANKING_POLICY_VERSION
