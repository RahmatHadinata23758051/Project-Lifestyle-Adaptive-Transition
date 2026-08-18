from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.repositories.assessment_repository import AssessmentRepository
from app.assessment.router import AssessmentRouter
from app.assessment.completeness import AssessmentCompletenessEvaluator
from app.schemas.assessment import (
    AssessmentGoalsUpdate,
    AssessmentStatusResponse,
    AssessmentQuestionsResponse,
    AssessmentAnswerPayload,
    AssessmentSnapshotResponse,
)

router = APIRouter()


@router.get("/status", response_model=AssessmentStatusResponse, summary="Get assessment completeness & plan readiness status")
def get_assessment_status(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    known_data = AssessmentRepository.get_user_known_data(db, user_id=current_user.id)
    active_goals = AssessmentRepository.get_active_goal_domains(db, user_id=current_user.id)
    eval_result = AssessmentCompletenessEvaluator.evaluate(active_goals, known_data)
    return eval_result


@router.post("/goals", status_code=status.HTTP_200_OK, summary="Set active goals and priorities for assessment routing")
def set_assessment_goals(
    payload: AssessmentGoalsUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    AssessmentRepository.set_user_goals(db, user_id=current_user.id, goals=payload.goals)
    known_data = AssessmentRepository.get_user_known_data(db, user_id=current_user.id)
    active_goals = [g.domain.value if hasattr(g.domain, "value") else str(g.domain) for g in payload.goals]
    return AssessmentCompletenessEvaluator.evaluate(active_goals, known_data)


@router.get("/questions", response_model=AssessmentQuestionsResponse, summary="Get filtered relevant questions for missing fields only")
def get_assessment_questions(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    known_data = AssessmentRepository.get_user_known_data(db, user_id=current_user.id)
    active_goals = AssessmentRepository.get_active_goal_domains(db, user_id=current_user.id)
    router_result = AssessmentRouter.determine_missing_fields(active_goals, known_data)
    return router_result


@router.post("/answers", response_model=AssessmentStatusResponse, summary="Submit answers and receive updated completeness")
def submit_assessment_answers(
    payload: AssessmentAnswerPayload,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    eval_result = AssessmentRepository.ingest_answers(db, user_id=current_user.id, answers=payload.answers)
    return eval_result


@router.post("/snapshot", response_model=AssessmentSnapshotResponse, status_code=status.HTTP_201_CREATED, summary="Create immutable assessment snapshot when plan-ready")
def create_assessment_snapshot(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        snapshot = AssessmentRepository.create_assessment_snapshot(db, user_id=current_user.id)
        return snapshot
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
