from typing import List, Dict, Tuple
from app.meal_structure.constants import MealSlotType
from app.meal_structure.models import MealSlotDTO
from app.food_candidates.constants import FoodPlannerRole, CandidatePolicy
from app.food_candidates.models import FoodCandidateItemDTO, FoodCandidateSetDTO
from app.food_candidates.scoring import build_candidate_set


def generate_bounded_combinations(
    slot: MealSlotDTO,
    items_by_role: Dict[FoodPlannerRole, List[FoodCandidateItemDTO]],
) -> Tuple[List[FoodCandidateSetDTO], bool, int, int]:
    """
    Generates deterministic bounded food combinations for a meal slot.
    - MAIN_MEAL: Staple + Protein (+ optional Vegetable/Fruit)
    - SNACK: 1 or 2 Snack items / Fruits
    Early pruning stops search when cumulative calories exceed near-match upper bound.
    Returns (candidates, search_truncated, evaluated_count, eligible_count).
    """
    candidates: List[FoodCandidateSetDTO] = []
    seen_sigs = set()
    search_truncated = False
    evaluated_count = 0
    eligible_count = 0

    max_energy_cutoff = (slot.max_kcal + (slot.target_kcal * CandidatePolicy.NEAR_MATCH_EXTENSION_RATIO)) * 1.1

    # Deterministic sorting of pool items prior to truncation
    def item_sort_key(i: FoodCandidateItemDTO):
        return (i.canonical_name, i.food_item_id, i.grams)

    staples = sorted(items_by_role.get(FoodPlannerRole.STAPLE, []), key=item_sort_key)[:CandidatePolicy.MAX_POOL_PER_ROLE]
    proteins = sorted(items_by_role.get(FoodPlannerRole.PROTEIN_SOURCE, []), key=item_sort_key)[:CandidatePolicy.MAX_POOL_PER_ROLE]
    vegetables = sorted(items_by_role.get(FoodPlannerRole.VEGETABLE, []), key=item_sort_key)[:CandidatePolicy.MAX_POOL_PER_ROLE]
    fruits = sorted(items_by_role.get(FoodPlannerRole.FRUIT, []), key=item_sort_key)[:CandidatePolicy.MAX_POOL_PER_ROLE]
    snacks = sorted(items_by_role.get(FoodPlannerRole.SNACK_ITEM, []), key=item_sort_key)[:CandidatePolicy.MAX_POOL_PER_ROLE]

    if slot.slot_type == MealSlotType.MAIN_MEAL:
        # 1. Staple + Protein (2 items)
        for st in staples:
            for pr in proteins:
                if st.food_item_id == pr.food_item_id:
                    continue
                evaluated_count += 1
                pair = [st, pr]
                tot_e = sum(i.energy_kcal for i in pair)
                if tot_e > max_energy_cutoff:
                    continue  # Early prune

                sig = "-".join(sorted(f"{i.food_item_id}:{i.grams:.0f}" for i in pair))
                if sig not in seen_sigs:
                    seen_sigs.add(sig)
                    c_set = build_candidate_set(slot, pair)
                    if c_set.match_status != c_set.match_status.INELIGIBLE:
                        eligible_count += 1
                        candidates.append(c_set)

                # 2. Staple + Protein + Vegetable/Fruit (3 items)
                for side in (vegetables + fruits)[:5]:
                    if side.food_item_id in (st.food_item_id, pr.food_item_id):
                        continue
                    evaluated_count += 1
                    trio = [st, pr, side]
                    tot_e3 = sum(i.energy_kcal for i in trio)
                    if tot_e3 > max_energy_cutoff:
                        continue

                    sig3 = "-".join(sorted(f"{i.food_item_id}:{i.grams:.0f}" for i in trio))
                    if sig3 not in seen_sigs:
                        seen_sigs.add(sig3)
                        c_set3 = build_candidate_set(slot, trio)
                        if c_set3.match_status != c_set3.match_status.INELIGIBLE:
                            eligible_count += 1
                            candidates.append(c_set3)

                if len(candidates) >= CandidatePolicy.MAX_CANDIDATES_RETURNED * 3:
                    search_truncated = True
                    break
            if len(candidates) >= CandidatePolicy.MAX_CANDIDATES_RETURNED * 3:
                break

    else:
        # SNACK SLOT: 1 item or 2 items
        snack_pool = sorted((snacks + fruits + staples), key=item_sort_key)[:CandidatePolicy.MAX_POOL_PER_ROLE]

        # 1-item snack
        for sn in snack_pool:
            evaluated_count += 1
            c_set = build_candidate_set(slot, [sn])
            if c_set.match_status != c_set.match_status.INELIGIBLE:
                eligible_count += 1
                candidates.append(c_set)

        # 2-item snack
        for i in range(len(snack_pool)):
            for j in range(i + 1, len(snack_pool)):
                s1 = snack_pool[i]
                s2 = snack_pool[j]
                if s1.food_item_id == s2.food_item_id:
                    continue
                evaluated_count += 1
                pair = [s1, s2]
                tot_e = sum(x.energy_kcal for x in pair)
                if tot_e > max_energy_cutoff:
                    continue

                sig = "-".join(sorted(f"{x.food_item_id}:{x.grams:.0f}" for x in pair))
                if sig not in seen_sigs:
                    seen_sigs.add(sig)
                    c_set = build_candidate_set(slot, pair)
                    if c_set.match_status != c_set.match_status.INELIGIBLE:
                        eligible_count += 1
                        candidates.append(c_set)

                if len(candidates) >= CandidatePolicy.MAX_CANDIDATES_RETURNED * 2:
                    search_truncated = True
                    break

    return candidates, search_truncated, evaluated_count, eligible_count
