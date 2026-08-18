from typing import Dict, List, Optional, Tuple, Any
from app.daily_nutrition_plan.constants import DailyPlanStatus
from app.budget_selection.constants import BudgetSelectionStatus
from app.food_candidates.models import FoodCandidateSetDTO
from app.price_knowledge.models import CandidateCostEstimateDTO
from app.price_knowledge.constants import CostCompleteness


def validate_nutrition_eligibility(status: Any) -> Optional[DailyPlanStatus]:
    """
    Evaluates Nutrition Core eligibility gate.
    """
    val = getattr(status, "value", status)
    normalized = str(val).upper().strip()
    if "ELIGIBLE" in normalized and not any(k in normalized for k in ("NOT_ELIGIBLE", "OUT_OF_SCOPE", "BLOCKED")):
        return None
    if "NEEDS_MORE_DATA" in normalized:
        return DailyPlanStatus.NEEDS_MORE_DATA
    if any(k in normalized for k in ("OUT_OF_SCOPE", "NOT_ELIGIBLE", "BLOCKED")):
        return DailyPlanStatus.NOT_ELIGIBLE
    return DailyPlanStatus.NOT_ELIGIBLE


def validate_meal_schedule_feasibility(schedule_status: Any) -> Optional[DailyPlanStatus]:
    """
    Evaluates Meal Structure feasibility gate.
    """
    val = getattr(schedule_status, "value", schedule_status)
    normalized = str(val).upper().strip()
    if "FEASIBLE" in normalized and "INFEASIBLE" not in normalized:
        return None
    if "NEEDS_MORE_DATA" in normalized:
        return DailyPlanStatus.NEEDS_MORE_DATA
    if "INFEASIBLE" in normalized:
        return DailyPlanStatus.INFEASIBLE
    return DailyPlanStatus.INFEASIBLE


def validate_budget_selection_status(
    status: Any,
) -> Optional[DailyPlanStatus]:
    """
    Evaluates Budget Selection status gate.
    """
    val = getattr(status, "value", status)
    normalized = str(val).upper().strip()

    if any(k in normalized for k in ("SELECTION_FOUND", "SELECTION_FOUND_WITH_LOW_CONFIDENCE_PRICE")):
        return None
    if "SEARCH_INCOMPLETE" in normalized:
        return DailyPlanStatus.SEARCH_INCOMPLETE
    if any(k in normalized for k in ("NEEDS_MORE_PRICE_DATA", "NEEDS_MORE_BUDGET_DATA", "BUDGET_NOT_CONFIGURED")):
        return DailyPlanStatus.NEEDS_MORE_DATA
    if any(k in normalized for k in ("NO_BUDGET_FEASIBLE_SELECTION", "BUDGET_ALREADY_EXCEEDED", "BUDGET_CONTEXT_CONFLICT", "NO_ELIGIBLE_CANDIDATES")):
        return DailyPlanStatus.INFEASIBLE
    return DailyPlanStatus.INFEASIBLE


def validate_slot_integrity(
    active_slot_ids: List[str],
    selected_candidates_by_slot: Dict[str, FoodCandidateSetDTO],
) -> Tuple[bool, Optional[str]]:
    """
    Validates that:
    1. Every active slot has exactly one candidate selected.
    2. No unknown slot_id is present.
    3. candidate.slot_id matches key slot_id.
    """
    active_set = set(active_slot_ids)
    selected_set = set(selected_candidates_by_slot.keys())

    missing = active_set - selected_set
    if missing:
        return False, f"Active meal slots missing candidate selections: {sorted(list(missing))}"

    unknown = selected_set - active_set
    if unknown:
        return False, f"Selected candidate references unknown or inactive slots: {sorted(list(unknown))}"

    for slot_id, cand in selected_candidates_by_slot.items():
        if cand.slot_id != slot_id:
            return False, f"Candidate {cand.candidate_id} belongs to slot {cand.slot_id}, but was assigned to slot {slot_id}."

    return True, None


def validate_cost_consistency(
    selected_candidates_by_slot: Dict[str, FoodCandidateSetDTO],
    candidate_costs_by_candidate_id: Dict[str, CandidateCostEstimateDTO],
    budget_selection_total_idr: Optional[int],
) -> Tuple[bool, Optional[str]]:
    """
    Validates that sum of selected candidate costs strictly matches budget selection total.
    """
    if budget_selection_total_idr is None:
        return True, None

    summed_cost = 0
    for cand in selected_candidates_by_slot.values():
        cost_dto = candidate_costs_by_candidate_id.get(cand.candidate_id)
        if cost_dto is None:
            return False, f"Candidate {cand.candidate_id} has no cost estimate DTO."
        if cost_dto.cost_completeness == CostCompleteness.COMPLETE and cost_dto.estimated_cost_idr is not None:
            summed_cost += cost_dto.estimated_cost_idr
        else:
            return False, f"Candidate {cand.candidate_id} cost is not complete."

    if summed_cost != budget_selection_total_idr:
        return False, f"Sum of candidate costs ({summed_cost}) does not match budget selection total ({budget_selection_total_idr})."

    return True, None
