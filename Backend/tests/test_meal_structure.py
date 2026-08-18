import pytest
import jwt
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.meal_structure.constants import (
    MealSlotType,
    MealStructureState,
    ScheduleFeasibilityStatus,
    ScheduleProvenance,
    MealScheduleReasonCode,
    MealWindowType,
    MealPolicy,
)
from app.meal_structure.models import (
    MealSlotDTO,
    ConstraintIntervalDTO,
)
from app.meal_structure.structure import calculate_meal_structure_slots
from app.meal_structure.energy_distribution import (
    allocate_slot_energy_targets,
    validate_energy_shares,
)
from app.meal_structure.scheduler import schedule_daily_meals


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_baseline_day_structure():
    # Day 1 / step 0 = strictly baseline (2 main meals)
    slots = calculate_meal_structure_slots(
        baseline_meals_per_day=2,
        baseline_snacks_per_day=0,
        step_index=0,
        structure_state=MealStructureState.BASELINE,
    )
    assert len(slots) == 2
    assert all(s.slot_type == MealSlotType.MAIN_MEAL for s in slots)
    assert slots[0].schedule_source == ScheduleProvenance.BASELINE


def test_hold_and_recovery_preserves_structure():
    # State = HOLD at step 1 (2 main + 1 snack)
    slots_hold = calculate_meal_structure_slots(
        baseline_meals_per_day=2,
        baseline_snacks_per_day=0,
        step_index=1,
        structure_state=MealStructureState.HOLD,
    )
    assert len(slots_hold) == 3
    assert sum(1 for s in slots_hold if s.slot_type == MealSlotType.MAIN_MEAL) == 2
    assert sum(1 for s in slots_hold if s.slot_type == MealSlotType.SNACK) == 1

    # State = RECOVERY at step 2 (3 main)
    slots_rec = calculate_meal_structure_slots(
        baseline_meals_per_day=2,
        baseline_snacks_per_day=0,
        step_index=2,
        structure_state=MealStructureState.RECOVERY,
    )
    assert len(slots_rec) == 3
    assert all(s.slot_type == MealSlotType.MAIN_MEAL for s in slots_rec)


def test_transition_step_progression():
    # Step 0: Baseline
    s0 = calculate_meal_structure_slots(baseline_meals_per_day=2, step_index=0)
    assert len(s0) == 2

    # Step 1: 2 main + 1 snack
    s1 = calculate_meal_structure_slots(baseline_meals_per_day=2, step_index=1, structure_state=MealStructureState.TRANSITION)
    assert len(s1) == 3

    # Step 2: 3 main meals
    s2 = calculate_meal_structure_slots(baseline_meals_per_day=2, step_index=2, structure_state=MealStructureState.TRANSITION)
    assert len(s2) == 3
    assert all(s.slot_type == MealSlotType.MAIN_MEAL for s in s2)

    # Step 3: Target (3 main + 1 snack)
    s3 = calculate_meal_structure_slots(baseline_meals_per_day=2, step_index=3, structure_state=MealStructureState.TARGET)
    assert len(s3) == 4


def test_missing_timing_context_returns_needs_more_data():
    # Missing wake time
    res_no_wake = schedule_daily_meals(
        date="2026-08-19",
        wake_time=None,
        sleep_time="23:00",
        total_energy_target_kcal=2400.0,
    )
    assert res_no_wake.feasibility == ScheduleFeasibilityStatus.NEEDS_MORE_DATA
    assert res_no_wake.meal_structure_ready is False
    assert MealScheduleReasonCode.NO_WAKE_CONTEXT in res_no_wake.reason_codes

    # Missing sleep time
    res_no_sleep = schedule_daily_meals(
        date="2026-08-19",
        wake_time="07:00",
        sleep_time=None,
        total_energy_target_kcal=2400.0,
    )
    assert res_no_sleep.feasibility == ScheduleFeasibilityStatus.NEEDS_MORE_DATA
    assert res_no_sleep.meal_structure_ready is False
    assert MealScheduleReasonCode.NO_SLEEP_CONTEXT in res_no_sleep.reason_codes


def test_hard_constraint_shifts_slot_with_reason_code():
    # Hard constraint: Lecture 08:00–12:00
    constraints = [
        ConstraintIntervalDTO(
            name="Kuliah Pagi",
            start_time="08:00",
            end_time="12:00",
            availability_type="HARD_BLOCK",
        )
    ]

    schedule = schedule_daily_meals(
        date="2026-08-19",
        wake_time="07:00",
        sleep_time="23:00",
        total_energy_target_kcal=2400.0,
        baseline_meals_per_day=3,
        step_index=2,
        constraints=constraints,
    )

    assert schedule.feasibility == ScheduleFeasibilityStatus.FEASIBLE_WITH_ADJUSTMENTS
    assert schedule.meal_structure_ready is True
    assert MealScheduleReasonCode.CONSTRAINT_COLLISION in schedule.reason_codes
    assert any(s.schedule_source == ScheduleProvenance.SHIFTED_FOR_CONSTRAINT for s in schedule.slots)


