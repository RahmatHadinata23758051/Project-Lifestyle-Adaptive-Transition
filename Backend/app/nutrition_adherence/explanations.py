from typing import List
from app.nutrition_adherence.constants import (
    MealCompletionState,
    TimingAdherenceStatus,
    FoodChoiceAdherence,
    ReportingCompleteness,
)
from app.nutrition_adherence.models import (
    SlotAdherenceDTO,
    DailyNutritionAdherenceDTO,
    UnplannedIntakeDTO,
)


def generate_adherence_explanations(
    slot_adherences: List[SlotAdherenceDTO],
    unplanned_intakes: List[UnplannedIntakeDTO],
    reporting_completeness: ReportingCompleteness,
) -> List[str]:
    """
    Produces deterministic, factual, non-judgmental explanations of daily adherence observations.
    """
    explanations: List[str] = []
    total_slots = len(slot_adherences)
    reported_slots = sum(1 for s in slot_adherences if s.meal_completion != MealCompletionState.NOT_REPORTED)

    explanations.append(f"{reported_slots} of {total_slots} planned meal slots were reported.")

    within_window = sum(1 for s in slot_adherences if s.timing_adherence == TimingAdherenceStatus.WITHIN_WINDOW)
    if within_window > 0:
        explanations.append(f"{within_window} meal(s) occurred within their scheduled time window.")

    different_foods = sum(1 for s in slot_adherences if s.food_choice_adherence == FoodChoiceAdherence.DIFFERENT)
    if different_foods > 0:
        explanations.append(f"{different_foods} meal(s) used different food choices than planned.")

    skipped_meals = sum(1 for s in slot_adherences if s.meal_completion == MealCompletionState.SKIPPED)
    if skipped_meals > 0:
        explanations.append(f"{skipped_meals} planned meal slot(s) were explicitly skipped.")

    if unplanned_intakes:
        explanations.append(f"{len(unplanned_intakes)} additional unplanned intake event(s) were logged.")

    return explanations
