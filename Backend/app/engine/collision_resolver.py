from typing import List, Dict, Any, Tuple
from app.engine.feasibility import time_to_minutes, minutes_to_time
from app.schemas.constraints import UserConstraint


def intervals_overlap(start1: int, end1: int, start2: int, end2: int) -> bool:
    """Check if two time intervals (in minutes) overlap on the same day."""
    return max(start1, start2) < min(end1, end2)


def has_schedule_collision(
    scheduled_time_str: str,
    duration_minutes: int,
    constraint: UserConstraint,
) -> bool:
    """Check if a planned item collides with a user constraint."""
    item_start = time_to_minutes(scheduled_time_str)
    item_end = item_start + duration_minutes
    
    constraint_start = time_to_minutes(constraint.start_time)
    constraint_end = time_to_minutes(constraint.end_time)

    return intervals_overlap(item_start, item_end, constraint_start, constraint_end)


def resolve_schedule_collisions(
    scheduled_time_str: str,
    duration_minutes: int,
    constraints: List[UserConstraint],
    buffer_minutes: int = 15,
) -> Tuple[str, bool]:
    """
    Resolve potential schedule collisions by shifting planned time to the nearest safe available window.
    Returns (resolved_time_str, did_shift).
    """
    current_time_m = time_to_minutes(scheduled_time_str)
    did_shift = False

    # Sort constraints by start time
    sorted_constraints = sorted(
        constraints,
        key=lambda c: time_to_minutes(c.start_time)
    )

    for constraint in sorted_constraints:
        c_start = time_to_minutes(constraint.start_time)
        c_end = time_to_minutes(constraint.end_time)
        
        item_start = current_time_m
        item_end = current_time_m + duration_minutes

        if intervals_overlap(item_start, item_end, c_start, c_end):
            # Shift after the constraint ends + buffer
            current_time_m = (c_end + buffer_minutes) % 1440
            did_shift = True

    return minutes_to_time(current_time_m), did_shift
