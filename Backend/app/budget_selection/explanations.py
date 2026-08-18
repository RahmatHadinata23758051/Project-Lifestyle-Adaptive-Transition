from typing import List, Optional
from app.budget_selection.constants import BudgetSelectionStatus
from app.budget_selection.models import DailyCandidateCombinationDTO
from app.price_knowledge.constants import PriceConfidence


def generate_selection_explanations(
    status: BudgetSelectionStatus,
    budget_envelope_idr: Optional[int],
    selected_combination: Optional[DailyCandidateCombinationDTO],
    shortfall_idr: Optional[int] = None,
) -> List[str]:
    """
    Produces deterministic structured explanations for Budget Selection results.
    """
    explanations = []

    if status == BudgetSelectionStatus.SELECTION_FOUND:
        cost = selected_combination.total_estimated_cost_idr if selected_combination else 0
        rem = selected_combination.remaining_after_selection_idr if selected_combination else 0
        explanations.append(
            f"Found feasible daily combination covering all active meal slots with total cost Rp{cost:,} (within budget envelope Rp{budget_envelope_idr:,}, remaining Rp{rem:,})."
        )
        if selected_combination and selected_combination.all_strict_nutrition:
            explanations.append("All selected slot candidates strictly match target meal energy ranges.")

    elif status == BudgetSelectionStatus.SELECTION_FOUND_WITH_LOW_CONFIDENCE_PRICE:
        cost = selected_combination.total_estimated_cost_idr if selected_combination else 0
        explanations.append(
            f"Found daily candidate combination costing Rp{cost:,}, but selection relies on low-confidence or aging/stale price observations."
        )

    elif status == BudgetSelectionStatus.NO_BUDGET_FEASIBLE_SELECTION:
        if shortfall_idr is not None and budget_envelope_idr is not None:
            min_cost = budget_envelope_idr + shortfall_idr
            explanations.append(
                f"No nutritionally eligible candidate combination fits the daily budget envelope of Rp{budget_envelope_idr:,}. Minimum viable complete combination costs Rp{min_cost:,} (shortfall Rp{shortfall_idr:,})."
            )
        else:
            explanations.append("No candidate combination meets all slot targets within the daily budget envelope.")

    elif status == BudgetSelectionStatus.NEEDS_MORE_PRICE_DATA:
        explanations.append(
            "One or more active meal slots lack complete price evidence. Missing price data is not assumed to be zero."
        )

    elif status == BudgetSelectionStatus.BUDGET_ALREADY_EXCEEDED:
        explanations.append("Current period food budget is already exceeded (remaining budget is negative).")

    elif status == BudgetSelectionStatus.NEEDS_MORE_BUDGET_DATA:
        explanations.append(
            "Period food spending data is unknown; cannot derive a safe remaining daily budget envelope."
        )

    elif status == BudgetSelectionStatus.BUDGET_NOT_CONFIGURED:
        explanations.append("User food budget has not been declared or configured.")

    elif status == BudgetSelectionStatus.NO_ELIGIBLE_CANDIDATES:
        explanations.append("No nutritionally eligible food candidates found for one or more active meal slots.")

    return explanations
