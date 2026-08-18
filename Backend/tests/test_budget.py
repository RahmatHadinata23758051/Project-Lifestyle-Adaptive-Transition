import pytest
from app.engine.budget import (
    calculate_daily_budget_cap,
    rebalance_daily_budget,
)


def test_calculate_daily_budget_cap():
    # 350.000 weekly budget / 7 days = 50.000 / day
    assert calculate_daily_budget_cap(350000.0, 7) == 50000.0
    # Negative budget raises error
    with pytest.raises(ValueError):
        calculate_daily_budget_cap(-1000.0)


def test_rebalance_daily_budget_normal():
    # Weekly: 350.000. Spent: 100.000. Remaining days: 5.
    # Remaining budget: 250.000 / 5 days = 50.000 / day
    result = rebalance_daily_budget(
        weekly_budget=350000.0,
        total_spent_so_far=100000.0,
        remaining_days=5,
    )
    assert result["remaining_budget"] == 250000.0
    assert result["new_daily_budget_cap"] == 50000.0
    assert result["is_overbudget"] is False


def test_rebalance_daily_budget_overspending():
    # Weekly: 350.000. Spent: 380.000 (Overbudget by 30.000). Remaining days: 2.
    result = rebalance_daily_budget(
        weekly_budget=350000.0,
        total_spent_so_far=380000.0,
        remaining_days=2,
    )
    assert result["remaining_budget"] == -30000.0
    assert result["new_daily_budget_cap"] == 0.0
    assert result["is_overbudget"] is True
    assert result["overbudget_amount"] == 30000.0
