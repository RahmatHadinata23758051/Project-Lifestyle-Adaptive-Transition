from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.schemas.profile import CurrentSelfBaseline, TargetSelfGoal
from app.schemas.constraints import UserConstraint
from app.services.roadmap_service import create_user_transition_roadmap, get_active_daily_plan
from app.services.checkin_service import process_item_checkin, evaluate_daily_plan_completion

router = APIRouter()


class OnboardingRequest(BaseModel):
    email: str
    baseline: CurrentSelfBaseline
    goal: TargetSelfGoal
    constraints: List[UserConstraint] = Field(default_factory=list)
    start_date: Optional[str] = None


class CheckinRequest(BaseModel):
    item_id: str
    actual_time: Optional[str] = None
    actual_cost: Optional[float] = None
    is_late: bool = False


class EvaluateRequest(BaseModel):
    daily_plan_id: str
    did_open_app: bool = True


@router.post("/onboard", summary="Onboard user and generate complete transition roadmap")
def onboard_user(payload: OnboardingRequest, db: Session = Depends(get_db)):
    try:
        return create_user_transition_roadmap(
            db=db,
            email=payload.email,
            baseline_data=payload.baseline,
            goal_data=payload.goal,
            constraints_data=payload.constraints,
            start_date_str=payload.start_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{roadmap_id}/today", summary="Get today's active daily plan with tasks and budget")
def get_today_plan(roadmap_id: str, day: Optional[int] = None, db: Session = Depends(get_db)):
    plan = get_active_daily_plan(db=db, roadmap_id=roadmap_id, day_number=day)
    if not plan:
        raise HTTPException(status_code=404, detail="Daily plan not found for this roadmap.")
    return plan


@router.post("/checkin", summary="1-Tap check-in item with optional actual time and spending")
def checkin_item(payload: CheckinRequest, db: Session = Depends(get_db)):
    try:
        return process_item_checkin(
            db=db,
            item_id=payload.item_id,
            actual_time_str=payload.actual_time,
            actual_cost=payload.actual_cost,
            is_late=payload.is_late,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/evaluate", summary="Evaluate end of day and update roadmap progress")
def evaluate_day(payload: EvaluateRequest, db: Session = Depends(get_db)):
    try:
        return evaluate_daily_plan_completion(
            db=db,
            daily_plan_id=payload.daily_plan_id,
            did_open_app=payload.did_open_app,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
