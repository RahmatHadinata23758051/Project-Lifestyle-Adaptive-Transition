import hashlib
from typing import List, Dict
from app.budget_selection.constants import (
    CandidateBudgetStatus,
    BudgetSelectionPolicy,
)
from app.budget_selection.models import (
    BudgetCandidateEvaluationDTO,
    DailyCandidateCombinationDTO,
)
from app.price_knowledge.constants import PriceConfidence
from app.food_candidates.constants import CandidateMatchStatus


def _get_weakest_confidence(confidences: List[PriceConfidence]) -> PriceConfidence:
    if not confidences:
        return PriceConfidence.UNKNOWN
    if PriceConfidence.UNKNOWN in confidences:
        return PriceConfidence.UNKNOWN
    if PriceConfidence.LOW in confidences:
        return PriceConfidence.LOW
    if PriceConfidence.MEDIUM in confidences:
        return PriceConfidence.MEDIUM
    return PriceConfidence.HIGH


def build_daily_combination(
    selections_by_slot: Dict[str, BudgetCandidateEvaluationDTO],
    budget_envelope_idr: int,
) -> DailyCandidateCombinationDTO:
    """
    Builds a DailyCandidateCombinationDTO from selected candidate evaluations.
    """
    total_cost = sum(eval_dto.estimated_cost_idr or 0 for eval_dto in selections_by_slot.values())
    remaining = budget_envelope_idr - total_cost

    confidences = [eval_dto.price_confidence for eval_dto in selections_by_slot.values()]
    comb_conf = _get_weakest_confidence(confidences)
    uses_stale = any(eval_dto.uses_stale_prices for eval_dto in selections_by_slot.values())

    total_dev = sum(eval_dto.absolute_energy_deviation for eval_dto in selections_by_slot.values())
    total_pref = sum(eval_dto.preference_score for eval_dto in selections_by_slot.values())
    all_strict = all(eval_dto.nutrition_fit_status == CandidateMatchStatus.STRICT_MATCH for eval_dto in selections_by_slot.values())

    # Deterministic stable combination ID
    cand_ids = sorted([f"{slot}:{eval_dto.candidate_id}" for slot, eval_dto in selections_by_slot.items()])
    comb_id = "comb_" + hashlib.sha256(";".join(cand_ids).encode("utf-8")).hexdigest()[:16]

    return DailyCandidateCombinationDTO(
        combination_id=comb_id,
        selections=selections_by_slot,
        total_estimated_cost_idr=total_cost,
        budget_envelope_idr=budget_envelope_idr,
        remaining_after_selection_idr=remaining,
        price_confidence=comb_conf,
        uses_stale_prices=uses_stale,
        nutrition_deviation_score=round(total_dev, 2),
        preference_score=total_pref,
        all_strict_nutrition=all_strict,
    )


def rank_combinations(
    combinations: List[DailyCandidateCombinationDTO],
) -> List[DailyCandidateCombinationDTO]:
    """
    Ranks daily candidate combinations using BUDGET_SELECTION_RANKING_V01:
    1. Feasible within budget envelope (remaining >= 0)
    2. Fresh/Aging prices preferred over Stale prices (stale is fallback only)
    3. All STRICT_MATCH nutrition fit preferred over combinations with NEAR_MATCH
    4. Higher price confidence (HIGH > MEDIUM > LOW)
    5. Lowest total absolute energy deviation
    6. Highest user preference score
    7. Lower total cost (secondary tie-break, not cheapest-by-default)
    8. Stable combination ID hash
    """
    conf_rank = {
        PriceConfidence.HIGH: 3,
        PriceConfidence.MEDIUM: 2,
        PriceConfidence.LOW: 1,
        PriceConfidence.UNKNOWN: 0,
    }

    def sort_key(c: DailyCandidateCombinationDTO):
        is_within_budget = 1 if c.remaining_after_selection_idr >= 0 else 0
        is_fresh = 0 if c.uses_stale_prices else 1  # Fresh/Aging gets 1, Stale gets 0
        nutrition_tier = 1 if c.all_strict_nutrition else 0
        c_conf = conf_rank.get(c.price_confidence, 0)
        return (
            is_within_budget,             # 1 (feasible) before 0 (over-budget)
            is_fresh,                     # 1 (fresh/aging) before 0 (stale fallback)
            nutrition_tier,               # 1 (all strict) before 0 (near match present)
            c_conf,                       # 3 (HIGH) before 2 before 1
            -c.nutrition_deviation_score, # Lower deviation is better
            c.preference_score,           # Higher preference is better
            -c.total_estimated_cost_idr,   # Lower cost as secondary tie-break
            c.combination_id,             # Stable tie-break
        )

    return sorted(combinations, key=sort_key, reverse=True)
