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
    MealStructureDefinition,
    BaselineMealTiming,
    ConstraintIntervalDTO,
)
from app.meal_structure.structure import (
    derive_transition_path,
    calculate_meal_structure_slots,
)
from app.meal_structure.energy_distribution import (
    allocate_slot_energy_targets,
    validate_energy_shares,
)
from app.meal_structure.scheduler import (
    schedule_daily_meals,
    is_interval_overlapping_circular,
    is_time_inside_window_circular,
)


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_baseline_timing_preservation_known_vs_unknown():
    # Case A: Known baseline times (13:00 and 20:00) preserved on Step 0 / BASELINE (P0.1)
    baseline_timings = [
        BaselineMealTiming(slot_type=MealSlotType.MAIN_MEAL, sequence=1, preferred_time="13:00"),
        BaselineMealTiming(slot_type=MealSlotType.MAIN_MEAL, sequence=2, preferred_time="20:00"),
    ]

    schedule_known = schedule_daily_meals(
        date="2026-08-19",
        wake_time="10:00",
        sleep_time="02:00",
        total_energy_target_kcal=2400.0,
        baseline_meals_per_day=2,
        step_index=0,
        structure_state=MealStructureState.BASELINE,
        baseline_timings=baseline_timings,
    )

    assert schedule_known.feasibility == ScheduleFeasibilityStatus.FEASIBLE
    assert len(schedule_known.slots) == 2
    assert schedule_known.slots[0].preferred_time == "13:00"
    assert schedule_known.slots[1].preferred_time == "20:00"
    assert schedule_known.slots[0].schedule_source == ScheduleProvenance.BASELINE_OBSERVED
    assert MealScheduleReasonCode.BASELINE_TIME_PRESERVED in schedule_known.reason_codes

    # Case B: Unknown baseline times derived explicitly
    schedule_unknown = schedule_daily_meals(
        date="2026-08-19",
        wake_time="10:00",
        sleep_time="02:00",
        total_energy_target_kcal=2400.0,
        baseline_meals_per_day=2,
        step_index=0,
        structure_state=MealStructureState.BASELINE,
        baseline_timings=None,
    )

    assert schedule_unknown.feasibility == ScheduleFeasibilityStatus.FEASIBLE
    assert schedule_unknown.slots[0].schedule_source == ScheduleProvenance.BASELINE_DERIVED


def test_dynamic_transition_path_arbitrary_baselines():
    # Case A: 1 main -> 3 main (monotonic progression)
    path_a = derive_transition_path(
        baseline=MealStructureDefinition(main_meals=1, snacks=0),
        target=MealStructureDefinition(main_meals=3, snacks=0),
    )
    assert path_a == [
        MealStructureDefinition(main_meals=1, snacks=0),
        MealStructureDefinition(main_meals=2, snacks=0),
        MealStructureDefinition(main_meals=3, snacks=0),
    ]

    # Case B: 4 main -> 3 main (no spurious snacks)
    path_b = derive_transition_path(
        baseline=MealStructureDefinition(main_meals=4, snacks=0),
        target=MealStructureDefinition(main_meals=3, snacks=0),
    )
    assert path_b == [
        MealStructureDefinition(main_meals=4, snacks=0),
        MealStructureDefinition(main_meals=3, snacks=0),
    ]

    # Case C: 3 main -> 3 main (no frequency change)
    path_c = derive_transition_path(
        baseline=MealStructureDefinition(main_meals=3, snacks=0),
        target=MealStructureDefinition(main_meals=3, snacks=0),
    )
    assert path_c == [MealStructureDefinition(main_meals=3, snacks=0)]

    # Case D: 2 main + 1 snack -> 3 main + 1 snack
    path_d = derive_transition_path(
        baseline=MealStructureDefinition(main_meals=2, snacks=1),
        target=MealStructureDefinition(main_meals=3, snacks=1),
    )
    assert path_d == [
        MealStructureDefinition(main_meals=2, snacks=1),
        MealStructureDefinition(main_meals=3, snacks=1),
    ]


def test_hold_and_recovery_preserves_step_structure():
    # State = HOLD at step 1
    slots_hold = calculate_meal_structure_slots(
        baseline_meals_per_day=2,
        baseline_snacks_per_day=0,
        step_index=1,
        structure_state=MealStructureState.HOLD,
        target_meals_per_day=3,
        target_snacks_per_day=1,
    )
    assert len(slots_hold) == 3

    # State = RECOVERY at step 0
    slots_rec = calculate_meal_structure_slots(
        baseline_meals_per_day=2,
        baseline_snacks_per_day=0,
        step_index=0,
        structure_state=MealStructureState.RECOVERY,
    )
    assert len(slots_rec) == 2


