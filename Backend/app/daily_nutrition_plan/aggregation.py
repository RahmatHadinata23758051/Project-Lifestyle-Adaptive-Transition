from typing import Dict, List, Optional
from app.daily_nutrition_plan.constants import MacroCompleteness
from app.daily_nutrition_plan.models import (
    DailyNutritionSummaryDTO,
    DailyBudgetSummaryDTO,
)
from app.food_candidates.models import FoodCandidateSetDTO
from app.food_candidates.constants import CandidateMatchStatus
from app.price_knowledge.models import CandidateCostEstimateDTO
from app.price_knowledge.constants import PriceConfidence, CostCompleteness
from app.budget_selection.constants import BudgetSource


def aggregate_daily_nutrition(
    candidates_by_slot: Dict[str, FoodCandidateSetDTO],
    target_energy_kcal: float,
) -> DailyNutritionSummaryDTO:
    """
    Aggregates planned daily energy and macronutrients from selected candidates.
    Invariant: unknown != 0. If any candidate lacks macro values, macro completeness is PARTIAL.
    """
    total_energy = 0.0
    total_protein = 0.0
    total_fat = 0.0
    total_carbs = 0.0
    macro_partial = False
    strict_count = 0
    near_count = 0

    for cand in candidates_by_slot.values():
        total_energy += cand.total_energy_kcal

        if cand.total_protein_g is not None:
            total_protein += cand.total_protein_g
        else:
            macro_partial = True

        if cand.total_fat_g is not None:
            total_fat += cand.total_fat_g
        else:
            macro_partial = True

        if cand.total_carbohydrate_g is not None:
            total_carbs += cand.total_carbohydrate_g
        else:
            macro_partial = True

        if cand.match_status == CandidateMatchStatus.STRICT_MATCH:
            strict_count += 1
        elif cand.match_status == CandidateMatchStatus.NEAR_MATCH:
            near_count += 1

    diff = total_energy - target_energy_kcal

    return DailyNutritionSummaryDTO(
        target_energy_kcal=round(target_energy_kcal, 1),
        planned_energy_kcal=round(total_energy, 1),
        energy_difference_kcal=round(diff, 1),
        planned_protein_g=round(total_protein, 1) if not macro_partial else None,
        planned_fat_g=round(total_fat, 1) if not macro_partial else None,
        planned_carbohydrate_g=round(total_carbs, 1) if not macro_partial else None,
        macro_completeness=MacroCompleteness.PARTIAL if macro_partial else MacroCompleteness.COMPLETE,
        strict_match_slot_count=strict_count,
        near_match_slot_count=near_count,
    )


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


def aggregate_daily_budget(
    candidates_by_slot: Dict[str, FoodCandidateSetDTO],
    candidate_costs_by_candidate_id: Dict[str, CandidateCostEstimateDTO],
    budget_envelope_idr: Optional[int],
    budget_source: BudgetSource = BudgetSource.USER_DECLARED,
) -> DailyBudgetSummaryDTO:
    """
    Aggregates planned daily cost and financial envelope.
    """
    total_cost = 0
    all_complete = True
    any_available = False
    confidences: List[PriceConfidence] = []
    uses_stale = False

    for cand in candidates_by_slot.values():
        cost_dto = candidate_costs_by_candidate_id.get(cand.candidate_id)
        if cost_dto is not None:
            any_available = True
            if cost_dto.cost_completeness == CostCompleteness.COMPLETE and cost_dto.estimated_cost_idr is not None:
                total_cost += cost_dto.estimated_cost_idr
            else:
                all_complete = False

            confidences.append(cost_dto.confidence)
            if cost_dto.uses_stale_prices:
                uses_stale = True
        else:
            all_complete = False

    if not any_available:
        completeness = CostCompleteness.UNAVAILABLE
    elif all_complete:
        completeness = CostCompleteness.COMPLETE
    else:
        completeness = CostCompleteness.PARTIAL

    comb_conf = _get_weakest_confidence(confidences)
    remaining = (budget_envelope_idr - total_cost) if (budget_envelope_idr is not None and completeness == CostCompleteness.COMPLETE) else None

    return DailyBudgetSummaryDTO(
        budget_envelope_idr=budget_envelope_idr,
        planned_cost_idr=total_cost if completeness == CostCompleteness.COMPLETE else None,
        remaining_after_plan_idr=remaining,
        cost_completeness=completeness,
        price_confidence=comb_conf,
        uses_stale_prices=uses_stale,
        budget_source=budget_source,
    )
