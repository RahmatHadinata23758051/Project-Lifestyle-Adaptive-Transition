from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas.profile import TargetSelfGoal, CurrentSelfBaseline
from app.schemas.constraints import UserConstraint
from app.engine.feasibility import evaluate_feasibility
from app.engine.step_sizing import calculate_daily_target_times
from app.engine.state_machine import evaluate_daily_deviation, resolve_next_adaptation_action
from app.engine.collision_resolver import resolve_schedule_collisions
from app.engine.budget import rebalance_daily_budget, calculate_daily_budget_cap

router = APIRouter()


class FeasibilityRequest(BaseModel):
    baseline_wake_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    target_wake_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    duration_days: int = Field(..., ge=1, le=365)
    baseline_bedtime: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    target_bedtime: str = Field(..., pattern=r"^\d{2}:\d{2}$")


class DailyTargetRequest(BaseModel):
    baseline_wake_time: str
    target_wake_time: str
    baseline_bedtime: str
    target_bedtime: str
    current_day: int
    total_days: int
    step_size_minutes: int = 15


class EvaluationRequest(BaseModel):
    target_time: str
    actual_time: Optional[str] = None
    did_open_app: bool = True
    recent_history: Optional[List[str]] = None


class BudgetRebalanceRequest(BaseModel):
    weekly_budget: float
    total_spent_so_far: float
    remaining_days: int


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


@router.post("/daily-targets", summary="Calculate daily target times for a roadmap day")
async def get_daily_targets(payload: DailyTargetRequest):
    return calculate_daily_target_times(
        baseline_wake_str=payload.baseline_wake_time,
        target_wake_str=payload.target_wake_time,
        baseline_bed_str=payload.baseline_bedtime,
        target_bed_str=payload.target_bedtime,
        current_day=payload.current_day,
        total_days=payload.total_days,
        step_size_minutes=payload.step_size_minutes,
    )


@router.post("/evaluate-day", summary="Evaluate daily deviation and resolve adaptation")
async def evaluate_day(payload: EvaluationRequest):
    eval_result = evaluate_daily_deviation(
        target_time_str=payload.target_time,
        actual_time_str=payload.actual_time,
        did_open_app=payload.did_open_app,
    )
    
    action = resolve_next_adaptation_action(
        current_result=eval_result["result"],
        recent_history=None,
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
