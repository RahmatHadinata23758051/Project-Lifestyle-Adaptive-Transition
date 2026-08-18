from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.repositories.assessment_repository import AssessmentRepository
from app.repositories.baseline_repository import BaselineRepository
from app.repositories.constraint_repository import ConstraintRepository
from app.meal_structure.models import (
    ConstraintIntervalDTO,
    MealSlotDTO,
    BaselineMealTiming,
)
from app.meal_structure.scheduler import schedule_daily_meals
from app.schemas.meal_structure import (
    MealStructurePreviewInput,
    DailyMealScheduleResponse,
    MealSlotResponse,
)

router = APIRouter()


@router.post(
    "/preview",
    response_model=DailyMealScheduleResponse,
    summary="Preview deterministic meal structure and scheduling across the logical waking day",
)
def preview_meal_structure(
    payload: MealStructurePreviewInput,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    known_data = AssessmentRepository.get_user_known_data(db, user_id=current_user.id)
    sleep_baseline = BaselineRepository.get_current_sleep_baseline(db, user_id=current_user.id)

    # 1. Resolve Wake & Sleep Context
    wake_time = (
        payload.wake_time
        or (sleep_baseline.wake_time if sleep_baseline else None)
        or known_data.get("sleep.wake_time")
    )
    sleep_time = (
        payload.sleep_time
        or (sleep_baseline.bedtime if sleep_baseline else None)
        or known_data.get("sleep.target_sleep_time")
        or known_data.get("sleep.bedtime")
    )

    # 2. Resolve Energy Target
    energy_target = payload.total_energy_target_kcal or 2400.0

    # 3. Resolve Meals Per Day
    baseline_meals = payload.baseline_meals_per_day or known_data.get("nutrition.meals_per_day") or 2
    baseline_snacks = payload.baseline_snacks_per_day or 0

    # 4. Resolve Constraints
    user_db_constraints = ConstraintRepository.get_user_constraints(db, user_id=current_user.id)
    merged_constraints: List[ConstraintIntervalDTO] = [
        ConstraintIntervalDTO(
            name=c.name,
            start_time=c.start_time,
            end_time=c.end_time,
            availability_type="HARD_BLOCK" if c.is_hard_constraint else "SOFT_BLOCK",
        )
        for c in user_db_constraints
    ]
    for c_in in payload.constraints:
        merged_constraints.append(
            ConstraintIntervalDTO(
                name=c_in.name,
                start_time=c_in.start_time,
                end_time=c_in.end_time,
                availability_type=c_in.availability_type,
                buffer_before_minutes=c_in.buffer_before_minutes,
                buffer_after_minutes=c_in.buffer_after_minutes,
            )
        )

    # 5. Resolve Baseline Timings
    baseline_timings_dto = [
        BaselineMealTiming(
            slot_type=bt.slot_type,
            sequence=bt.sequence,
            preferred_time=bt.preferred_time,
            earliest_time=bt.earliest_time,
            latest_time=bt.latest_time,
            duration_minutes=bt.duration_minutes,
        )
        for bt in payload.baseline_timings
    ]

    schedule_dto = schedule_daily_meals(
        date=payload.date,
        wake_time=wake_time,
        sleep_time=sleep_time,
        total_energy_target_kcal=energy_target,
        baseline_meals_per_day=baseline_meals,
        baseline_snacks_per_day=baseline_snacks,
        step_index=payload.step_index,
        structure_state=payload.structure_state,
        baseline_timings=baseline_timings_dto if baseline_timings_dto else None,
        constraints=merged_constraints,
        custom_energy_shares=payload.custom_energy_shares,
        minimum_slot_gap_minutes=payload.minimum_slot_gap_minutes,
    )

    return DailyMealScheduleResponse(
        date=schedule_dto.date,
        logical_day_id=schedule_dto.logical_day_id,
        structure_state=schedule_dto.structure_state,
        step_index=schedule_dto.step_index,
        energy_target_kcal=schedule_dto.energy_target_kcal,
        feasibility=schedule_dto.feasibility,
        slots=[MealSlotResponse.model_validate(s) for s in schedule_dto.slots],
        policy_version=schedule_dto.policy_version,
        assessment_snapshot_id=schedule_dto.assessment_snapshot_id,
        reason_codes=schedule_dto.reason_codes,
        explanation=schedule_dto.explanation,
        meal_structure_ready=schedule_dto.meal_structure_ready,
        food_plan_ready=schedule_dto.food_plan_ready,
    )
