from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.schemas.nutrition_adaptation import (
    NutritionAdaptationEvaluationRequest,
    NutritionAdaptationEvaluationResponse,
)
from app.nutrition_adaptation.models import (
    NutritionAdaptationEvaluationInputDTO,
    NutritionEvidenceDayDTO,
    WeightObservationDTO,
)
from app.nutrition_adaptation.evidence import classify_day_evidence_quality
from app.services.nutrition_adaptation_service import NutritionAdaptationService

router = APIRouter()


@router.post("/preview", response_model=NutritionAdaptationEvaluationResponse)
def preview_nutrition_adaptation(
    request: NutritionAdaptationEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    owner_user_id = current_user.id

    evidence_days = []
    for d in request.evidence_days:
        quality = d.evidence_quality or classify_day_evidence_quality(
            d.plan_status, d.reporting_completeness, d.nutrition_completeness
        )
        evidence_days.append(
            NutritionEvidenceDayDTO(
                logical_day_id=d.logical_day_id,
                date=d.date,
                plan_status=d.plan_status,
                reporting_completeness=d.reporting_completeness,
                nutrition_completeness=d.nutrition_completeness,
                planned_energy_kcal=d.planned_energy_kcal,
                actual_energy_kcal=d.actual_energy_kcal,
                meal_completion_counts=d.meal_completion_counts,
                deviation_reasons=d.deviation_reasons,
                evidence_quality=quality,
            )
        )

    weight_measurements = [
        WeightObservationDTO(
            measured_at=w.measured_at,
            weight_kg=w.weight_kg,
            source=w.source,
            context=w.context,
        )
        for w in request.weight_measurements
    ]

    input_dto = NutritionAdaptationEvaluationInputDTO(
        user_id=owner_user_id,
        nutrition_goal_type=request.nutrition_goal_type,
        target_energy_kcal=request.target_energy_kcal,
        meal_structure_state=request.meal_structure_state,
        step_index=request.step_index,
        assessment_eligibility_status=request.assessment_eligibility_status,
        evidence_days=evidence_days,
        weight_measurements=weight_measurements,
        last_adaptation_at=request.last_adaptation_at,
        evaluation_reference_time=request.evaluation_reference_time,
    )

    try:
        result = NutritionAdaptationService.evaluate_adaptation(
            db, owner_user_id, input_dto, persist=request.persist
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/evaluations")
def list_adaptation_evaluations(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return NutritionAdaptationService.get_evaluation_history(db, current_user.id, limit)
