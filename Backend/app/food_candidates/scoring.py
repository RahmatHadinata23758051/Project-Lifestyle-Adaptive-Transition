import hashlib
from typing import List, Optional
from app.meal_structure.models import MealSlotDTO
from app.food_candidates.constants import CandidateMatchStatus
from app.food_candidates.models import FoodCandidateItemDTO, FoodCandidateSetDTO


def build_candidate_set(
    slot: MealSlotDTO,
    items: List[FoodCandidateItemDTO],
) -> FoodCandidateSetDTO:
    """
    Aggregates component items and validates energy against slot range.
    """
    total_energy = round(sum(i.energy_kcal for i in items), 1)

    protein_values = [i.protein_g for i in items if i.protein_g is not None]
    total_protein = round(sum(protein_values), 1) if len(protein_values) == len(items) else None

    fat_values = [i.fat_g for i in items if i.fat_g is not None]
    total_fat = round(sum(fat_values), 1) if len(fat_values) == len(items) else None

    carb_values = [i.carbohydrate_g for i in items if i.carbohydrate_g is not None]
    total_carb = round(sum(carb_values), 1) if len(carb_values) == len(items) else None

    deviation = round(total_energy - slot.target_kcal, 1)
    abs_deviation = round(abs(deviation), 1)

    # Match status check
    if slot.min_kcal <= total_energy <= slot.max_kcal:
        match_status = CandidateMatchStatus.STRICT_MATCH
    else:
        # Near match if within 25% deviation from target
        near_lower = slot.target_kcal * 0.75
        near_upper = slot.target_kcal * 1.25
        if near_lower <= total_energy <= near_upper:
            match_status = CandidateMatchStatus.NEAR_MATCH
        else:
            match_status = CandidateMatchStatus.INELIGIBLE

    # Deterministic candidate ID
    items_sig = "-".join(sorted(f"{i.food_item_id}:{i.grams:.0f}" for i in items))
    cand_raw = f"{slot.slot_id}:{items_sig}"
    cand_id = "cand_" + hashlib.sha256(cand_raw.encode("utf-8")).hexdigest()[:12]

    explanations = [
        f"Alokasi kalori {total_energy:.0f} kcal (target {slot.target_kcal:.0f} kcal, rentang {slot.min_kcal:.0f}–{slot.max_kcal:.0f} kcal)",
        f"Kombinasi {len(items)} makanan dengan komposisi nutrisi terverifikasi resmi",
    ]

    return FoodCandidateSetDTO(
        candidate_id=cand_id,
        slot_id=slot.slot_id,
        items=items,
        total_energy_kcal=total_energy,
        total_protein_g=total_protein,
        total_fat_g=total_fat,
        total_carbohydrate_g=total_carb,
        energy_deviation_kcal=deviation,
        absolute_energy_deviation=abs_deviation,
        match_status=match_status,
        explanations=explanations,
        preparation_complexity="VERY_SIMPLE",
        source_quality="VERIFIED_OFFICIAL",
        macro_data_partial=any(i.protein_g is None or i.fat_g is None or i.carbohydrate_g is None for i in items),
    )


def rank_candidates(candidates: List[FoodCandidateSetDTO]) -> List[FoodCandidateSetDTO]:
    """
    Deterministic ranking v0.1:
    1. STRICT_MATCH before NEAR_MATCH / INELIGIBLE
    2. Lowest absolute energy deviation from slot target
    3. Highest protein content
    4. Deterministic candidate ID
    """
    def sort_key(c: FoodCandidateSetDTO):
        status_rank = 0 if c.match_status == CandidateMatchStatus.STRICT_MATCH else (1 if c.match_status == CandidateMatchStatus.NEAR_MATCH else 2)
        protein_neg = -(c.total_protein_g or 0.0)
        return (status_rank, c.absolute_energy_deviation, protein_neg, c.candidate_id)

    return sorted(candidates, key=sort_key)
