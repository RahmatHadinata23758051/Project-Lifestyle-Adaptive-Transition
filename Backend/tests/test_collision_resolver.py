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


def test_resolve_schedule_collisions():
    class_constraint = UserConstraint(
        title="Morning Lecture",
        category=ConstraintCategory.UNIVERSITY,
        day_of_week=DayOfWeek.MONDAY,
        start_time="08:00",
        end_time="12:00",
    )

    # Planned lunch at 11:30 (duration 30m) collides with lecture (08:00-12:00)
    # Resolver should shift to constraint end (12:00) + 15m buffer = 12:15
    resolved_time, did_shift = resolve_schedule_collisions(
        scheduled_time_str="11:30",
        duration_minutes=30,
        constraints=[class_constraint],
        buffer_minutes=15,
    )
    assert did_shift is True
    assert resolved_time == "12:15"
