from typing import Tuple, Dict, Any
from app.engine.feasibility import time_to_minutes, minutes_to_time


def normalize_midnight_delta(actual_time_str: str, target_time_str: str) -> int:
    """
    Calculate the directional deviation in minutes from target to actual.
    Positive value means actual was later than target (e.g. woke up late).
    Negative value means actual was earlier than target (e.g. woke up early).
    Properly handles rollover around midnight (e.g. target 00:30, actual 23:45 -> delta = -45m).
    """
    actual_m = time_to_minutes(actual_time_str)
    target_m = time_to_minutes(target_time_str)

    diff = actual_m - target_m
    
    # Handle midnight rollover wrap
    if diff > 720:
        diff -= 1440
    elif diff < -720:
        diff += 1440
        
    return diff


def calculate_daily_target_times(
    baseline_wake_str: str,
    target_wake_str: str,
    baseline_bed_str: str,
    target_bed_str: str,
    current_day: int,
    total_days: int,
    step_size_minutes: int = 15,
) -> Dict[str, str]:
    """
    Calculate the target bedtime and wake time for a specific day in the transition.
    Shifts time by step_size_minutes every 2 days until target is reached.
    """
    if current_day <= 1:
        return {
            "target_wake_time": baseline_wake_str,
            "target_bedtime": baseline_bed_str,
        }

    # Total accumulated shift by current day (1 step every 2 days)
    steps_count = (current_day - 1) // 2
    accumulated_shift = steps_count * step_size_minutes

    base_wake_m = time_to_minutes(baseline_wake_str)
    target_wake_m = time_to_minutes(target_wake_str)
    
    # Calculate directional difference for wake
    wake_diff = target_wake_m - base_wake_m
    if wake_diff > 720:
        wake_diff -= 1440
    elif wake_diff < -720:
        wake_diff += 1440

    # Limit shift to not overshoot target
    if wake_diff < 0:
        actual_shift = max(-accumulated_shift, wake_diff)
    else:
        actual_shift = min(accumulated_shift, wake_diff)

    daily_wake_m = (base_wake_m + actual_shift) % 1440
    
    # Bedtime progression mirrors wake progression
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
