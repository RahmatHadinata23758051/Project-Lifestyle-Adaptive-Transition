from typing import List, Dict, Tuple, Optional
import itertools
from app.budget_selection.constants import (
    CandidateBudgetStatus,
    BudgetSelectionPolicy,
)
from app.budget_selection.models import (
    BudgetCandidateEvaluationDTO,
    DailyCandidateCombinationDTO,
)
from app.budget_selection.scoring import build_daily_combination


def generate_bounded_daily_combinations(
    slot_ids: List[str],
    candidates_by_slot: Dict[str, List[BudgetCandidateEvaluationDTO]],
    budget_envelope_idr: int,
) -> Tuple[List[DailyCandidateCombinationDTO], bool, int, Optional[int]]:
    """
    Performs bounded deterministic daily candidate combination search (BUDGET_SELECTION_SEARCH_V01).
    Invariant: search_truncated is True if EITHER any per-slot pool was truncated OR the combinatorial search hit its evaluation cap.
    Returns (combinations, search_truncated, evaluated_count, min_combination_cost_found).
    """
    if not slot_ids:
        return [], False, 0, None

    per_slot_truncated = False
    valid_pools: List[List[BudgetCandidateEvaluationDTO]] = []

    for slot_id in slot_ids:
        pool = candidates_by_slot.get(slot_id, [])
        complete_candidates = [
            c for c in pool if c.estimated_cost_idr is not None and c.budget_status != CandidateBudgetStatus.UNKNOWN_COST
        ]

        if len(complete_candidates) > BudgetSelectionPolicy.MAX_CANDIDATES_PER_SLOT_FOR_BUDGET_SEARCH:
            per_slot_truncated = True

        # Bounded slice per slot
        bounded_pool = complete_candidates[: BudgetSelectionPolicy.MAX_CANDIDATES_PER_SLOT_FOR_BUDGET_SEARCH]
        if not bounded_pool:
            # At least one slot has no complete-cost candidate
            return [], False, 0, None
        valid_pools.append(bounded_pool)

    # Combinatorial search with early pruning and evaluation counter
    evaluated_count = 0
    combination_truncated = False
    all_combinations: List[DailyCandidateCombinationDTO] = []
    min_cost_found: Optional[int] = None

    for prod in itertools.product(*valid_pools):
        if evaluated_count >= BudgetSelectionPolicy.MAX_DAILY_COMBINATIONS_EVALUATED:
            combination_truncated = True
            break

        evaluated_count += 1
        selections_by_slot = {slot_ids[idx]: prod[idx] for idx in range(len(slot_ids))}
        comb = build_daily_combination(selections_by_slot, budget_envelope_idr)

        if min_cost_found is None or comb.total_estimated_cost_idr < min_cost_found:
            min_cost_found = comb.total_estimated_cost_idr

        all_combinations.append(comb)

    search_truncated = per_slot_truncated or combination_truncated
    return all_combinations, search_truncated, evaluated_count, min_cost_found