def test_missing_timing_context_returns_needs_more_data():
    res_no_wake = schedule_daily_meals(
        date="2026-08-19",
        wake_time=None,
        sleep_time="23:00",
        total_energy_target_kcal=2400.0,
    )
    assert res_no_wake.feasibility == ScheduleFeasibilityStatus.NEEDS_MORE_DATA
    assert res_no_wake.meal_structure_ready is False
    assert MealScheduleReasonCode.NO_WAKE_CONTEXT in res_no_wake.reason_codes

    res_no_sleep = schedule_daily_meals(
        date="2026-08-19",
        wake_time="07:00",
        sleep_time=None,
        total_energy_target_kcal=2400.0,
    )
    assert res_no_sleep.feasibility == ScheduleFeasibilityStatus.NEEDS_MORE_DATA
    assert res_no_sleep.meal_structure_ready is False
    assert MealScheduleReasonCode.NO_SLEEP_CONTEXT in res_no_sleep.reason_codes


def test_equal_wake_and_sleep_returns_invalid_waking_period():
    # Hardening H2: wake == sleep is not 24h awake
    res = schedule_daily_meals(
        date="2026-08-19",
        wake_time="08:00",
        sleep_time="08:00",
        total_energy_target_kcal=2400.0,
    )
    assert res.feasibility == ScheduleFeasibilityStatus.NEEDS_MORE_DATA
    assert MealScheduleReasonCode.INVALID_WAKING_PERIOD in res.reason_codes
    assert res.meal_structure_ready is False


def test_short_waking_day_returns_infeasible_without_shrinking_buffers():
    # Hardening H1: wake 10:00, sleep 12:00 (span = 120m < 45+90+30 = 165m)
    res = schedule_daily_meals(
        date="2026-08-19",
        wake_time="10:00",
        sleep_time="12:00",
        total_energy_target_kcal=2400.0,
        baseline_meals_per_day=2,
    )
    assert res.feasibility == ScheduleFeasibilityStatus.INFEASIBLE
    assert MealScheduleReasonCode.INSUFFICIENT_FREE_WINDOWS in res.reason_codes
    assert res.meal_structure_ready is False


def test_slot_to_slot_spacing_enforcement():
    # P0.3: Spacing between slot end and next slot start must be >= minimum_slot_gap (e.g. 120m)
    baseline_timings = [
        BaselineMealTiming(slot_type=MealSlotType.MAIN_MEAL, sequence=1, preferred_time="12:00", duration_minutes=30),
        BaselineMealTiming(slot_type=MealSlotType.MAIN_MEAL, sequence=2, preferred_time="13:00", duration_minutes=30),  # Gap = 30m (< 120m)
    ]

    schedule = schedule_daily_meals(
        date="2026-08-19",
        wake_time="07:00",
        sleep_time="23:00",
        total_energy_target_kcal=2400.0,
        baseline_meals_per_day=2,
        step_index=0,
        baseline_timings=baseline_timings,
        minimum_slot_gap_minutes=120,
    )

    assert schedule.feasibility == ScheduleFeasibilityStatus.INFEASIBLE
    assert MealScheduleReasonCode.MEAL_SPACING_CONFLICT in schedule.reason_codes
    assert schedule.meal_structure_ready is False


def test_original_window_bounds_preserved():
    # P0.4: Baseline slot with preferred 12:00 (window 11:15–12:45).
    # Hard constraint covers 11:00–13:00 completely.
    baseline_timings = [
        BaselineMealTiming(slot_type=MealSlotType.MAIN_MEAL, sequence=1, preferred_time="12:00"),
    ]
    constraints_full = [
        ConstraintIntervalDTO(
            name="Block Entire Window",
            start_time="11:00",
            end_time="13:00",
            availability_type="HARD_BLOCK",
        )
    ]

    schedule_blocked = schedule_daily_meals(
        date="2026-08-19",
        wake_time="10:00",
        sleep_time="02:00",
        total_energy_target_kcal=2400.0,
        baseline_meals_per_day=1,
        baseline_timings=baseline_timings,
        constraints=constraints_full,
    )
    # Cannot escape window to 13:05 -> returns INFEASIBLE with OUTSIDE_ORIGINAL_WINDOW
    assert schedule_blocked.feasibility == ScheduleFeasibilityStatus.INFEASIBLE
    assert (
        MealScheduleReasonCode.OUTSIDE_ORIGINAL_WINDOW in schedule_blocked.reason_codes
        or MealScheduleReasonCode.INSUFFICIENT_FREE_WINDOWS in schedule_blocked.reason_codes
    )


