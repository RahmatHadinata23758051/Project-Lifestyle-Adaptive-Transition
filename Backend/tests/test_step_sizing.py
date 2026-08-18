import pytest
from app.engine.step_sizing import (
    calculate_daily_target_times,
)


def test_calculate_daily_target_times_step_indexing():
    # Baseline wake: 10:00, Target: 08:00 (120 min reduction)
    # Step size: 15 min per step
    # Step 0: 10:00
    # Step 1: 09:45
    # Step 2: 09:30
    s0 = calculate_daily_target_times("10:00", "08:00", "02:00", "00:00", current_step_index=0)
    assert s0["target_wake_time"] == "10:00"
    assert s0["target_bedtime"] == "02:00"

    s1 = calculate_daily_target_times("10:00", "08:00", "02:00", "00:00", current_step_index=1)
    assert s1["target_wake_time"] == "09:45"
    assert s1["target_bedtime"] == "01:45"

    s2 = calculate_daily_target_times("10:00", "08:00", "02:00", "00:00", current_step_index=2)
    assert s2["target_wake_time"] == "09:30"
    assert s2["target_bedtime"] == "01:30"


def test_calculate_daily_target_times_hold_preserves_target():
    # Demonstrating Calendar Day != Transition Step:
    # If Day 5 is on Step 1 (due to HOLD), target remains 09:45
    d5_hold = calculate_daily_target_times("10:00", "08:00", "02:00", "00:00", current_step_index=1)
    assert d5_hold["target_wake_time"] == "09:45"


def test_calculate_daily_target_times_no_overshoot():
    # Baseline: 08:30, Target: 08:00 (30 min difference)
    # Step 10 (150 min shift) should not overshoot target 08:00
    s10 = calculate_daily_target_times("08:30", "08:00", "00:30", "00:00", current_step_index=10)
    assert s10["target_wake_time"] == "08:00"
    assert s10["target_bedtime"] == "00:00"
