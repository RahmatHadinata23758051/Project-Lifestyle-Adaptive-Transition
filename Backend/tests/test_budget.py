import pytest
from app.engine.budget import (
    calculate_daily_budget_cap,
    rebalance_daily_budget,
)


def test_calculate_daily_budget_cap():
    assert calculate_daily_budget_cap(350000.0, 7) == 50000.0
    with pytest.raises(ValueError):
        calculate_daily_budget_cap(-1000.0)


def test_rebalance_daily_budget_normal():
    result = rebalance_daily_budget(
        weekly_budget=350000.0,
        total_spent_so_far=100000.0,
        remaining_days=5,
    )
    assert result["remaining_budget"] == 250000.0
    assert result["new_daily_budget_cap"] == 50000.0
    assert result["is_overbudget"] is False


def test_rebalance_daily_budget_overspending():
    result = rebalance_daily_budget(
        weekly_budget=350000.0,
        total_spent_so_far=380000.0,
        remaining_days=2,
    )
    assert result["remaining_budget"] == -30000.0
    assert result["new_daily_budget_cap"] == 0.0
    assert result["is_overbudget"] is True
    assert result["overbudget_amount"] == 30000.0


def test_rebalance_daily_budget_zero_remaining_days():
    # When remaining_days == 0, new daily cap is 0.0
    result = rebalance_daily_budget(
        weekly_budget=350000.0,
        total_spent_so_far=300000.0,
        remaining_days=0,
    )
    assert result["new_daily_budget_cap"] == 0.0
    assert result["remaining_budget"] == 50000.0
    assert result["is_overbudget"] is False


def test_rebalance_daily_budget_negative_inputs_rejected():
    with pytest.raises(ValueError):
        rebalance_daily_budget(-100.0, 50.0, 5)
    with pytest.raises(ValueError):
        rebalance_daily_budget(100.0, -50.0, 5)
    with pytest.raises(ValueError):
        rebalance_daily_budget(100.0, 50.0, -2)
