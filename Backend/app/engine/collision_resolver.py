from typing import List, Tuple, Optional
from app.engine.time_utils import time_to_minutes, minutes_to_time
from app.schemas.constraints import UserConstraint


def intervals_overlap(start1: int, end1: int, start2: int, end2: int) -> bool:
    """Check if two time intervals (in minutes from 00:00) overlap."""
    return max(start1, start2) < min(end1, end2)


def get_constraint_intervals(constraint: UserConstraint) -> List[Tuple[int, int]]:
    """
    Get (start_m, end_m) intervals for a constraint.
    Splits cross-midnight constraints (e.g. 22:00 to 02:00) into [22:00-1440] and [0-02:00].
    """
    c_start = time_to_minutes(constraint.start_time)
    c_end = time_to_minutes(constraint.end_time)

    if c_start <= c_end:
        return [(c_start, c_end)]
    else:
        # Cross midnight
        return [(c_start, 1440), (0, c_end)]


def has_schedule_collision(
    scheduled_time_str: str,
    duration_minutes: int,
    constraint: UserConstraint,
) -> bool:
    """Check if a planned item collides with a user constraint (including cross-midnight constraints)."""
    item_start = time_to_minutes(scheduled_time_str)
    item_end = item_start + duration_minutes

    intervals = get_constraint_intervals(constraint)
    for c_start, c_end in intervals:
        # Check standard overlap
        if intervals_overlap(item_start, min(item_end, 1440), c_start, c_end):
            return True
        # If item wraps past midnight (item_end > 1440)
        if item_end > 1440 and intervals_overlap(0, item_end - 1440, c_start, c_end):
            return True
    return False


def resolve_schedule_collisions(
    scheduled_time_str: str,
    duration_minutes: int,
    constraints: List[UserConstraint],
    buffer_minutes: int = 15,
    max_iterations: int = 20,
    earliest_allowed_time: Optional[str] = None,
    latest_allowed_time: Optional[str] = None,
    is_movable: bool = True,
) -> Tuple[str, bool]:
    """
    Resolve potential schedule collisions using iterative re-checking across ALL constraints.
    Iterates until no collisions exist or max_iterations reached.
    """
    if not is_movable or not constraints:
        return scheduled_time_str, False

    current_time_m = time_to_minutes(scheduled_time_str)
    did_shift = False
    earliest_m = time_to_minutes(earliest_allowed_time) if earliest_allowed_time else None
    latest_m = time_to_minutes(latest_allowed_time) if latest_allowed_time else None

    # Collect all flattened constraint intervals
    all_intervals: List[Tuple[int, int]] = []
    for c in constraints:
        all_intervals.extend(get_constraint_intervals(c))
    all_intervals.sort(key=lambda x: x[0])

    for _ in range(max_iterations):
        collision_found = False
        item_start = current_time_m
        item_end = item_start + duration_minutes

        for c_start, c_end in all_intervals:
            if intervals_overlap(item_start, min(item_end, 1440), c_start, c_end) or (
                item_end > 1440 and intervals_overlap(0, item_end - 1440, c_start, c_end)
            ):
                # Shift candidate after constraint + buffer
                current_time_m = (c_end + buffer_minutes) % 1440
                did_shift = True
                collision_found = True
                break  # Re-check candidate against all constraints from the beginning

        if not collision_found:
            # Check window boundaries if defined
            if earliest_m is not None and current_time_m < earliest_m:
                current_time_m = earliest_m
                continue
            if latest_m is not None and current_time_m > latest_m:
                # Out of allowed window, return original
                return scheduled_time_str, False

            return minutes_to_time(current_time_m), did_shift

    # If max iterations exhausted without clean slot
    return minutes_to_time(current_time_m), did_shift
