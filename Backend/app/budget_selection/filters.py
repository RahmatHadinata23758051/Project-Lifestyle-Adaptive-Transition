from typing import Optional, Dict
from app.budget_selection.constants import CandidateBudgetStatus
from app.budget_selection.models import BudgetCandidateEvaluationDTO
from app.price_knowledge.constants import CostCompleteness, PriceConfidence
from app.price_knowledge.models import CandidateCostEstimateDTO
from app.food_candidates.models import FoodCandidateSetDTO


def evaluate_candidate_price_and_budget(
    candidate: FoodCandidateSetDTO,
    cost_estimate: Optional[CandidateCostEstimateDTO],
    budget_envelope_idr: Optional[int] = None,
    user_preferences: Optional[Dict[str, int]] = None,
) -> BudgetCandidateEvaluationDTO:
    """
    Evaluates candidate price readiness, budget status, and user preference score.
    Invariant: PARTIAL or UNAVAILABLE cost is marked UNKNOWN_COST (never assumed 0 or cheap).
    """
    prefs = user_preferences or {}
    pref_score = sum(prefs.get(item.food_item_id, 0) for item in candidate.items)

    if cost_estimate is None or cost_estimate.cost_completeness != CostCompleteness.COMPLETE:
        return BudgetCandidateEvaluationDTO(
            candidate_id=candidate.candidate_id,
            slot_id=candidate.slot_id,
            estimated_cost_idr=None,
            budget_status=CandidateBudgetStatus.UNKNOWN_COST,
            price_confidence=PriceConfidence.UNKNOWN,
            uses_stale_prices=False,
            nutrition_fit_status=candidate.match_status,
            preference_score=pref_score,
            absolute_energy_deviation=candidate.absolute_energy_deviation,
            explanations=["Price data is incomplete or unavailable; cost cannot be verified."],
        )

    estimated_cost = cost_estimate.estimated_cost_idr
    confidence = cost_estimate.confidence
    uses_stale = cost_estimate.uses_stale_prices

    # Evaluate against daily envelope (as a loose individual upper bound or label)
    if budget_envelope_idr is not None and estimated_cost is not None and estimated_cost > budget_envelope_idr:
        budget_status = CandidateBudgetStatus.OVER_BUDGET
        explanation = f"Estimated candidate cost Rp{estimated_cost} exceeds full daily budget envelope Rp{budget_envelope_idr}."
    elif confidence == PriceConfidence.LOW or uses_stale:
        budget_status = CandidateBudgetStatus.LOW_CONFIDENCE_COST
        explanation = f"Estimated candidate cost Rp{estimated_cost} is complete but relies on low confidence/stale prices."
    else:
        budget_status = CandidateBudgetStatus.WITHIN_BUDGET
        explanation = f"Estimated candidate cost Rp{estimated_cost} is complete and within reasonable budget envelope."

    return BudgetCandidateEvaluationDTO(
        candidate_id=candidate.candidate_id,
        slot_id=candidate.slot_id,
        estimated_cost_idr=estimated_cost,
        budget_status=budget_status,
        price_confidence=confidence,
        uses_stale_prices=uses_stale,
        nutrition_fit_status=candidate.match_status,
        preference_score=pref_score,
        absolute_energy_deviation=candidate.absolute_energy_deviation,
        explanations=[explanation],
    )
