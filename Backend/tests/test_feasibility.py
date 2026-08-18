import pytest
from app.engine.feasibility import (
    evaluate_feasibility,
)


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
    assert result["minimum_days_required"] == 56
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
    assert "lebih cepat dari policy default" in result["feedback_message"]
    assert result["safe_first_phase_wake_time"] is not None


def test_evaluate_feasibility_unsafe_sleep_duration():
    # Bedtime 03:00 to wake 06:00 = 3 hours sleep (Under policy threshold < 6h)
    result = evaluate_feasibility(
        baseline_wake="07:00",
        target_wake="06:00",
        duration_days=14,
        baseline_bedtime="23:00",
        target_bedtime="03:00",
    )
    assert result["is_feasible"] is False
    assert result["target_sleep_duration_hours"] == 3.0
    assert "di bawah batas minimum yang digunakan Chronos" in result["feedback_message"]
