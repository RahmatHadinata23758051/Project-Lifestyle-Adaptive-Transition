from typing import List, Tuple
from app.engine.time_utils import (
    time_to_minutes,
    minutes_to_time,
    validate_time_string,
)
from app.meal_structure.constants import MealPolicy, MealWindowType
from app.meal_structure.models import MealSlotDTO


def calculate_initial_slot_timings(
    wake_time: str,
    sleep_time: str,
    slots: List[MealSlotDTO],
) -> List[MealSlotDTO]:
    """
    Distributes meal slots evenly across the logical waking day.
    Supports cross-midnight waking periods (e.g., wake: 15:00, sleep: 05:00).
    """
    validate_time_string(wake_time)
    validate_time_string(sleep_time)

    if not slots:
        return []

    wake_min = time_to_minutes(wake_time)
    sleep_min = time_to_minutes(sleep_time)

    total_waking_minutes = (sleep_min - wake_min) % 1440
    if total_waking_minutes == 0:
        total_waking_minutes = 1440

    start_window_offset = MealPolicy.DEFAULT_WAKE_BUFFER_MINUTES
    end_window_offset = total_waking_minutes - MealPolicy.DEFAULT_SLEEP_BUFFER_MINUTES

    if end_window_offset <= start_window_offset:
        # Fallback if waking day is extremely short (< 2.5 hours)
        start_window_offset = 15
        end_window_offset = max(total_waking_minutes - 15, start_window_offset + 30)

    usable_span = end_window_offset - start_window_offset
    n_slots = len(slots)

    timed_slots: List[MealSlotDTO] = []

    if n_slots == 1:
        step_offsets = [start_window_offset + (usable_span // 2)]
    else:
        step_offsets = [
            int(round(start_window_offset + i * (usable_span / (n_slots - 1))))
            for i in range(n_slots)
        ]

    for slot, offset in zip(slots, step_offsets):
        preferred_min = (wake_min + offset) % 1440
        earliest_min = (preferred_min - MealPolicy.WINDOW_FLEXIBILITY_MARGIN_MINUTES) % 1440
        latest_min = (preferred_min + MealPolicy.WINDOW_FLEXIBILITY_MARGIN_MINUTES) % 1440

        timed_slots.append(
            MealSlotDTO(
                slot_id=slot.slot_id,
                slot_type=slot.slot_type,
                sequence=slot.sequence,
                preferred_time=minutes_to_time(preferred_min),
                earliest_time=minutes_to_time(earliest_min),
                latest_time=minutes_to_time(latest_min),
                duration_minutes=slot.duration_minutes,
                target_kcal=slot.target_kcal,
                min_kcal=slot.min_kcal,
                max_kcal=slot.max_kcal,
                schedule_source=slot.schedule_source,
                reason_code=slot.reason_code,
                window_type=slot.window_type,
                is_user_fixed=slot.is_user_fixed,
                location_context=slot.location_context,
                prep_context=slot.prep_context,
            )
        )

    return timed_slots
