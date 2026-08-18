import pytest
from app.schemas.constraints import UserConstraint, ConstraintCategory, DayOfWeek
from app.engine.collision_resolver import (
    has_schedule_collision,
    resolve_schedule_collisions,
)


def test_has_schedule_collision():
    class_constraint = UserConstraint(
        title="Morning Lecture",
        category=ConstraintCategory.UNIVERSITY,
        day_of_week=DayOfWeek.MONDAY,
        start_time="08:00",
        end_time="12:00",
    )

    # 09:00 (30m duration) is inside 08:00-12:00 -> Collision
    assert has_schedule_collision("09:00", 30, class_constraint) is True
    # 07:00 (30m duration) ends at 07:30 before 08:00 -> No collision
    assert has_schedule_collision("07:00", 30, class_constraint) is False
    # 12:30 (30m duration) is after 12:00 -> No collision
    assert has_schedule_collision("12:30", 30, class_constraint) is False


def test_resolve_schedule_collisions_single():
    class_constraint = UserConstraint(
        title="Morning Lecture",
        category=ConstraintCategory.UNIVERSITY,
        day_of_week=DayOfWeek.MONDAY,
        start_time="08:00",
        end_time="12:00",
    )

    # Planned lunch at 11:30 (duration 30m) collides with lecture (08:00-12:00)
    # Resolver should shift to 12:00 + 15m buffer = 12:15
    resolved_time, did_shift = resolve_schedule_collisions(
        scheduled_time_str="11:30",
        duration_minutes=30,
        constraints=[class_constraint],
        buffer_minutes=15,
    )
    assert did_shift is True
    assert resolved_time == "12:15"


def test_resolve_schedule_collisions_multiple_iterative_recheck():
    # Constraint A: 12:00 - 13:00 (Meeting)
    # Constraint B: 13:10 - 14:00 (Commute)
    # Task at 12:30 (duration 30m).
    # First shift -> 13:00 + 15m buffer = 13:15.
    # 13:15 collides with Constraint B (13:10-14:00)!
    # Second shift -> 14:00 + 15m buffer = 14:15.
    c1 = UserConstraint(
        title="Meeting",
        category=ConstraintCategory.WORK,
        day_of_week=DayOfWeek.MONDAY,
        start_time="12:00",
        end_time="13:00",
    )
    c2 = UserConstraint(
        title="Commute",
        category=ConstraintCategory.COMMUTE,
        day_of_week=DayOfWeek.MONDAY,
        start_time="13:10",
        end_time="14:00",
    )

    resolved_time, did_shift = resolve_schedule_collisions(
        scheduled_time_str="12:30",
        duration_minutes=30,
        constraints=[c1, c2],
        buffer_minutes=15,
    )
    assert did_shift is True
    assert resolved_time == "14:15"


def test_cross_midnight_constraint_collision():
    night_shift = UserConstraint(
        title="Night Shift",
        category=ConstraintCategory.WORK,
        day_of_week=DayOfWeek.MONDAY,
        start_time="22:00",
        end_time="02:00",
    )

    # 23:00 is inside 22:00-02:00 -> Collision
    assert has_schedule_collision("23:00", 30, night_shift) is True
    # 01:00 is inside 22:00-02:00 -> Collision
    assert has_schedule_collision("01:00", 30, night_shift) is True
    # 02:30 is outside -> No collision
    assert has_schedule_collision("02:30", 30, night_shift) is False
