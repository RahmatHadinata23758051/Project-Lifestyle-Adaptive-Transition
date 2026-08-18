import pytest
from app.engine.feasibility import (
    evaluate_feasibility,
    calculate_time_delta_minutes,
    calculate_sleep_duration_hours,
    time_to_minutes,
    minutes_to_time,
)


def test_time_to_minutes_valid():
    assert time_to_minutes("00:00") == 0
    assert time_to_minutes("06:30") == 390
    assert time_to_minutes("13:00") == 780
    assert time_to_minutes("23:59") == 1439


def test_time_to_minutes_invalid():
    with pytest.raises(ValueError):
        time_to_minutes("24:00")
    with pytest.raises(ValueError):
        time_to_minutes("invalid")


def test_calculate_time_delta_minutes():
    # 13:00 to 06:00 (7 hours shift = 420 min)
    assert calculate_time_delta_minutes("13:00", "06:00") == 420
    # 02:00 to 02:30 (30 min)
    assert calculate_time_delta_minutes("02:00", "02:30") == 30
    # 23:00 to 01:00 (2 hours = 120 min)
    assert calculate_time_delta_minutes("23:00", "01:00") == 120


def test_calculate_sleep_duration_hours_midnight_rollover():
    # Bedtime 23:00 to 07:00 = 8 hours
    assert calculate_sleep_duration_hours("23:00", "07:00") == 8.0
    # Bedtime 02:00 to 10:00 = 8 hours
    assert calculate_sleep_duration_hours("02:00", "10:00") == 8.0
    # Bedtime 04:30 to 13:00 = 8.5 hours
    assert calculate_sleep_duration_hours("04:30", "13:00") == 8.5


def test_evaluate_feasibility_realistic_scenario():
    # 13:00 to 06:00 (420 min shift) with 60 days duration
    result = evaluate_feasibility(
        baseline_wake="13:00",
        target_wake="06:00",
        duration_days=60,
        baseline_bedtime="04:00",
        target_bedtime="22:00",
    )
    assert result["is_feasible"] is True
    assert result["wake_delta_minutes"] == 420
    assert result["minimum_days_required"] == 56  # 420 / 7.5 = 56 days
    assert result["target_sleep_duration_hours"] == 8.0


def test_evaluate_feasibility_unrealistic_short_duration():
    # 13:00 to 06:00 (420 min shift) with only 7 days (too fast)
    result = evaluate_feasibility(
        baseline_wake="13:00",
        target_wake="06:00",
        duration_days=7,
        baseline_bedtime="04:00",
        target_bedtime="22:00",
    )
    assert result["is_feasible"] is False
    assert result["minimum_days_required"] == 56
    assert "terlalu singkat" in result["feedback_message"]
    # Safe first phase target for 7 days: 7 * 7.5 = 52.5 min shift from 13:00 -> ~12:07
    assert result["safe_first_phase_wake_time"] is not None


def test_evaluate_feasibility_unsafe_sleep_duration():
    # Bedtime 03:00 to wake 06:00 = 3 hours sleep (Unsafe < 6h)
    result = evaluate_feasibility(
        baseline_wake="07:00",
        target_wake="06:00",
        duration_days=14,
        baseline_bedtime="23:00",
        target_bedtime="03:00",
    )
    assert result["is_feasible"] is False
    assert result["target_sleep_duration_hours"] == 3.0
    assert "di bawah batas aman" in result["feedback_message"]
