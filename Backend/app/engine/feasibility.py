import math
from typing import Dict, Any, Tuple
from app.core.config import settings


def time_to_minutes(time_str: str) -> int:
    """Convert 'HH:MM' string to total minutes from 00:00."""
    parts = time_str.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: '{time_str}'. Expected 'HH:MM'.")
    hours, minutes = int(parts[0]), int(parts[1])
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        raise ValueError(f"Time out of 24h bounds: '{time_str}'.")
    return hours * 60 + minutes


def minutes_to_time(total_minutes: int) -> str:
    """Convert total minutes (modulo 1440) to 'HH:MM' string."""
    normalized = total_minutes % 1440
    hours = normalized // 60
    minutes = normalized % 60
    return f"{hours:02d}:{minutes:02d}"


def calculate_time_delta_minutes(start_time: str, end_time: str) -> int:
    """
    Calculate the absolute shortest delta in minutes between two times in a 24-hour cycle.
    """
    m1 = time_to_minutes(start_time)
    m2 = time_to_minutes(end_time)
    diff = abs(m2 - m1)
    return min(diff, 1440 - diff)


def calculate_sleep_duration_hours(bedtime: str, wake_time: str) -> float:
    """Calculate hours of sleep between bedtime and wake time handling midnight rollover."""
    m_bed = time_to_minutes(bedtime)
    m_wake = time_to_minutes(wake_time)
    
    if m_wake >= m_bed:
        duration_minutes = m_wake - m_bed
    else:
        duration_minutes = (1440 - m_bed) + m_wake
        
    return duration_minutes / 60.0


def evaluate_feasibility(
    baseline_wake: str,
    target_wake: str,
    duration_days: int,
    baseline_bedtime: str,
    target_bedtime: str,
) -> Dict[str, Any]:
    """
    Evaluate whether the requested transition duration is physically feasible and safe.
    Uses maximum safe step sizing rate: 7.5 minutes per day (15 min per 2 days).
    """
    if duration_days <= 0:
        raise ValueError("Duration days must be greater than zero.")

    # 1. Calculate shift delta
    wake_delta_minutes = calculate_time_delta_minutes(baseline_wake, target_wake)
    
    # 2. Minimum safe days calculation
    min_days_required = math.ceil(wake_delta_minutes / settings.SAFE_DAILY_STEP_MINUTES)
    if min_days_required == 0:
        min_days_required = 1

    # 3. Check sleep duration safety
    target_sleep_duration = calculate_sleep_duration_hours(target_bedtime, target_wake)
    is_sleep_duration_safe = target_sleep_duration >= settings.MINIMUM_SAFE_SLEEP_HOURS

    # 4. Determine feasibility
    is_duration_feasible = duration_days >= min_days_required
    is_feasible = is_duration_feasible and is_sleep_duration_safe

    # 5. Calculate safe first-phase target if unfeasible
    max_safe_minutes_in_duration = int(duration_days * settings.SAFE_DAILY_STEP_MINUTES)
    
    # Directional shift for first phase
    m_base = time_to_minutes(baseline_wake)
    m_target = time_to_minutes(target_wake)
    
    # Shift towards target
    if m_target < m_base:
        safe_first_phase_wake_m = m_base - max_safe_minutes_in_duration
    else:
        safe_first_phase_wake_m = m_base + max_safe_minutes_in_duration
        
    safe_first_phase_wake = minutes_to_time(safe_first_phase_wake_m)

    messages = []
    if not is_duration_feasible:
        messages.append(
            f"Durasi {duration_days} hari terlalu singkat untuk pergeseran {wake_delta_minutes} menit. "
            f"Dibutuhkan minimal {min_days_required} hari agar tubuh beradaptasi secara alami."
        )
    if not is_sleep_duration_safe:
        messages.append(
            f"Target durasi tidur ({target_sleep_duration:.1f} jam) berada di bawah batas aman medis "
            f"({settings.MINIMUM_SAFE_SLEEP_HOURS} jam)."
        )

    if not messages:
        messages.append("Target transisi realistis dan aman untuk dijalani.")

    return {
        "is_feasible": is_feasible,
        "wake_delta_minutes": wake_delta_minutes,
        "minimum_days_required": min_days_required,
        "requested_duration_days": duration_days,
        "target_sleep_duration_hours": round(target_sleep_duration, 1),
        "safe_first_phase_wake_time": safe_first_phase_wake,
        "feedback_message": " ".join(messages),
    }
