from typing import Optional
from app.nutrition_adherence.constants import (
    MealCheckinStatus,
    MealCompletionState,
    FoodChoiceAdherence,
    EnergyAdherenceStatus,
)


def derive_meal_completion_state(status: MealCheckinStatus) -> MealCompletionState:
    if status == MealCheckinStatus.ATE_AS_PLANNED:
        return MealCompletionState.FULL
    elif status in (MealCheckinStatus.ATE_PARTIALLY, MealCheckinStatus.ATE_DIFFERENT_FOOD):
        return MealCompletionState.PARTIAL
    elif status == MealCheckinStatus.SKIPPED:
        return MealCompletionState.SKIPPED
    return MealCompletionState.NOT_REPORTED


def derive_food_choice_adherence(status: MealCheckinStatus) -> FoodChoiceAdherence:
    if status == MealCheckinStatus.ATE_AS_PLANNED:
        return FoodChoiceAdherence.AS_PLANNED
    elif status == MealCheckinStatus.ATE_PARTIALLY:
        return FoodChoiceAdherence.PARTIAL_MATCH
    elif status == MealCheckinStatus.ATE_DIFFERENT_FOOD:
        return FoodChoiceAdherence.DIFFERENT
    elif status == MealCheckinStatus.SKIPPED:
        return FoodChoiceAdherence.SKIPPED
    return FoodChoiceAdherence.NOT_REPORTED


def evaluate_energy_adherence(
    actual_energy_kcal: Optional[float],
    planned_energy_kcal: float,
    min_kcal: Optional[float] = None,
    max_kcal: Optional[float] = None,
) -> EnergyAdherenceStatus:
    """
    Compares actual energy to slot target range.
    """
    if actual_energy_kcal is None:
        return EnergyAdherenceStatus.UNKNOWN

    lower_bound = min_kcal if min_kcal is not None else (planned_energy_kcal * 0.85)
    upper_bound = max_kcal if max_kcal is not None else (planned_energy_kcal * 1.15)

    if lower_bound <= actual_energy_kcal <= upper_bound:
        return EnergyAdherenceStatus.WITHIN_PLANNED_RANGE
    elif actual_energy_kcal < lower_bound:
        return EnergyAdherenceStatus.BELOW_PLANNED_RANGE
    else:
        return EnergyAdherenceStatus.ABOVE_PLANNED_RANGE