def test_cross_midnight_constraint_and_waking_day():
    # Wake 15:00, Sleep 05:00. Hard constraint 23:00–02:00.
    constraints = [
        ConstraintIntervalDTO(
            name="Night Shift Work",
            start_time="23:00",
            end_time="02:00",
            availability_type="HARD_BLOCK",
        )
    ]

    schedule = schedule_daily_meals(
        date="2026-08-19",
        wake_time="15:00",
        sleep_time="05:00",
        total_energy_target_kcal=2500.0,
        baseline_meals_per_day=3,
        step_index=2,
        constraints=constraints,
    )

    assert schedule.meal_structure_ready is True
    assert MealScheduleReasonCode.CROSS_MIDNIGHT_HANDLED in schedule.reason_codes
    assert len(schedule.slots) == 3


def test_full_interval_collision_regression():
    # Meal 19:00–19:30, constraint 19:15–20:00
    assert is_interval_overlapping_circular(
        start_a=19 * 60,
        end_a=19 * 60 + 30,
        start_b=19 * 60 + 15,
        end_b=20 * 60,
    ) is True


def test_user_fixed_slot_conflict_never_silently_moved():
    fixed_slot = MealSlotDTO(
        slot_id="slot_2",
        slot_type=MealSlotType.MAIN_MEAL,
        sequence=2,
        preferred_time="19:00",
        earliest_time="19:00",
        latest_time="19:00",
        duration_minutes=30,
        target_kcal=800.0,
        min_kcal=680.0,
        max_kcal=920.0,
        schedule_source=ScheduleProvenance.USER_FIXED,
        reason_code=MealScheduleReasonCode.NORMAL_BASELINE,
        window_type=MealWindowType.FIXED,
        is_user_fixed=True,
    )
    constraints = [
        ConstraintIntervalDTO(
            name="Family Meeting",
            start_time="18:30",
            end_time="20:00",
            availability_type="HARD_BLOCK",
        )
    ]

    schedule = schedule_daily_meals(
        date="2026-08-19",
        wake_time="08:00",
        sleep_time="23:00",
        total_energy_target_kcal=2400.0,
        baseline_meals_per_day=2,
        fixed_slots=[fixed_slot],
        constraints=constraints,
    )

    assert schedule.feasibility == ScheduleFeasibilityStatus.INFEASIBLE
    assert MealScheduleReasonCode.FIXED_SLOT_CONFLICT in schedule.reason_codes
    assert schedule.meal_structure_ready is False


def test_energy_shares_validation_and_allocation():
    with pytest.raises(ValueError):
        validate_energy_shares([0.4, 0.4, 0.4])

    raw_slots = calculate_meal_structure_slots(baseline_meals_per_day=2, step_index=0)
    allocated = allocate_slot_energy_targets(total_target_kcal=2400.0, slots=raw_slots)

    assert len(allocated) == 2
    assert allocated[0].target_kcal == 1200.0
    assert allocated[1].target_kcal == 1200.0


@pytest.mark.asyncio
async def test_api_meal_structure_preview_authenticated(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-meal-structure-h", "mealh@chronos.local")
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

        # 2. Call Preview Endpoint with Baseline Timings
        payload = {
            "date": "2026-08-19",
            "total_energy_target_kcal": 2500.0,
            "baseline_meals_per_day": 2,
            "step_index": 0,
            "structure_state": "BASELINE",
            "baseline_timings": [
                {"slot_type": "MAIN_MEAL", "sequence": 1, "preferred_time": "12:30"},
                {"slot_type": "MAIN_MEAL", "sequence": 2, "preferred_time": "19:30"},
            ],
            "constraints": [],
        }

        res = await client.post("/api/v1/meal-structure/preview", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["meal_structure_ready"] is True
        assert data["food_plan_ready"] is False
        assert data["structure_state"] == "BASELINE"
        assert data["step_index"] == 0
        assert data["energy_target_kcal"] == 2500.0
        assert len(data["slots"]) == 2
        assert data["slots"][0]["preferred_time"] == "12:30"
        assert data["slots"][1]["preferred_time"] == "19:30"
        assert data["slots"][0]["schedule_source"] == "BASELINE_OBSERVED"
