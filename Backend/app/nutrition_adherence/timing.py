from typing import Optional
from app.nutrition_adherence.constants import TimingAdherenceStatus
from app.engine.time_utils import time_to_minutes, validate_time_string


def evaluate_timing_adherence(
    meal_occurred_at: Optional[str],
    earliest_time: Optional[str],
    latest_time: Optional[str],
) -> TimingAdherenceStatus:
    """
    Evaluates whether actual meal timing occurred within the authoritative slot window.
    """
    if not meal_occurred_at or not earliest_time or not latest_time:
        return TimingAdherenceStatus.UNKNOWN

    if (
        not validate_time_string(meal_occurred_at)
        or not validate_time_string(earliest_time)
        or not validate_time_string(latest_time)
    ):
        return TimingAdherenceStatus.UNKNOWN

    t_occ = time_to_minutes(meal_occurred_at)
    t_early = time_to_minutes(earliest_time)
    t_late = time_to_minutes(latest_time)

    # Standard within-day interval
    if t_early <= t_late:
        if t_early <= t_occ <= t_late:
            return TimingAdherenceStatus.WITHIN_WINDOW
        return TimingAdherenceStatus.OUTSIDE_WINDOW
    else:
        # Cross-midnight interval (e.g. 23:30 to 01:30)
        if t_occ >= t_early or t_occ <= t_late:
            return TimingAdherenceStatus.WITHIN_WINDOW
        return TimingAdherenceStatus.OUTSIDE_WINDOW
