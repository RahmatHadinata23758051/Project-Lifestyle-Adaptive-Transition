from typing import List, Dict
from collections import defaultdict
from app.food_candidates.constants import (
    FoodPlannerRole,
    CandidateMatchStatus,
    CandidateGenerationStatus,
    CandidateRejectionReason,
    CandidatePolicy,
)
from app.food_candidates.models import (
    CandidateGenerationInputDTO,
    FoodCandidateItemDTO,
    FoodCandidateSetDTO,
    FoodCandidateGenerationResultDTO,
)
from app.food_candidates.roles import map_food_category_to_role
from app.food_candidates.filters import is_food_eligible_for_candidate_pool
from app.food_candidates.servings import generate_portion_options_for_food
from app.food_candidates.combinations import generate_bounded_combinations
from app.food_candidates.scoring import rank_candidates


def generate_food_candidates(
    input_dto: CandidateGenerationInputDTO,
) -> FoodCandidateGenerationResultDTO:
    """
    Pure zero-I/O Food Candidate Engine (P1.2 Hardened).
    Generates deterministic, safe food combinations to fill a meal slot target.
    Enforces single-source-of-truth nutrition eligibility gate and unknown->NEEDS_MORE_DATA semantics.
    """
    slot = input_dto.slot

    # 1. P0.2 — Single Authoritative Nutrition Eligibility Gate
    elig_status = (input_dto.nutrition_eligibility_status or "ELIGIBLE").upper()
    if elig_status != "ELIGIBLE":
        gen_status = (
            CandidateGenerationStatus.NEEDS_MORE_DATA
            if elig_status == "NEEDS_MORE_DATA"
            else CandidateGenerationStatus.NOT_ELIGIBLE
        )
        return FoodCandidateGenerationResultDTO(
            slot_id=slot.slot_id,
            status=gen_status,
            candidate_count=0,
            candidates=[],
            evaluated_candidate_count=0,
            eligible_candidate_count=0,
            returned_candidate_count=0,
            rejected_counts_by_reason={CandidateRejectionReason.NUTRITION_NOT_ELIGIBLE.value: 1},
            search_truncated=False,
            policy_version=CandidatePolicy.VERSION,
            ranking_policy_version=CandidatePolicy.RANKING_POLICY_VERSION,
        )

    # 2. Input Validation
    if slot.min_kcal <= 0:
        raise ValueError("Batas energi minimum slot (min_kcal) harus bernilai positif > 0.")
    if slot.max_kcal < slot.min_kcal:
        raise ValueError("Batas energi maksimum slot (max_kcal) tidak boleh lebih kecil dari min_kcal.")

    rejected_counts: Dict[str, int] = defaultdict(int)
    eligible_foods = []

    # 3. Filter Reference Food Pool
    for food in input_dto.food_pool:
        is_ok, reason, _ = is_food_eligible_for_candidate_pool(
            food=food,
            user_allergies=input_dto.user_allergies,
            user_restrictions=input_dto.user_restrictions,
            cooking_capability=input_dto.cooking_capability,
            user_equipment=input_dto.user_equipment,
        )
        if is_ok:
            eligible_foods.append(food)
        else:
            if reason:
                rejected_counts[reason.value] += 1

    if not eligible_foods:
        # If all candidates failed solely due to unknown equipment / unknown allergen data, return NEEDS_MORE_DATA
        has_unknown_equipment = CandidateRejectionReason.EQUIPMENT_UNKNOWN.value in rejected_counts
        has_unknown_allergen = CandidateRejectionReason.ALLERGEN_UNKNOWN.value in rejected_counts
        only_unknown_issues = all(
            k in (CandidateRejectionReason.EQUIPMENT_UNKNOWN.value, CandidateRejectionReason.ALLERGEN_UNKNOWN.value)
            for k in rejected_counts.keys()
        )

        if only_unknown_issues and (has_unknown_equipment or has_unknown_allergen):
            fallback_status = CandidateGenerationStatus.NEEDS_MORE_DATA
        else:
            fallback_status = CandidateGenerationStatus.NO_ELIGIBLE_FOODS

        return FoodCandidateGenerationResultDTO(
            slot_id=slot.slot_id,
            status=fallback_status,
            candidate_count=0,
            candidates=[],
            evaluated_candidate_count=0,
            eligible_candidate_count=0,
            returned_candidate_count=0,
            rejected_counts_by_reason=dict(rejected_counts),
            search_truncated=False,
            policy_version=CandidatePolicy.VERSION,
            ranking_policy_version=CandidatePolicy.RANKING_POLICY_VERSION,
        )

    # 4. Role Mapping and Portion Generation (with discrete serving handling)
    items_by_role: Dict[FoodPlannerRole, List[FoodCandidateItemDTO]] = defaultdict(list)
    for food in eligible_foods:
        role = map_food_category_to_role(food.food_category)
        portions = generate_portion_options_for_food(food, role=role)
        items_by_role[role].extend(portions)

    # 5. Generate Bounded Combinations
    raw_candidates, search_truncated, evaluated_count, eligible_count = generate_bounded_combinations(
        slot=slot,
        items_by_role=items_by_role,
    )

    # 6. Deterministic Ranking (FOOD_CANDIDATE_RANKING_V01)
    ranked_candidates = rank_candidates(raw_candidates)[:CandidatePolicy.MAX_CANDIDATES_RETURNED]

    # 7. Resolve Final Status
    if not ranked_candidates:
        status = CandidateGenerationStatus.NO_STRICT_MATCH
    else:
        has_strict = any(c.match_status == CandidateMatchStatus.STRICT_MATCH for c in ranked_candidates)
        status = CandidateGenerationStatus.CANDIDATES_FOUND if has_strict else CandidateGenerationStatus.NO_STRICT_MATCH

    return FoodCandidateGenerationResultDTO(
        slot_id=slot.slot_id,
        status=status,
        candidate_count=len(ranked_candidates),
        candidates=ranked_candidates,
        evaluated_candidate_count=evaluated_count,
        eligible_candidate_count=eligible_count,
        returned_candidate_count=len(ranked_candidates),
        rejected_counts_by_reason=dict(rejected_counts),
        search_truncated=search_truncated,
        policy_version=CandidatePolicy.VERSION,
        ranking_policy_version=CandidatePolicy.RANKING_POLICY_VERSION,
    )
