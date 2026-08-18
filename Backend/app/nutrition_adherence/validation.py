from typing import Tuple, Optional, List
from app.nutrition_adherence.constants import MealCheckinStatus
from app.nutrition_adherence.models import MealCheckinDTO, UnplannedIntakeDTO


def validate_meal_checkin_input(checkin: MealCheckinDTO) -> Tuple[bool, Optional[str]]:
    """
    Validates meal checkin input integrity.
    """
    if checkin.status == MealCheckinStatus.SKIPPED and len(checkin.actual_items) > 0:
        return False, "Check-in marked as SKIPPED cannot have actual food items."

    if checkin.actual_spend_idr is not None and checkin.actual_spend_idr < 0:
        return False, "Actual spend cannot be negative."

    if checkin.status == MealCheckinStatus.ATE_DIFFERENT_FOOD and len(checkin.actual_items) == 0:
        return False, "Check-in marked as ATE_DIFFERENT_FOOD requires at least one actual food item."

    return True, None


def validate_unplanned_intake_input(intake: UnplannedIntakeDTO) -> Tuple[bool, Optional[str]]:
    """
    Validates unplanned intake input integrity.
    """
    if len(intake.items) == 0:
        return False, "Unplanned intake must contain at least one food item."

    if intake.actual_spend_idr is not None and intake.actual_spend_idr < 0:
        return False, "Actual spend cannot be negative."

    return True, None
