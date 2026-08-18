import math
from typing import Tuple


def validate_time_string(time_str: str) -> bool:
    """Validate that string matches 'HH:MM' with 00 <= HH <= 23 and 00 <= MM <= 59."""
    if not isinstance(time_str, str):
        return False
    parts = time_str.strip().split(":")
    if len(parts) != 2:
        return False
    try:
        hours, minutes = int(parts[0]), int(parts[1])
        return 0 <= hours <= 23 and 0 <= minutes <= 59 and len(parts[0]) == 2 and len(parts[1]) == 2
    except ValueError:
        return False


def time_to_minutes(time_str: str) -> int:
    """Convert 'HH:MM' string to total minutes from 00:00 (0 to 1439)."""
    if not validate_time_string(time_str):
        raise ValueError(f"Invalid 24h time format: '{time_str}'. Expected 'HH:MM' from 00:00 to 23:59.")
    parts = time_str.strip().split(":")
    hours, minutes = int(parts[0]), int(parts[1])
    return hours * 60 + minutes


def minutes_to_time(total_minutes: int) -> str:
    """Convert total minutes (modulo 1440) to 'HH:MM' string."""
    normalized = total_minutes % 1440
    hours = normalized // 60
    minutes = normalized % 60
    return f"{hours:02d}:{minutes:02d}"


def signed_time_delta(actual_time_str: str, target_time_str: str) -> int:
    """
    Calculate directional deviation in minutes from target to actual.
    Positive value means actual was later than target.
    Negative value means actual was earlier than target.
    Correctly handles circular midnight wrap:
    - 23:30 -> 00:30 is +60m (later)
    - 00:30 -> 23:30 is -60m (earlier)
    - target 00:15 vs actual 23:55 is -20m (earlier)
    - target 23:45 vs actual 00:10 is +25m (later)
    """
    actual_m = time_to_minutes(actual_time_str)
    target_m = time_to_minutes(target_time_str)

    diff = actual_m - target_m
    if diff > 720:
        diff -= 1440
    elif diff < -720:
        diff += 1440
    return diff


def absolute_time_delta(t1_str: str, t2_str: str) -> int:
    """Calculate the shortest absolute difference in minutes between two 24h times."""
    return abs(signed_time_delta(t1_str, t2_str))


def sleep_duration_hours(bedtime_str: str, wake_time_str: str) -> float:
    """Calculate sleep opportunity in hours between bedtime and wake time."""
    m_bed = time_to_minutes(bedtime_str)
    m_wake = time_to_minutes(wake_time_str)

    if m_wake >= m_bed:
        duration_minutes = m_wake - m_bed
    else:
        duration_minutes = (1440 - m_bed) + m_wake

    return round(duration_minutes / 60.0, 2)
