from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.schemas.roadmap import EvaluationResult, AdaptationAction
from app.engine.feasibility import evaluate_feasibility
from app.engine.step_sizing import calculate_daily_target_times
from app.engine.state_machine import evaluate_daily_deviation, resolve_next_adaptation_action
from app.engine.collision_resolver import resolve_schedule_collisions
from app.engine.budget import rebalance_daily_budget, calculate_daily_budget_cap
from app.engine.time_utils import validate_time_string

router = APIRouter()


class FeasibilityRequest(BaseModel):
    baseline_wake_time: str
    target_wake_time: str
    duration_days: int = Field(..., ge=1, le=365)
    baseline_bedtime: str
    target_bedtime: str

    @field_validator("baseline_wake_time", "target_wake_time", "baseline_bedtime", "target_bedtime")
    @classmethod
    def check_valid_time(cls, v: str) -> str:
        if not validate_time_string(v):
            raise ValueError(f"Invalid time format '{v}'. Expected 24h format HH:MM (00:00 to 23:59).")
        return v


class DailyTargetRequest(BaseModel):
    baseline_wake_time: str
    target_wake_time: str
    baseline_bedtime: str
    target_bedtime: str
    current_step_index: int = 0
    step_size_minutes: int = 15
    progress_offset_minutes: Optional[int] = None

    @field_validator("baseline_wake_time", "target_wake_time", "baseline_bedtime", "target_bedtime")
    @classmethod
    def check_valid_time(cls, v: str) -> str:
        if not validate_time_string(v):
            raise ValueError(f"Invalid time format '{v}'. Expected 24h format HH:MM (00:00 to 23:59).")
        return v


class EvaluationRequest(BaseModel):
    target_time: str
    actual_time: Optional[str] = None
    did_open_app: bool = True
    recent_history: Optional[List[str]] = None

    @field_validator("target_time", "actual_time")
    @classmethod
    def check_valid_time(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not validate_time_string(v):
            raise ValueError(f"Invalid time format '{v}'. Expected 24h format HH:MM (00:00 to 23:59).")
        return v


class BudgetRebalanceRequest(BaseModel):
    weekly_budget: float = Field(..., ge=0.0)
    total_spent_so_far: float = Field(..., ge=0.0)
    remaining_days: int = Field(..., ge=0)


@router.post("/feasibility", summary="Evaluate transition feasibility")
async def check_feasibility(payload: FeasibilityRequest):
    try:
        result = evaluate_feasibility(
            baseline_wake=payload.baseline_wake_time,
            target_wake=payload.target_wake_time,
            duration_days=payload.duration_days,
            baseline_bedtime=payload.baseline_bedtime,
            target_bedtime=payload.target_bedtime,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/daily-targets", summary="Calculate daily target times from transition step progress")
async def get_daily_targets(payload: DailyTargetRequest):
    return calculate_daily_target_times(
        baseline_wake_str=payload.baseline_wake_time,
        target_wake_str=payload.target_wake_time,
        baseline_bed_str=payload.baseline_bedtime,
        target_bed_str=payload.target_bedtime,
        current_step_index=payload.current_step_index,
        step_size_minutes=payload.step_size_minutes,
        progress_offset_minutes=payload.progress_offset_minutes,
    )


@router.post("/evaluate-day", summary="Evaluate daily deviation and resolve adaptation with history")
async def evaluate_day(payload: EvaluationRequest):
    eval_result = evaluate_daily_deviation(
        target_time_str=payload.target_time,
        actual_time_str=payload.actual_time,
        did_open_app=payload.did_open_app,
    )

    # Parse recent history into EvaluationResult enum list
    parsed_history: List[EvaluationResult] = []
    if payload.recent_history:
        for item in payload.recent_history:
            try:
                parsed_history.append(EvaluationResult(item))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid evaluation status in recent_history: '{item}'.")

    action = resolve_next_adaptation_action(
        current_result=eval_result["result"],
        recent_history=parsed_history,
    )

    return {
        "evaluation": eval_result,
        "recommended_action": action,
    }


@router.post("/budget-rebalance", summary="Rebalance daily budget based on actual spending")
async def rebalance_budget(payload: BudgetRebalanceRequest):
    try:
        return rebalance_daily_budget(
            weekly_budget=payload.weekly_budget,
            total_spent_so_far=payload.total_spent_so_far,
            remaining_days=payload.remaining_days,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
