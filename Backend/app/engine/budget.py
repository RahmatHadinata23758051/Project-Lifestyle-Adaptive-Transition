from typing import Dict, Any


def calculate_daily_budget_cap(weekly_budget: float, total_days: int = 7) -> float:
    """Calculate the baseline daily budget allowance from weekly budget."""
    if total_days <= 0:
        raise ValueError("Total days must be greater than zero.")
    if weekly_budget < 0:
        raise ValueError("Weekly budget cannot be negative.")
    return round(weekly_budget / total_days, 2)


def rebalance_daily_budget(
    weekly_budget: float,
    total_spent_so_far: float,
    remaining_days: int,
) -> Dict[str, Any]:
    """
    Recalculate remaining daily budget allocation based on actual spending.
    Rejects negative parameters.
    """
    if weekly_budget < 0:
        raise ValueError("Weekly budget cannot be negative.")
    if total_spent_so_far < 0:
        raise ValueError("Total spent so far cannot be negative.")
    if remaining_days < 0:
        raise ValueError("Remaining days cannot be negative.")

    if remaining_days == 0:
        remaining_budget = weekly_budget - total_spent_so_far
        return {
            "remaining_budget": round(remaining_budget, 2),
            "new_daily_budget_cap": 0.0,
            "is_overbudget": total_spent_so_far > weekly_budget,
            "overbudget_amount": max(0.0, round(total_spent_so_far - weekly_budget, 2)),
        }

    remaining_budget = weekly_budget - total_spent_so_far
    is_overbudget = remaining_budget < 0

    if is_overbudget:
        new_daily_cap = 0.0
    else:
        new_daily_cap = round(remaining_budget / remaining_days, 2)

    return {
        "remaining_budget": round(remaining_budget, 2),
        "new_daily_budget_cap": new_daily_cap,
        "is_overbudget": is_overbudget,
        "overbudget_amount": round(abs(remaining_budget), 2) if is_overbudget else 0.0,
    }
