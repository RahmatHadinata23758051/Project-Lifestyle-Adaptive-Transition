from typing import List, Optional
from app.meal_structure.constants import (
    MealSlotType,
    MealStructureState,
    MealWindowType,
    ScheduleProvenance,
    MealScheduleReasonCode,
    MealPolicy,
)
from app.meal_structure.models import MealSlotDTO


def generate_slots_for_structure(
    slot_types: List[MealSlotType],
    schedule_source: ScheduleProvenance = ScheduleProvenance.DERIVED,
    reason_code: MealScheduleReasonCode = MealScheduleReasonCode.NORMAL_BASELINE,
) -> List[MealSlotDTO]:
    slots: List[MealSlotDTO] = []
    for idx, st in enumerate(slot_types, 1):
        duration = (
            MealPolicy.DEFAULT_MEAL_DURATION_MINUTES
            if st == MealSlotType.MAIN_MEAL
            else MealPolicy.DEFAULT_SNACK_DURATION_MINUTES
        )
        slots.append(
            MealSlotDTO(
                slot_id=f"slot_{idx}",
                slot_type=st,
                sequence=idx,
                preferred_time="12:00",  # Placeholder to be resolved by window scheduler
                earliest_time="11:30",
                latest_time="12:30",
                duration_minutes=duration,
                target_kcal=0.0,
                min_kcal=0.0,
                max_kcal=0.0,
                schedule_source=schedule_source,
                reason_code=reason_code,
                window_type=MealWindowType.FLEXIBLE,
                is_user_fixed=False,
            )
        )
    return slots


def calculate_meal_structure_slots(
    baseline_meals_per_day: int = 2,
    baseline_snacks_per_day: int = 0,
    step_index: int = 0,
    structure_state: MealStructureState = MealStructureState.BASELINE,
    target_meals_per_day: int = 3,
    target_snacks_per_day: int = 1,
) -> List[MealSlotDTO]:
    """
    Pure deterministic structure calculator.
    Separates transition step index from calendar days.
    - Day 1 / step 0 = BASELINE structure.
    - Progressive transition steps:
      Step 0: Baseline (e.g. 2 main meals)
      Step 1: Baseline + 1 snack (e.g. 2 main + 1 snack)
      Step 2: 3 main meals
      Step 3: 3 main meals + 1 snack (Target)
    - If structure_state == HOLD or RECOVERY: preserves the structure at step_index.
    """
    if baseline_meals_per_day <= 0:
        raise ValueError("Baseline meals per day harus bernilai positif >= 1.")

    # In BASELINE state or step_index == 0, strictly use baseline habit
    if structure_state == MealStructureState.BASELINE or step_index == 0:
        slots_types = [MealSlotType.MAIN_MEAL] * baseline_meals_per_day
        if baseline_snacks_per_day > 0:
            slots_types.extend([MealSlotType.SNACK] * baseline_snacks_per_day)
        return generate_slots_for_structure(
            slots_types,
            schedule_source=ScheduleProvenance.BASELINE,
            reason_code=MealScheduleReasonCode.NORMAL_BASELINE,
        )

    # In TARGET state, return full target structure
    if structure_state == MealStructureState.TARGET:
        slots_types = [MealSlotType.MAIN_MEAL] * target_meals_per_day + [MealSlotType.SNACK] * target_snacks_per_day
        return generate_slots_for_structure(
            slots_types,
            schedule_source=ScheduleProvenance.DERIVED,
            reason_code=MealScheduleReasonCode.NORMAL_BASELINE,
        )

    # Step Progression mapping (TRANSITION, HOLD, RECOVERY)
    # Step 0: Baseline
    # Step 1: 2 main + 1 snack
    # Step 2: 3 main
    # Step 3+: 3 main + target snacks
    if step_index == 1:
        slots_types = [MealSlotType.MAIN_MEAL] * max(baseline_meals_per_day, 2) + [MealSlotType.SNACK]
    elif step_index == 2:
        slots_types = [MealSlotType.MAIN_MEAL] * 3
    else:
        slots_types = [MealSlotType.MAIN_MEAL] * target_meals_per_day + [MealSlotType.SNACK] * target_snacks_per_day

    return generate_slots_for_structure(
        slots_types,
        schedule_source=ScheduleProvenance.DERIVED,
        reason_code=MealScheduleReasonCode.NORMAL_BASELINE,
    )
