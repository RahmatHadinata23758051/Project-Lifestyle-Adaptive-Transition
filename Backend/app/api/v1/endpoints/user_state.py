from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.repositories.goal_repository import GoalRepository
from app.repositories.constraint_repository import ConstraintRepository
from app.repositories.financial_repository import FinancialRepository
from app.repositories.baseline_repository import BaselineRepository
from app.schemas.identity import (
    GoalCreate,
    GoalResponse,
    ConstraintCreate,
    ConstraintResponse,
    FinancialProfileUpdate,
    FinancialProfileResponse,
    SleepBaselineCreate,
    SleepBaselineResponse,
)

router = APIRouter()


# 1. User Goals
@router.get("/goals", response_model=List[GoalResponse], summary="List user goals")
def list_goals(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return GoalRepository.get_user_goals(db, user_id=current_user.id)


@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED, summary="Create a user goal")
def create_goal(
    payload: GoalCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return GoalRepository.create_goal(db, user_id=current_user.id, data=payload)


# 2. User Constraints
@router.get("/constraints", response_model=List[ConstraintResponse], summary="List user constraints")
def list_constraints(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ConstraintRepository.get_user_constraints(db, user_id=current_user.id)


@router.post("/constraints", response_model=ConstraintResponse, status_code=status.HTTP_201_CREATED, summary="Create a user constraint")
def create_constraint(
    payload: ConstraintCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ConstraintRepository.create_constraint(db, user_id=current_user.id, data=payload)


@router.delete("/constraints/{constraint_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a user constraint")
def delete_constraint(
    constraint_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = ConstraintRepository.delete_constraint(db, user_id=current_user.id, constraint_id=constraint_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Constraint not found or access denied")
    return None


# 3. Financial Profile
@router.get("/financial-profile", response_model=FinancialProfileResponse, summary="Get user financial profile")
def get_financial_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return FinancialRepository.get_or_create(db, user_id=current_user.id)


@router.put("/financial-profile", response_model=FinancialProfileResponse, summary="Update user financial profile")
def update_financial_profile(
    payload: FinancialProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return FinancialRepository.update(db, user_id=current_user.id, data=payload)


# 4. Sleep Baseline (History Preserved)
@router.get("/baselines/sleep", response_model=Optional[SleepBaselineResponse], summary="Get current sleep baseline")
def get_current_sleep_baseline(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    baseline = BaselineRepository.get_current_sleep_baseline(db, user_id=current_user.id)
    return baseline


@router.get("/baselines/sleep/history", response_model=List[SleepBaselineResponse], summary="Get full sleep baseline history")
def get_sleep_baseline_history(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BaselineRepository.get_sleep_baseline_history(db, user_id=current_user.id)


@router.post("/baselines/sleep", response_model=SleepBaselineResponse, status_code=status.HTTP_201_CREATED, summary="Create new sleep baseline preserving history")
def create_sleep_baseline(
    payload: SleepBaselineCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BaselineRepository.create_sleep_baseline(db, user_id=current_user.id, data=payload)