def test_infeasible_when_day_fully_blocked():
    # Hard block covering the whole waking day (07:00–23:00)
    constraints = [
        ConstraintIntervalDTO(
            name="All Day Block",
            start_time="07:00",
            end_time="23:00",
            availability_type="HARD_BLOCK",
        )
    ]

    schedule = schedule_daily_meals(
        date="2026-08-19",
        wake_time="07:00",
        sleep_time="23:00",
        total_energy_target_kcal=2400.0,
        baseline_meals_per_day=3,
        constraints=constraints,
    )

    assert schedule.feasibility == ScheduleFeasibilityStatus.INFEASIBLE
    assert schedule.meal_structure_ready is False
    assert MealScheduleReasonCode.INSUFFICIENT_FREE_WINDOWS in schedule.reason_codes


def test_cross_midnight_waking_day():
    # Wake at 15:00, sleep at 05:00 (cross-midnight shift worker / student)
    schedule = schedule_daily_meals(
        date="2026-08-19",
        wake_time="15:00",
        sleep_time="05:00",
        total_energy_target_kcal=2500.0,
        baseline_meals_per_day=3,
        step_index=2,
    )

    assert schedule.feasibility == ScheduleFeasibilityStatus.FEASIBLE
    assert schedule.meal_structure_ready is True
    assert MealScheduleReasonCode.CROSS_MIDNIGHT_HANDLED in schedule.reason_codes
    assert len(schedule.slots) == 3


def test_user_fixed_meal_preservation_and_conflict():
    # 1. Valid user-fixed dinner at 19:00
    fixed_slot = MealSlotDTO(
        slot_id="slot_2",
        slot_type=MealSlotType.MAIN_MEAL,
        sequence=2,
        preferred_time="19:00",
        earliest_time="18:30",
        latest_time="19:30",
        duration_minutes=30,
        target_kcal=800.0,
        min_kcal=680.0,
        max_kcal=920.0,
        schedule_source=ScheduleProvenance.USER_FIXED,
        reason_code=MealScheduleReasonCode.NORMAL_BASELINE,
        is_user_fixed=True,
    )

    schedule_ok = schedule_daily_meals(
        date="2026-08-19",
        wake_time="08:00",
        sleep_time="23:00",
        total_energy_target_kcal=2400.0,
        baseline_meals_per_day=2,
        fixed_slots=[fixed_slot],
    )
    assert schedule_ok.feasibility == ScheduleFeasibilityStatus.FEASIBLE
    assert any(s.preferred_time == "19:00" and s.is_user_fixed for s in schedule_ok.slots)

    # 2. Fixed meal collides with hard constraint (18:30–20:00 meeting) -> Explicit Conflict
    constraints = [
        ConstraintIntervalDTO(
            name="Meeting",
            start_time="18:30",
            end_time="20:00",
            availability_type="HARD_BLOCK",
        )
    ]
    schedule_conflict = schedule_daily_meals(
        date="2026-08-19",
        wake_time="08:00",
        sleep_time="23:00",
        total_energy_target_kcal=2400.0,
        baseline_meals_per_day=2,
        fixed_slots=[fixed_slot],
        constraints=constraints,
    )
    assert schedule_conflict.feasibility == ScheduleFeasibilityStatus.INFEASIBLE
    assert MealScheduleReasonCode.FIXED_SLOT_CONFLICT in schedule_conflict.reason_codes
    assert schedule_conflict.meal_structure_ready is False


def test_energy_shares_validation_and_allocation():
    # Invalid sum of shares (!= 1.0)
    with pytest.raises(ValueError):
        validate_energy_shares([0.4, 0.4, 0.4])  # 1.2

    # Negative share rejected
    with pytest.raises(ValueError):
        validate_energy_shares([1.2, -0.2])

    raw_slots = calculate_meal_structure_slots(baseline_meals_per_day=2, step_index=0)
    allocated = allocate_slot_energy_targets(total_target_kcal=2400.0, slots=raw_slots)

    assert len(allocated) == 2
    assert allocated[0].target_kcal == 1200.0
    assert allocated[1].target_kcal == 1200.0
    assert allocated[0].min_kcal == round(1200 * 0.85, 1)
    assert allocated[0].max_kcal == round(1200 * 1.15, 1)


@pytest.mark.asyncio
async def test_api_meal_structure_preview_authenticated(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-meal-structure", "meal@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Update Core Profile & Sleep Baseline
        await client.patch(
            "/api/v1/profile",
            json={"birth_date": "2000-01-01", "sex": "MALE", "height_cm": 175.0, "current_weight_kg": 60.0},
            headers=headers,
        )
        await client.post(
            "/api/v1/user-state/baselines/sleep",
            json={"bedtime": "23:30", "wake_time": "07:30"},
            headers=headers,
        )

        # 2. Call Preview Endpoint
        payload = {
            "date": "2026-08-19",
            "total_energy_target_kcal": 2500.0,
            "baseline_meals_per_day": 2,
            "step_index": 1,
            "structure_state": "TRANSITION",
            "constraints": [
                {
                    "name": "Praktikum Lab",
                    "start_time": "13:00",
                    "end_time": "16:00",
                    "availability_type": "HARD_BLOCK",
                }
            ],
        }

        res = await client.post("/api/v1/meal-structure/preview", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["meal_structure_ready"] is True
        assert data["food_plan_ready"] is False
        assert data["structure_state"] == "TRANSITION"
        assert data["step_index"] == 1
        assert data["energy_target_kcal"] == 2500.0
        assert len(data["slots"]) == 3  # 2 main + 1 snack
        assert data["policy_version"] == MealPolicy.VERSION
        assert sum(s["target_kcal"] for s in data["slots"]) == pytest.approx(2500.0, abs=1.0)
