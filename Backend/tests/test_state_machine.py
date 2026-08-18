import pytest
from app.schemas.roadmap import EvaluationResult, AdaptationAction
from app.engine.state_machine import (
    evaluate_daily_deviation,
    resolve_next_adaptation_action,
)


def test_evaluate_daily_deviation_no_data():
    # User did not open app or no check-in -> NO_DATA, deviation_minutes is None
    eval_res = evaluate_daily_deviation("08:00", None, did_open_app=False)
    assert eval_res["result"] == EvaluationResult.NO_DATA
    assert eval_res["deviation_minutes"] is None
    assert eval_res["raw_delta_minutes"] is None

    # Adaptation for NO_DATA is MAINTAIN_STEP (not ENTER_RECOVERY)
    action = resolve_next_adaptation_action(eval_res["result"])
    assert action == AdaptationAction.MAINTAIN_STEP


def test_evaluate_daily_deviation_success():
    eval_res = evaluate_daily_deviation("08:00", "08:15", did_open_app=True)
    assert eval_res["result"] == EvaluationResult.SUCCESS
    assert eval_res["deviation_minutes"] == 15
    assert resolve_next_adaptation_action(eval_res["result"]) == AdaptationAction.ADVANCE_STEP


def test_evaluate_daily_deviation_within_tolerance():
    eval_res = evaluate_daily_deviation("08:00", "08:35", did_open_app=True)
    assert eval_res["result"] == EvaluationResult.WITHIN_TOLERANCE
    assert eval_res["deviation_minutes"] == 35
    assert resolve_next_adaptation_action(eval_res["result"]) == AdaptationAction.MAINTAIN_STEP


def test_evaluate_daily_deviation_single_miss():
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


def test_evaluate_daily_deviation_miss_success_miss_not_consecutive():
    # MISS -> SUCCESS -> MISS should be HOLD_TARGET (not reduce step)
    action = resolve_next_adaptation_action(
        EvaluationResult.MISSED,
        recent_history=[EvaluationResult.MISSED, EvaluationResult.SUCCESS]
    )
    assert action == AdaptationAction.HOLD_TARGET


def test_evaluate_daily_deviation_significant_miss():
    eval_res = evaluate_daily_deviation("08:00", "11:30", did_open_app=True)
    assert eval_res["result"] == EvaluationResult.SIGNIFICANT_MISS
    assert resolve_next_adaptation_action(eval_res["result"]) == AdaptationAction.ENTER_RECOVERY
