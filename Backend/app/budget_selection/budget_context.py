from typing import Tuple, Optional
from app.budget_selection.constants import (
    BudgetPeriod,
    BudgetSource,
    BudgetSelectionStatus,
    BudgetSelectionPolicy,
)
from app.budget_selection.models import BudgetContextDTO


def derive_daily_budget_envelope(
    budget_context: Optional[BudgetContextDTO],
) -> Tuple[Optional[int], BudgetSelectionStatus, str]:
    """
    Derives the daily planning budget envelope according to BUDGET_ALLOCATION_V01.
    Follows strict priority:
    1. Explicit today budget
    2. Authoritative remaining period budget / days remaining
    3. Total minus known spent budget / days remaining
    Invariant: Unknown spend is NOT assumed to be 0 for multi-day periods.
    Invariant: Negative remaining budget returns BUDGET_ALREADY_EXCEEDED.
    """
    if budget_context is None or budget_context.total_food_budget_idr <= 0:
        return None, BudgetSelectionStatus.BUDGET_NOT_CONFIGURED, "No food budget configured."

    # Priority 1: Explicit daily override
    if budget_context.explicit_today_budget_idr is not None:
        if budget_context.explicit_today_budget_idr < 0:
            return None, BudgetSelectionStatus.BUDGET_ALREADY_EXCEEDED, "Explicit daily budget is negative."
        return (
            budget_context.explicit_today_budget_idr,
            BudgetSelectionStatus.SELECTION_FOUND,
            "Using explicit user-declared daily budget.",
        )

    # Priority 2: Authoritative remaining budget
    if budget_context.remaining_food_budget_idr is not None:
        if budget_context.remaining_food_budget_idr < 0:
            return None, BudgetSelectionStatus.BUDGET_ALREADY_EXCEEDED, "Remaining period budget is already exceeded."
        days = max(1, budget_context.period_days_remaining)
        today_envelope = budget_context.remaining_food_budget_idr // days
        return (
            today_envelope,
            BudgetSelectionStatus.SELECTION_FOUND,
            f"Derived from remaining budget Rp{budget_context.remaining_food_budget_idr} over {days} days.",
        )

    # Priority 3: Total minus known spent
    if budget_context.spent_food_budget_idr is not None:
        remaining = budget_context.total_food_budget_idr - budget_context.spent_food_budget_idr
        if remaining < 0:
            return None, BudgetSelectionStatus.BUDGET_ALREADY_EXCEEDED, "Spent amount exceeds total period budget."
        days = max(1, budget_context.period_days_remaining)
        today_envelope = remaining // days
        return (
            today_envelope,
            BudgetSelectionStatus.SELECTION_FOUND,
            f"Derived from total Rp{budget_context.total_food_budget_idr} minus spent Rp{budget_context.spent_food_budget_idr} over {days} days.",
        )

    # For DAILY period without spent specified, full budget is available today
    if budget_context.budget_period == BudgetPeriod.DAILY:
        return (
            budget_context.total_food_budget_idr,
            BudgetSelectionStatus.SELECTION_FOUND,
            "Using daily declared budget.",
        )

    # Multi-day period where spent is unknown -> cannot safely assume spend is 0!
    return (
        None,
        BudgetSelectionStatus.NEEDS_MORE_BUDGET_DATA,
        "Period spending is unknown; cannot derive remaining daily envelope safely.",
    )
