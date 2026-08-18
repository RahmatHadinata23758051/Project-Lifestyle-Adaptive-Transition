from typing import List, Tuple
from app.food_knowledge.constants import (
    FoodPlannerEligibilityStatus,
    DataQualityStatus,
    NutrientCompleteness,
    AllergenRelationshipType,
)
from app.food_knowledge.models import FoodKnowledgeItemDTO


def evaluate_food_planner_eligibility(
    food: FoodKnowledgeItemDTO,
) -> Tuple[FoodPlannerEligibilityStatus, List[str]]:
    """
    Evaluates whether a food item is eligible for automated nutrition meal planning.
    Planner Invariant: UNVERIFIED or INSUFFICIENT foods are not planner-eligible by default.
    """
    reasons: List[str] = []

    if not food.is_active:
        return FoodPlannerEligibilityStatus.DEPRECATED, ["Item makanan tidak aktif/kedaluwarsa."]

    if food.data_quality_status == DataQualityStatus.DEPRECATED:
        return FoodPlannerEligibilityStatus.DEPRECATED, ["Kualitas data makanan bertatus DEPRECATED."]

    if food.data_quality_status == DataQualityStatus.UNVERIFIED:
        reasons.append("Data makanan belum diverifikasi resmi/kurasi (UNVERIFIED).")

    if food.nutrients is None or food.nutrients.completeness != NutrientCompleteness.CORE_COMPLETE:
        reasons.append("Profil nutrisi inti (energi, protein, lemak, karbohidrat) tidak lengkap.")
        return FoodPlannerEligibilityStatus.NUTRIENT_DATA_INSUFFICIENT, reasons

    # Check for ambiguous unknown allergen relationships
    for a in food.allergens:
        if a.relationship_type == AllergenRelationshipType.UNKNOWN:
            reasons.append(f"Hubungan alergen '{a.allergen_type.value}' berstatus UNKNOWN.")
            return FoodPlannerEligibilityStatus.ALLERGEN_UNCERTAIN, reasons

    if len(reasons) > 0:
        return FoodPlannerEligibilityStatus.PARTIAL_DATA, reasons

    return FoodPlannerEligibilityStatus.ELIGIBLE, []
