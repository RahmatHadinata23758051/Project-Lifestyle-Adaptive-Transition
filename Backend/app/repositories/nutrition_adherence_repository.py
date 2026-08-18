import uuid
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.nutrition_adherence import (
    NutritionMealCheckin,
    NutritionActualItem,
    NutritionUnplannedIntake,
)
from app.nutrition_adherence.models import (
    MealCheckinDTO,
    ActualFoodItemDTO,
    UnplannedIntakeDTO,
)
from app.nutrition_adherence.constants import (
    MealCheckinStatus,
    ActualFoodSourceType,
    ActualIntakeCertainty,
    DeviationReason,
)


class NutritionAdherenceRepository:
    @staticmethod
    def save_meal_checkin(
        db: Session,
        owner_user_id: str,
        checkin_dto: MealCheckinDTO,
    ) -> MealCheckinDTO:
        # Check for existing active check-in on this slot
        existing_active = (
            db.query(NutritionMealCheckin)
            .filter(
                NutritionMealCheckin.owner_user_id == owner_user_id,
                NutritionMealCheckin.plan_id == checkin_dto.plan_id,
                NutritionMealCheckin.slot_id == checkin_dto.slot_id,
                NutritionMealCheckin.is_active == True,
            )
            .first()
        )

        revision = 1
        if existing_active:
            existing_active.is_active = False
            revision = existing_active.revision + 1

        checkin_id = checkin_dto.checkin_id or str(uuid.uuid4())
        try:
            checked_in_dt = datetime.fromisoformat(checkin_dto.checked_in_at)
        except Exception:
            checked_in_dt = datetime.now(timezone.utc)

        db_checkin = NutritionMealCheckin(
            id=checkin_id,
            owner_user_id=owner_user_id,
            plan_id=checkin_dto.plan_id,
            logical_day_id=checkin_dto.logical_day_id,
            slot_id=checkin_dto.slot_id,
            status=checkin_dto.status.value if hasattr(checkin_dto.status, "value") else str(checkin_dto.status),
            meal_occurred_at=checkin_dto.meal_occurred_at,
            checked_in_at=checked_in_dt,
            actual_spend_idr=checkin_dto.actual_spend_idr,
            deviation_reason=(
                checkin_dto.deviation_reason.value
                if hasattr(checkin_dto.deviation_reason, "value")
                else (checkin_dto.deviation_reason if checkin_dto.deviation_reason else None)
            ),
            notes=checkin_dto.notes,
            certainty=(
                checkin_dto.certainty.value
                if hasattr(checkin_dto.certainty, "value")
                else str(checkin_dto.certainty)
            ),
            revision=revision,
            is_active=True,
        )
        db.add(db_checkin)

        # Add items
        for item in checkin_dto.actual_items:
            db_item = NutritionActualItem(
                id=str(uuid.uuid4()),
                checkin_id=checkin_id,
                food_item_id=item.food_item_id,
                display_name=item.display_name,
                serving_id=item.serving_id,
                serving_name=item.serving_name,
                quantity=item.quantity,
                grams=item.grams,
                energy_kcal=item.energy_kcal,
                protein_g=item.protein_g,
                fat_g=item.fat_g,
                carbohydrate_g=item.carbohydrate_g,
                source_type=(
                    item.source_type.value
                    if hasattr(item.source_type, "value")
                    else str(item.source_type)
                ),
                certainty=(
                    item.certainty.value
                    if hasattr(item.certainty, "value")
                    else str(item.certainty)
                ),
            )
            db.add(db_item)

        db.commit()
        db.refresh(db_checkin)

        return NutritionAdherenceRepository._to_checkin_dto(db_checkin)

    @staticmethod
    def get_active_meal_checkins_for_day(
        db: Session,
        owner_user_id: str,
        logical_day_id: str,
    ) -> List[MealCheckinDTO]:
        records = (
            db.query(NutritionMealCheckin)
            .filter(
                NutritionMealCheckin.owner_user_id == owner_user_id,
                NutritionMealCheckin.logical_day_id == logical_day_id,
                NutritionMealCheckin.is_active == True,
            )
            .all()
        )
        return [NutritionAdherenceRepository._to_checkin_dto(r) for r in records]

    @staticmethod
    def save_unplanned_intake(
        db: Session,
        owner_user_id: str,
        intake_dto: UnplannedIntakeDTO,
    ) -> UnplannedIntakeDTO:
        intake_id = intake_dto.intake_id or str(uuid.uuid4())
        try:
            rec_dt = datetime.fromisoformat(intake_dto.recorded_at)
        except Exception:
            rec_dt = datetime.now(timezone.utc)

        db_intake = NutritionUnplannedIntake(
            id=intake_id,
            owner_user_id=owner_user_id,
            logical_day_id=intake_dto.logical_day_id,
            occurred_at=intake_dto.occurred_at,
            recorded_at=rec_dt,
            actual_spend_idr=intake_dto.actual_spend_idr,
            reason=intake_dto.reason,
            notes=intake_dto.notes,
        )
        db.add(db_intake)

        for item in intake_dto.items:
            db_item = NutritionActualItem(
                id=str(uuid.uuid4()),
                unplanned_intake_id=intake_id,
                food_item_id=item.food_item_id,
                display_name=item.display_name,
                serving_id=item.serving_id,
                serving_name=item.serving_name,
                quantity=item.quantity,
                grams=item.grams,
                energy_kcal=item.energy_kcal,
                protein_g=item.protein_g,
                fat_g=item.fat_g,
                carbohydrate_g=item.carbohydrate_g,
                source_type=(
                    item.source_type.value
                    if hasattr(item.source_type, "value")
                    else str(item.source_type)
                ),
                certainty=(
                    item.certainty.value
                    if hasattr(item.certainty, "value")
                    else str(item.certainty)
                ),
            )
            db.add(db_item)

        db.commit()
        db.refresh(db_intake)

        return NutritionAdherenceRepository._to_unplanned_dto(db_intake)

    @staticmethod
    def get_unplanned_intakes_for_day(
        db: Session,
        owner_user_id: str,
        logical_day_id: str,
    ) -> List[UnplannedIntakeDTO]:
        records = (
            db.query(NutritionUnplannedIntake)
            .filter(
                NutritionUnplannedIntake.owner_user_id == owner_user_id,
                NutritionUnplannedIntake.logical_day_id == logical_day_id,
            )
            .all()
        )
        return [NutritionAdherenceRepository._to_unplanned_dto(r) for r in records]

    @staticmethod
    def _to_checkin_dto(record: NutritionMealCheckin) -> MealCheckinDTO:
        items = [
            ActualFoodItemDTO(
                food_item_id=it.food_item_id,
                display_name=it.display_name,
                serving_id=it.serving_id,
                serving_name=it.serving_name,
                grams=it.grams,
                quantity=it.quantity,
                energy_kcal=it.energy_kcal,
                protein_g=it.protein_g,
                fat_g=it.fat_g,
                carbohydrate_g=it.carbohydrate_g,
                source_type=ActualFoodSourceType(it.source_type),
                certainty=ActualIntakeCertainty(it.certainty),
            )
            for it in record.actual_items
        ]
        return MealCheckinDTO(
            checkin_id=record.id,
            plan_id=record.plan_id,
            logical_day_id=record.logical_day_id,
            slot_id=record.slot_id,
            status=MealCheckinStatus(record.status),
            meal_occurred_at=record.meal_occurred_at,
            checked_in_at=record.checked_in_at.isoformat() if record.checked_in_at else datetime.now(timezone.utc).isoformat(),
            actual_items=items,
            actual_spend_idr=record.actual_spend_idr,
            deviation_reason=DeviationReason(record.deviation_reason) if record.deviation_reason else None,
            notes=record.notes,
            certainty=ActualIntakeCertainty(record.certainty),
            revision=record.revision,
        )

    @staticmethod
    def _to_unplanned_dto(record: NutritionUnplannedIntake) -> UnplannedIntakeDTO:
        items = [
            ActualFoodItemDTO(
                food_item_id=it.food_item_id,
                display_name=it.display_name,
                serving_id=it.serving_id,
                serving_name=it.serving_name,
                grams=it.grams,
                quantity=it.quantity,
                energy_kcal=it.energy_kcal,
                protein_g=it.protein_g,
                fat_g=it.fat_g,
                carbohydrate_g=it.carbohydrate_g,
                source_type=ActualFoodSourceType(it.source_type),
                certainty=ActualIntakeCertainty(it.certainty),
            )
            for it in record.items
        ]
        return UnplannedIntakeDTO(
            intake_id=record.id,
            logical_day_id=record.logical_day_id,
            occurred_at=record.occurred_at,
            recorded_at=record.recorded_at.isoformat() if record.recorded_at else datetime.now(timezone.utc).isoformat(),
            items=items,
            actual_spend_idr=record.actual_spend_idr,
            reason=record.reason,
            notes=record.notes,
        )
