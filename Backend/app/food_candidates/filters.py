from typing import List, Tuple, Optional
from app.food_knowledge.constants import (
    DataQualityStatus,
    NutrientCompleteness,
    AllergenType,
    PreparationState,
    HalalStatus,
    KitchenEquipment,
)
from app.food_knowledge.models import FoodKnowledgeItemDTO
from app.food_knowledge.allergens import check_allergen_conflict
from app.food_candidates.constants import CandidateRejectionReason


def is_food_eligible_for_candidate_pool(
    food: FoodKnowledgeItemDTO,
    user_allergies: List[str],
    user_restrictions: List[str],
    cooking_capability: Optional[str] = "CAN_COOK",
    user_equipment: Optional[List[str]] = None,
) -> Tuple[bool, Optional[CandidateRejectionReason], str]:
    """
    Pure deterministic eligibility filter pipeline (P1.2 Hardened):
    1. Quality & Completeness Filter
    2. Allergen Hard-Block Filter (Unknown != Safe)
    3. Dietary & Halal Restriction Filter (Structured Halal Only, Zero-Inference)
    4. Cooking Capability & Equipment Compatibility Filter (Unknown Equipment != Available)
    """
    # 1. Quality & Completeness
    if not food.is_active:
        return False, CandidateRejectionReason.QUALITY_NOT_ELIGIBLE, "Makanan tidak aktif."

    if food.data_quality_status not in (
        DataQualityStatus.VERIFIED_OFFICIAL,
        DataQualityStatus.VERIFIED_CURATED,
    ):
        return False, CandidateRejectionReason.QUALITY_NOT_ELIGIBLE, f"Kualitas data '{food.data_quality_status.value}' belum terverifikasi."

    if not food.nutrients or food.nutrients.energy_kcal is None or food.nutrients.completeness != NutrientCompleteness.CORE_COMPLETE:
        return False, CandidateRejectionReason.NUTRIENT_DATA_INCOMPLETE, "Data nutrisi inti (kalori, protein, lemak, karbohidrat) tidak lengkap."

    # 2. Allergen Safety
    allergen_enums: List[AllergenType] = []
    for a_str in user_allergies:
        try:
            allergen_enums.append(AllergenType(a_str.upper()))
        except ValueError:
            pass

    if allergen_enums:
        has_conflict, reasons = check_allergen_conflict(allergen_enums, food.allergens)
        if has_conflict:
            is_unknown = any("UNKNOWN" in r for r in reasons)
            reason_code = CandidateRejectionReason.ALLERGEN_UNKNOWN if is_unknown else CandidateRejectionReason.ALLERGEN_CONFLICT
            return False, reason_code, f"Konflik alergen: {', '.join(reasons)}"

    # 3. Dietary & Halal Restrictions
    restrictions_upper = [r.upper() for r in user_restrictions]
    canonical_lower = food.canonical_name.lower()

    if "HALAL_REQUIRED" in restrictions_upper or "HALAL" in restrictions_upper:
        # P0.1: Must never infer halal from category/name/no-pork. Use structured status only.
        halal_st = getattr(food, "halal_status", HalalStatus.UNKNOWN)
        if halal_st == HalalStatus.NOT_HALAL:
            return False, CandidateRejectionReason.HALAL_RESTRICTION_CONFLICT, "Makanan berstatus tidak halal."
        elif halal_st == HalalStatus.VERIFIED_HALAL:
            pass  # Verified halal
        elif halal_st == HalalStatus.NOT_APPLICABLE:
            pass  # Non-food items or natural water
        else:
            # UNKNOWN halal status is rejected conservatively (Unknown != Safe)
            return False, CandidateRejectionReason.HALAL_STATUS_UNVERIFIED, "Status kehalalan bahan belum terverifikasi secara terstruktur."

    if "NO_PORK" in restrictions_upper:
        if "babi" in canonical_lower or "pork" in canonical_lower or "lard" in canonical_lower:
            return False, CandidateRejectionReason.RESTRICTION_CONFLICT, "Mengandung unsur babi yang dibatasi pengguna."

    if "VEGETARIAN" in restrictions_upper:
        if food.food_category in ("MEAT", "POULTRY", "FISH_SEAFOOD"):
            return False, CandidateRejectionReason.RESTRICTION_CONFLICT, "Bahan hewani bertentangan dengan preferensi vegetarian."

    # 4. Cooking Capability & Equipment (H2)
    capability_upper = (cooking_capability or "UNKNOWN").upper()
    prep_req = food.preparation_requirements

    if capability_upper in ("BUY_ONLY", "UNKNOWN"):
        if prep_req and prep_req.requires_cooking:
            if food.preparation_state not in (PreparationState.READY_TO_EAT, PreparationState.COOKED, PreparationState.FRIED, PreparationState.BOILED):
                return False, CandidateRejectionReason.PREPARATION_INCOMPATIBLE, "Makanan memerlukan proses memasak sedangkan kemampuan masak belum terverifikasi/BUY_ONLY."

    if prep_req and prep_req.required_equipment:
        non_none_reqs = [eq for eq in prep_req.required_equipment if eq != KitchenEquipment.NONE]
        if non_none_reqs:
            if user_equipment is None:
                # Unknown equipment != Available
                return False, CandidateRejectionReason.EQUIPMENT_UNKNOWN, "Data peralatan dapur pengguna belum diketahui untuk bahan yang memerlukan peralatan."
            user_eq_set = {eq.upper() for eq in user_equipment}
            for req_eq in non_none_reqs:
                if req_eq.value.upper() not in user_eq_set:
                    return False, CandidateRejectionReason.PREPARATION_INCOMPATIBLE, f"Memerlukan alat '{req_eq.value}' yang tidak dimiliki pengguna."

    return True, None, "Layak digunakan."
