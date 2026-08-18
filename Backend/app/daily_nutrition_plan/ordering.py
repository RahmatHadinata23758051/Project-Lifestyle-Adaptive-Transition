from typing import List, Optional
from app.engine.time_utils import time_to_minutes, validate_time_string
from app.daily_nutrition_plan.models import DailyMealEntryDTO


def get_waking_day_offset(time_str: str, wake_time_str: Optional[str]) -> int:
    """
    Computes offset in minutes from wake time (0 to 1439).
    Supports cross-midnight waking days.
    """
    if not validate_time_string(time_str):
        return 0
    t_min = time_to_minutes(time_str)
    if not wake_time_str or not validate_time_string(wake_time_str):
        return t_min
    w_min = time_to_minutes(wake_time_str)
    return (t_min - w_min) % 1440


def order_meal_entries_by_waking_day(
    entries: List[DailyMealEntryDTO],
    wake_time_str: Optional[str] = None,
) -> List[DailyMealEntryDTO]:
    """
    Sorts daily meal entries in chronological order within the user's logical waking day.
    Cross-midnight slots are placed in their proper experiential order after waking,
    not simple 00:00-23:59 clock order.
    """
    return sorted(
        entries,
        key=lambda e: (get_waking_day_offset(e.scheduled_time, wake_time_str), e.slot_id),
    )
