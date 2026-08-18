import pytest
from app.schemas.roadmap import EvaluationResult, AdaptationAction
from app.engine.state_machine import (
    evaluate_daily_deviation,
    resolve_next_adaptation_action,
)


def test_evaluate_daily_deviation_success():
    # Target 08:00, Actual 08:15 (15m delta <= 20m) -> SUCCESS
    eval_res = evaluate_daily_deviation("08:00", "08:15", did_open_app=True)
    assert eval_res["result"] == EvaluationResult.SUCCESS
    assert eval_res["deviation_minutes"] == 15
    assert resolve_next_adaptation_action(eval_res["result"]) == AdaptationAction.ADVANCE_STEP


def test_evaluate_daily_deviation_within_tolerance():
    # Target 08:00, Actual 08:35 (35m delta: 21m <= delta <= 45m) -> WITHIN_TOLERANCE
    eval_res = evaluate_daily_deviation("08:00", "08:35", did_open_app=True)
    assert eval_res["result"] == EvaluationResult.WITHIN_TOLERANCE
    assert eval_res["deviation_minutes"] == 35
    assert resolve_next_adaptation_action(eval_res["result"]) == AdaptationAction.MAINTAIN_STEP


def test_evaluate_daily_deviation_single_miss():
    # Target 08:00, Actual 09:10 (70m delta: 46m <= delta <= 90m) -> MISSED
    eval_res = evaluate_daily_deviation("08:00", "09:10", did_open_app=True)
    assert eval_res["result"] == EvaluationResult.MISSED
    # Single miss without history should HOLD_TARGET
    assert resolve_next_adaptation_action(eval_res["result"], recent_history=[]) == AdaptationAction.HOLD_TARGET


def test_evaluate_daily_deviation_consecutive_miss():
    # Previous day was MISSED, today is MISSED -> REDUCE_STEP_SIZE
    action = resolve_next_adaptation_action(
        EvaluationResult.MISSED,
        recent_history=[EvaluationResult.MISSED]
    )
    assert action == AdaptationAction.REDUCE_STEP_SIZE


def test_evaluate_daily_deviation_zero_app_open():
    # User did not open app -> SIGNIFICANT_MISS & ENTER_RECOVERY
    eval_res = evaluate_daily_deviation("08:00", None, did_open_app=False)
    assert eval_res["result"] == EvaluationResult.SIGNIFICANT_MISS
    assert resolve_next_adaptation_action(eval_res["result"]) == AdaptationAction.ENTER_RECOVERY


def test_evaluate_daily_deviation_large_miss():
    # Target 08:00, Actual 11:30 (210m delta > 90m) -> SIGNIFICANT_MISS
    eval_res = evaluate_daily_deviation("08:00", "11:30", did_open_app=True)
    assert eval_res["result"] == EvaluationResult.SIGNIFICANT_MISS
    assert resolve_next_adaptation_action(eval_res["result"]) == AdaptationAction.ENTER_RECOVERY
