from typing import Optional, List
from sqlalchemy.orm import Session
from app.nutrition_adherence.constants import MealCheckinStatus
from app.nutrition_adherence.models import (
    MealCheckinDTO,
    UnplannedIntakeDTO,
    DailyNutritionAdherenceDTO,
)
from app.nutrition_adherence.validation import (
    validate_meal_checkin_input,
    validate_unplanned_intake_input,
)
from app.nutrition_adherence.actual_intake import materialize_as_planned_items
from app.nutrition_adherence.adherence import evaluate_daily_nutrition_adherence
from app.nutrition_adherence.models import DailyNutritionPlanDTO
from app.repositories.nutrition_adherence_repository import NutritionAdherenceRepository


class NutritionAdherenceService:
    @staticmethod
    def record_meal_checkin(
        db: Session,
        owner_user_id: str,
        checkin_dto: MealCheckinDTO,
        planned_plan: Optional[DailyNutritionPlanDTO] = None,
    ) -> MealCheckinDTO:
        # If ATE_AS_PLANNED and actual items not passed, materialize from plan if provided
        if checkin_dto.status == MealCheckinStatus.ATE_AS_PLANNED and not checkin_dto.actual_items and planned_plan:
            for entry in planned_plan.meal_entries:
                if entry.slot_id == checkin_dto.slot_id:
                    checkin_dto.actual_items = materialize_as_planned_items(entry)
                    break

        is_valid, err = validate_meal_checkin_input(checkin_dto)
        if not is_valid:
            raise ValueError(err)

        return NutritionAdherenceRepository.save_meal_checkin(db, owner_user_id, checkin_dto)

    @staticmethod
    def record_unplanned_intake(
        db: Session,
        owner_user_id: str,
        intake_dto: UnplannedIntakeDTO,
    ) -> UnplannedIntakeDTO:
        is_valid, err = validate_unplanned_intake_input(intake_dto)
        if not is_valid:
            raise ValueError(err)

        return NutritionAdherenceRepository.save_unplanned_intake(db, owner_user_id, intake_dto)

    @staticmethod
    def get_daily_adherence_summary(
        db: Session,
        owner_user_id: str,
        plan: DailyNutritionPlanDTO,
    ) -> DailyNutritionAdherenceDTO:
        checkins = NutritionAdherenceRepository.get_active_meal_checkins_for_day(
            db, owner_user_id, plan.logical_day_id
        )
        unplanned = NutritionAdherenceRepository.get_unplanned_intakes_for_day(
            db, owner_user_id, plan.logical_day_id
        )
        return evaluate_daily_nutrition_adherence(plan, checkins, unplanned)
