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
    1. Explicit today budget (with conflict check against remaining period budget)
    2. Authoritative remaining period budget / days remaining
    3. Total minus known spent budget / days remaining

    Invariant: Unknown spend is NOT assumed to be 0 for multi-day periods.
    Invariant: Negative remaining budget returns BUDGET_ALREADY_EXCEEDED.
    Invariant: period_days_remaining must be strictly positive (> 0).
    Invariant: Floor division remainder (e.g. Rp100.000 // 3 = Rp33.333, remainder Rp1)
               remains safely in the overall period budget and is not lost.
    """
    if budget_context is None or budget_context.total_food_budget_idr <= 0:
        return None, BudgetSelectionStatus.BUDGET_NOT_CONFIGURED, "No food budget configured."

    # Priority 1: Explicit daily override (with single source of truth conflict check)
    if budget_context.explicit_today_budget_idr is not None:
        explicit_today = budget_context.explicit_today_budget_idr
        if explicit_today < 0:
            return None, BudgetSelectionStatus.BUDGET_ALREADY_EXCEEDED, "Explicit daily budget is negative."

        # Conflict check against remaining period budget
        if budget_context.remaining_food_budget_idr is not None:
            if explicit_today > budget_context.remaining_food_budget_idr:
                return (
                    None,
                    BudgetSelectionStatus.BUDGET_CONTEXT_CONFLICT,
                    f"Explicit daily budget Rp{explicit_today:,} exceeds remaining period budget Rp{budget_context.remaining_food_budget_idr:,}.",
                )
        elif budget_context.spent_food_budget_idr is not None:
            derived_remaining = budget_context.total_food_budget_idr - budget_context.spent_food_budget_idr
            if explicit_today > derived_remaining:
                return (
                    None,
                    BudgetSelectionStatus.BUDGET_CONTEXT_CONFLICT,
                    f"Explicit daily budget Rp{explicit_today:,} exceeds remaining period budget Rp{derived_remaining:,}.",
                )

        return (
            explicit_today,
            BudgetSelectionStatus.SELECTION_FOUND,
            "Using explicit user-declared daily budget.",
        )

    # Multi-day period requires strictly positive period_days_remaining
    if budget_context.budget_period != BudgetPeriod.DAILY:
        if budget_context.period_days_remaining is None or budget_context.period_days_remaining <= 0:
            return (
                None,
                BudgetSelectionStatus.NEEDS_MORE_BUDGET_DATA,
                "period_days_remaining must be strictly greater than 0 for multi-day budget periods.",
            )

    # Priority 2: Authoritative remaining budget
    if budget_context.remaining_food_budget_idr is not None:
        if budget_context.remaining_food_budget_idr < 0:
            return None, BudgetSelectionStatus.BUDGET_ALREADY_EXCEEDED, "Remaining period budget is already exceeded."
        days = budget_context.period_days_remaining
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
        days = budget_context.period_days_remaining
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
