import hashlib
from typing import Dict, List, Optional
from app.daily_nutrition_plan.constants import DailyPlanPolicy
from app.daily_nutrition_plan.models import DailyPlanProvenanceDTO
from app.nutrition.constants import NutritionPolicy
from app.meal_structure.constants import MealPolicy
from app.food_candidates.constants import CandidatePolicy
from app.price_knowledge.constants import PricePolicy
from app.budget_selection.constants import BudgetSelectionPolicy


def build_daily_plan_provenance(
    policy_versions: Optional[Dict[str, str]] = None,
    assessment_snapshot_id: Optional[str] = None,
) -> DailyPlanProvenanceDTO:
    """
    Builds structured policy provenance for the daily nutrition plan.
    """
    pv = policy_versions or {}
    return DailyPlanProvenanceDTO(
        assessment_snapshot_id=assessment_snapshot_id,
        nutrition_policy_version=pv.get("nutrition_policy_version", NutritionPolicy.VERSION),
        meal_structure_policy_version=pv.get("meal_structure_policy_version", MealPolicy.VERSION),
        food_candidate_policy_version=pv.get("food_candidate_policy_version", CandidatePolicy.VERSION),
        price_policy_version=pv.get("price_policy_version", PricePolicy.VERSION),
        budget_selection_policy_version=pv.get("budget_selection_policy_version", BudgetSelectionPolicy.VERSION),
        assembly_policy_version=DailyPlanPolicy.VERSION,
    )


def generate_deterministic_plan_id(
    logical_day_id: str,
    selected_candidate_ids: List[str],
    provenance: DailyPlanProvenanceDTO,
) -> str:
    """
    Generates a deterministic, reproducible plan ID from upstream state and candidate IDs.
    """
    sorted_cands = sorted(selected_candidate_ids)
    components = [
        logical_day_id,
        ",".join(sorted_cands),
        provenance.nutrition_policy_version,
        provenance.meal_structure_policy_version,
        provenance.food_candidate_policy_version,
        provenance.price_policy_version,
        provenance.budget_selection_policy_version,
        provenance.assembly_policy_version,
    ]
    raw_hash = hashlib.sha256(";".join(components).encode("utf-8")).hexdigest()[:16]
    return f"plan_{logical_day_id}_{raw_hash}"
