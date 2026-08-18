import math
from typing import Dict, Any
from app.core.config import settings
from app.engine.time_utils import (
    time_to_minutes,
    minutes_to_time,
    absolute_time_delta,
    sleep_duration_hours,
)


def evaluate_feasibility(
    baseline_wake: str,
    target_wake: str,
    duration_days: int,
    baseline_bedtime: str,
    target_bedtime: str,
) -> Dict[str, Any]:
    """
    Evaluate whether the requested transition duration is feasible according to Chronos progression policies.
    Uses default rate: 7.5 minutes per day (15 min per 2 days).
    """
    if duration_days <= 0:
        raise ValueError("Duration days must be greater than zero.")

    # 1. Calculate shift delta
    wake_delta_minutes = absolute_time_delta(baseline_wake, target_wake)

    # 2. Minimum recommended days calculation
    min_days_required = math.ceil(wake_delta_minutes / settings.DEFAULT_TRANSITION_RATE_MINUTES_PER_DAY)
    if min_days_required == 0:
        min_days_required = 1

    # 3. Check sleep duration opportunity
    target_sleep_duration = sleep_duration_hours(target_bedtime, target_wake)
    is_sleep_duration_adequate = target_sleep_duration >= settings.MINIMUM_SLEEP_OPPORTUNITY_HOURS

    # 4. Determine feasibility
    is_duration_feasible = duration_days >= min_days_required
    is_feasible = is_duration_feasible and is_sleep_duration_adequate

    # 5. Calculate safe first-phase target if unfeasible
    max_safe_minutes_in_duration = int(duration_days * settings.DEFAULT_TRANSITION_RATE_MINUTES_PER_DAY)

    m_base = time_to_minutes(baseline_wake)
    m_target = time_to_minutes(target_wake)

    # Directional shift
    diff = m_target - m_base
    if diff > 720:
        diff -= 1440
    elif diff < -720:
        diff += 1440

    if diff < 0:
        safe_shift = max(-max_safe_minutes_in_duration, diff)
    else:
        safe_shift = min(max_safe_minutes_in_duration, diff)

    safe_first_phase_wake = minutes_to_time(m_base + safe_shift)

    messages = []
    if not is_duration_feasible:
        messages.append(
            f"Durasi {duration_days} hari lebih cepat dari policy default Chronos untuk pergeseran {wake_delta_minutes} menit. "
            f"Direkomendasikan minimal {min_days_required} hari agar tubuh beradaptasi secara bertahap."
        )
    if not is_sleep_duration_adequate:
        messages.append(
            f"Target durasi istirahat ({target_sleep_duration:.1f} jam) berada di bawah batas minimum yang digunakan Chronos "
            f"({settings.MINIMUM_SLEEP_OPPORTUNITY_HOURS} jam)."
        )

    if not messages:
        messages.append("Target transisi realistis dan sesuai dengan policy Chronos.")

    return {
        "is_feasible": is_feasible,
        "wake_delta_minutes": wake_delta_minutes,
        "minimum_days_required": min_days_required,
        "requested_duration_days": duration_days,
        "target_sleep_duration_hours": round(target_sleep_duration, 1),
        "safe_first_phase_wake_time": safe_first_phase_wake,
        "feedback_message": " ".join(messages),
    }
