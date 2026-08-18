import pytest
from app.engine.step_sizing import (
    normalize_midnight_delta,
    calculate_daily_target_times,
)


def test_normalize_midnight_delta_standard():
    # Target 07:00, Actual 07:15 -> +15m late
    assert normalize_midnight_delta("07:15", "07:00") == 15
    # Target 07:00, Actual 06:50 -> -10m early
    assert normalize_midnight_delta("06:50", "07:00") == -10


def test_normalize_midnight_delta_across_midnight():
    # Target 00:15 (past midnight), Actual 23:55 (before midnight) -> -20m early
    assert normalize_midnight_delta("23:55", "00:15") == -20
    # Target 23:45, Actual 00:10 -> +25m late
    assert normalize_midnight_delta("00:10", "23:45") == 25


def test_calculate_daily_target_times_progression():
    # Baseline wake: 10:00, Target: 08:00 (120 min reduction)
    # Step size: 15 min per 2 days
    # Day 1: 10:00
    # Day 2: 10:00 (step 0)
    # Day 3: 09:45 (step 1 = -15m)
    # Day 4: 09:45
    # Day 5: 09:30 (step 2 = -30m)
    d1 = calculate_daily_target_times("10:00", "08:00", "02:00", "00:00", current_day=1, total_days=20)
    assert d1["target_wake_time"] == "10:00"
    assert d1["target_bedtime"] == "02:00"

    d3 = calculate_daily_target_times("10:00", "08:00", "02:00", "00:00", current_day=3, total_days=20)
    assert d3["target_wake_time"] == "09:45"
    assert d3["target_bedtime"] == "01:45"

    d5 = calculate_daily_target_times("10:00", "08:00", "02:00", "00:00", current_day=5, total_days=20)
    assert d5["target_wake_time"] == "09:30"
    assert d5["target_bedtime"] == "01:30"
