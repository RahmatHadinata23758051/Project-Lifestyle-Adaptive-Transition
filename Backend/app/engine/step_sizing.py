from typing import Dict, Any, Optional
from app.engine.time_utils import (
    time_to_minutes,
    minutes_to_time,
    signed_time_delta,
)


def calculate_daily_target_times(
    baseline_wake_str: str,
    target_wake_str: str,
    baseline_bed_str: str,
    target_bed_str: str,
    current_step_index: int = 0,
    step_size_minutes: int = 15,
    progress_offset_minutes: Optional[int] = None,
) -> Dict[str, str]:
    """
    Calculate the target bedtime and wake time based on transition step progress (current_step_index).
    Calendar Day != Transition Step.
    Step 0 represents baseline.
    """
    if progress_offset_minutes is not None:
        accumulated_shift = progress_offset_minutes
    else:
        accumulated_shift = max(0, current_step_index) * step_size_minutes

    base_wake_m = time_to_minutes(baseline_wake_str)
    target_wake_m = time_to_minutes(target_wake_str)

    wake_diff = target_wake_m - base_wake_m
    if wake_diff > 720:
        wake_diff -= 1440
    elif wake_diff < -720:
        wake_diff += 1440

    # Limit shift to target boundary
    if wake_diff < 0:
        actual_wake_shift = max(-accumulated_shift, wake_diff)
    else:
        actual_wake_shift = min(accumulated_shift, wake_diff)

    daily_wake_m = (base_wake_m + actual_wake_shift) % 1440

    # Bedtime progression
    base_bed_m = time_to_minutes(baseline_bed_str)
    target_bed_m = time_to_minutes(target_bed_str)

    bed_diff = target_bed_m - base_bed_m
    if bed_diff > 720:
        bed_diff -= 1440
    elif bed_diff < -720:
        bed_diff += 1440

    if bed_diff < 0:
        actual_bed_shift = max(-accumulated_shift, bed_diff)
    else:
        actual_bed_shift = min(accumulated_shift, bed_diff)

    daily_bed_m = (base_bed_m + actual_bed_shift) % 1440

    return {
        "target_wake_time": minutes_to_time(daily_wake_m),
        "target_bedtime": minutes_to_time(daily_bed_m),
    }
