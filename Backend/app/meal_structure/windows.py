from typing import List
from app.engine.time_utils import (
    time_to_minutes,
    minutes_to_time,
    validate_time_string,
)
from app.meal_structure.constants import MealPolicy, ScheduleProvenance, MealWindowType
from app.meal_structure.models import MealSlotDTO


def calculate_initial_slot_timings(
    wake_time: str,
    sleep_time: str,
    slots: List[MealSlotDTO],
) -> List[MealSlotDTO]:
    """
    Distributes meal slots across the logical waking day while strictly preserving
    known baseline timings when present (P0.1).
    Supports cross-midnight waking periods without magic buffer shrinking (H1).
    """
    validate_time_string(wake_time)
    validate_time_string(sleep_time)

    if not slots:
        return []

    wake_min = time_to_minutes(wake_time)
    sleep_min = time_to_minutes(sleep_time)

    total_waking_minutes = (sleep_min - wake_min) % 1440
    if total_waking_minutes == 0:
        raise ValueError("Waktu bangun dan waktu tidur tidak boleh sama.")

    start_window_offset = MealPolicy.DEFAULT_WAKE_BUFFER_MINUTES
    end_window_offset = total_waking_minutes - MealPolicy.DEFAULT_SLEEP_BUFFER_MINUTES

    usable_span = end_window_offset - start_window_offset
    n_slots = len(slots)

    # Calculate default evenly distributed step offsets
    if n_slots == 1:
        default_offsets = [start_window_offset + (usable_span // 2)]
    else:
        default_offsets = [
            int(round(start_window_offset + i * (usable_span / (n_slots - 1))))
            for i in range(n_slots)
        ]

    timed_slots: List[MealSlotDTO] = []

    for idx, (slot, offset) in enumerate(zip(slots, default_offsets)):
        # If slot already has an observed baseline time, PRESERVE IT (P0.1)
        if slot.schedule_source == ScheduleProvenance.BASELINE_OBSERVED:
            pref_min = time_to_minutes(slot.preferred_time)
            earliest_min = (pref_min - MealPolicy.WINDOW_FLEXIBILITY_MARGIN_MINUTES) % 1440
            latest_min = (pref_min + MealPolicy.WINDOW_FLEXIBILITY_MARGIN_MINUTES) % 1440

            timed_slots.append(
                MealSlotDTO(
                    slot_id=slot.slot_id,
                    slot_type=slot.slot_type,
                    sequence=slot.sequence,
                    preferred_time=slot.preferred_time,
                    earliest_time=minutes_to_time(earliest_min),
                    latest_time=minutes_to_time(latest_min),
                    duration_minutes=slot.duration_minutes,
                    target_kcal=slot.target_kcal,
                    min_kcal=slot.min_kcal,
                    max_kcal=slot.max_kcal,
                    schedule_source=slot.schedule_source,
                    reason_code=slot.reason_code,
                    window_type=MealWindowType.FLEXIBLE,
                    is_user_fixed=slot.is_user_fixed,
                    location_context=slot.location_context,
                    prep_context=slot.prep_context,
                )
            )
        else:
            # Derived evenly distributed placement
            derived_min = (wake_min + offset) % 1440
            earliest_min = (derived_min - MealPolicy.WINDOW_FLEXIBILITY_MARGIN_MINUTES) % 1440
            latest_min = (derived_min + MealPolicy.WINDOW_FLEXIBILITY_MARGIN_MINUTES) % 1440

            timed_slots.append(
                MealSlotDTO(
                    slot_id=slot.slot_id,
                    slot_type=slot.slot_type,
                    sequence=slot.sequence,
                    preferred_time=minutes_to_time(derived_min),
                    earliest_time=minutes_to_time(earliest_min),
                    latest_time=minutes_to_time(latest_min),
                    duration_minutes=slot.duration_minutes,
                    target_kcal=slot.target_kcal,
                    min_kcal=slot.min_kcal,
                    max_kcal=slot.max_kcal,
                    schedule_source=slot.schedule_source,
                    reason_code=slot.reason_code,
                    window_type=MealWindowType.DERIVED,
                    is_user_fixed=slot.is_user_fixed,
                    location_context=slot.location_context,
                    prep_context=slot.prep_context,
                )
            )

    return timed_slots
