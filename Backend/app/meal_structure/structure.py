from typing import List, Optional
from app.meal_structure.constants import (
    MealSlotType,
    MealStructureState,
    MealWindowType,
    ScheduleProvenance,
    MealScheduleReasonCode,
    MealPolicy,
)
from app.meal_structure.models import (
    MealSlotDTO,
    MealStructureDefinition,
    BaselineMealTiming,
)


def derive_transition_path(
    baseline: MealStructureDefinition,
    target: MealStructureDefinition,
) -> List[MealStructureDefinition]:
    """
    Pure deterministic transition path generator (MEAL_STRUCTURE_TRANSITION_V01).
    Derives step progression from baseline to target without forcing a single universal path.
    Guarantees monotonic progression towards target without unnecessary oscillation.
    """
    if baseline.main_meals <= 0 or target.main_meals <= 0:
        raise ValueError("Jumlah makan utama (main_meals) harus >= 1.")
    if baseline.snacks < 0 or target.snacks < 0:
        raise ValueError("Jumlah snack tidak boleh negatif.")

    path: List[MealStructureDefinition] = [MealStructureDefinition(main_meals=baseline.main_meals, snacks=baseline.snacks)]

    curr_main = baseline.main_meals
    curr_snacks = baseline.snacks

    # Step-by-step adjustment until target is reached
    while (curr_main != target.main_meals) or (curr_snacks != target.snacks):
        if curr_main < target.main_meals:
            curr_main += 1
        elif curr_main > target.main_meals:
            curr_main -= 1
        elif curr_snacks < target.snacks:
            curr_snacks += 1
        elif curr_snacks > target.snacks:
            curr_snacks -= 1

        path.append(MealStructureDefinition(main_meals=curr_main, snacks=curr_snacks))

    return path


def generate_slots_for_structure(
    slot_types: List[MealSlotType],
    schedule_source: ScheduleProvenance = ScheduleProvenance.DERIVED,
    reason_code: MealScheduleReasonCode = MealScheduleReasonCode.NORMAL_BASELINE,
    baseline_timings: Optional[List[BaselineMealTiming]] = None,
) -> List[MealSlotDTO]:
    slots: List[MealSlotDTO] = []
    timing_map = {bt.sequence: bt for bt in (baseline_timings or [])}

    for idx, st in enumerate(slot_types, 1):
        duration = (
            MealPolicy.DEFAULT_MEAL_DURATION_MINUTES
            if st == MealSlotType.MAIN_MEAL
            else MealPolicy.DEFAULT_SNACK_DURATION_MINUTES
        )

        bt = timing_map.get(idx)
        if bt and bt.preferred_time:
            preferred_time = bt.preferred_time
            earliest_time = bt.earliest_time or preferred_time
            latest_time = bt.latest_time or preferred_time
            dur = bt.duration_minutes or duration
            source = ScheduleProvenance.BASELINE_OBSERVED
            reason = MealScheduleReasonCode.BASELINE_TIME_PRESERVED
            win_type = MealWindowType.FLEXIBLE if (bt.earliest_time and bt.latest_time) else MealWindowType.DERIVED
        else:
            preferred_time = "12:00"  # Placeholder to be resolved by window scheduler
            earliest_time = "11:15"
            latest_time = "12:45"
            dur = duration
            source = schedule_source
            reason = reason_code
            win_type = MealWindowType.DERIVED

        slots.append(
            MealSlotDTO(
                slot_id=f"slot_{idx}",
                slot_type=st,
                sequence=idx,
                preferred_time=preferred_time,
                earliest_time=earliest_time,
                latest_time=latest_time,
                duration_minutes=dur,
                target_kcal=0.0,
                min_kcal=0.0,
                max_kcal=0.0,
                schedule_source=source,
                reason_code=reason,
                window_type=win_type,
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
    baseline_timings: Optional[List[BaselineMealTiming]] = None,
) -> List[MealSlotDTO]:
    """
    Pure deterministic structure calculator.
    - Preserves known baseline timings when available.
    - Dynamically derives transition path from baseline to target structure.
    - In HOLD / RECOVERY, preserves the structure at step_index without advancing.
    """
    if baseline_meals_per_day <= 0:
        raise ValueError("Baseline meals per day harus bernilai positif >= 1.")

    baseline_def = MealStructureDefinition(main_meals=baseline_meals_per_day, snacks=baseline_snacks_per_day)
    target_def = MealStructureDefinition(main_meals=target_meals_per_day, snacks=target_snacks_per_day)

    path = derive_transition_path(baseline=baseline_def, target=target_def)

    # In BASELINE state or step_index == 0, strictly use baseline structure
    if structure_state == MealStructureState.BASELINE or step_index == 0:
        active_def = baseline_def
        source = (
            ScheduleProvenance.BASELINE_OBSERVED
            if baseline_timings
            else ScheduleProvenance.BASELINE_DERIVED
        )
        reason = (
            MealScheduleReasonCode.BASELINE_TIME_PRESERVED
            if baseline_timings
            else MealScheduleReasonCode.BASELINE_TIME_DERIVED
        )
        slot_types = [MealSlotType.MAIN_MEAL] * active_def.main_meals + [MealSlotType.SNACK] * active_def.snacks
        return generate_slots_for_structure(
            slot_types,
            schedule_source=source,
            reason_code=reason,
            baseline_timings=baseline_timings,
        )

    # In TARGET state, use target structure
    if structure_state == MealStructureState.TARGET:
        active_def = target_def
    else:
        # Clamped indexing over transition path
        clamped_step = min(step_index, len(path) - 1)
        active_def = path[clamped_step]

    slot_types = [MealSlotType.MAIN_MEAL] * active_def.main_meals + [MealSlotType.SNACK] * active_def.snacks
    return generate_slots_for_structure(
        slot_types,
        schedule_source=ScheduleProvenance.DERIVED,
        reason_code=MealScheduleReasonCode.NORMAL_BASELINE,
        baseline_timings=None,
    )
