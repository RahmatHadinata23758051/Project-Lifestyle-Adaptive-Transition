from typing import List, Optional
from app.engine.time_utils import (
    time_to_minutes,
    minutes_to_time,
    validate_time_string,
)
from app.meal_structure.constants import (
    MealSlotType,
    MealStructureState,
    ScheduleFeasibilityStatus,
    ScheduleProvenance,
    MealScheduleReasonCode,
    MealPolicy,
)
from app.meal_structure.models import (
    MealSlotDTO,
    ConstraintIntervalDTO,
    DailyMealScheduleDTO,
)
from app.meal_structure.structure import calculate_meal_structure_slots
from app.meal_structure.energy_distribution import allocate_slot_energy_targets
from app.meal_structure.windows import calculate_initial_slot_timings


def is_interval_overlapping_circular(
    start_a: int,
    end_a: int,
    start_b: int,
    end_b: int,
) -> bool:
    """Checks overlap between two time intervals on a 1440-minute circular clock."""
    span_a = (end_a - start_a) % 1440
    if span_a == 0:
        span_a = 1440

    offset_start_b = (start_b - start_a) % 1440
    offset_end_b = (end_b - start_a) % 1440

    if offset_start_b < span_a:
        return True
    if offset_end_b < span_a and offset_end_b > 0:
        return True
    if offset_start_b > offset_end_b and offset_end_b > 0:
        return True

    return False


def schedule_daily_meals(
    date: str,
    wake_time: Optional[str],
    sleep_time: Optional[str],
    total_energy_target_kcal: float,
    baseline_meals_per_day: int = 2,
    baseline_snacks_per_day: int = 0,
    step_index: int = 0,
    structure_state: MealStructureState = MealStructureState.BASELINE,
    constraints: Optional[List[ConstraintIntervalDTO]] = None,
    fixed_slots: Optional[List[MealSlotDTO]] = None,
    custom_energy_shares: Optional[List[float]] = None,
    assessment_snapshot_id: Optional[str] = None,
) -> DailyMealScheduleDTO:
    """
    Pure deterministic meal scheduler.
    Coordinates sleep transition context, baseline meal structure, life constraints,
    cross-midnight waking periods, and energy share allocations.
    """
    logical_day_id = f"day_{date}"

    # 1. Check Missing Timing Context (Zero-Guessing Invariant)
    if not wake_time:
        return DailyMealScheduleDTO(
            date=date,
            logical_day_id=logical_day_id,
            structure_state=structure_state,
            step_index=step_index,
            energy_target_kcal=total_energy_target_kcal,
            feasibility=ScheduleFeasibilityStatus.NEEDS_MORE_DATA,
            slots=[],
            reason_codes=[MealScheduleReasonCode.NO_WAKE_CONTEXT],
            explanation="Jadwal makan tidak dapat dibuat karena waktu bangun (wake_time) belum ditentukan.",
            meal_structure_ready=False,
            food_plan_ready=False,
        )

    if not sleep_time:
        return DailyMealScheduleDTO(
            date=date,
            logical_day_id=logical_day_id,
            structure_state=structure_state,
            step_index=step_index,
            energy_target_kcal=total_energy_target_kcal,
            feasibility=ScheduleFeasibilityStatus.NEEDS_MORE_DATA,
            slots=[],
            reason_codes=[MealScheduleReasonCode.NO_SLEEP_CONTEXT],
            explanation="Jadwal makan tidak dapat dibuat karena waktu tidur (sleep_time) belum ditentukan.",
            meal_structure_ready=False,
            food_plan_ready=False,
        )

    # 2. Derive Slots from Structure State and Step Index
    raw_slots = calculate_meal_structure_slots(
        baseline_meals_per_day=baseline_meals_per_day,
        baseline_snacks_per_day=baseline_snacks_per_day,
        step_index=step_index,
        structure_state=structure_state,
    )

    # 3. Distribute Energy Targets
    allocated_slots = allocate_slot_energy_targets(
        total_target_kcal=total_energy_target_kcal,
        slots=raw_slots,
        custom_shares=custom_energy_shares,
    )

    # 4. Generate Initial Timing Windows
    timed_slots = calculate_initial_slot_timings(
        wake_time=wake_time,
        sleep_time=sleep_time,
        slots=allocated_slots,
    )

    # 5. Integrate User-Fixed Slots
    fixed_slots = fixed_slots or []
    for fs in fixed_slots:
        for idx, ts in enumerate(timed_slots):
            if ts.sequence == fs.sequence or ts.slot_id == fs.slot_id:
                timed_slots[idx] = MealSlotDTO(
                    slot_id=fs.slot_id,
                    slot_type=fs.slot_type,
                    sequence=fs.sequence,
                    preferred_time=fs.preferred_time,
                    earliest_time=fs.earliest_time,
                    latest_time=fs.latest_time,
                    duration_minutes=fs.duration_minutes,
                    target_kcal=ts.target_kcal,
                    min_kcal=ts.min_kcal,
                    max_kcal=ts.max_kcal,
                    schedule_source=ScheduleProvenance.USER_FIXED,
                    reason_code=MealScheduleReasonCode.NORMAL_BASELINE,
                    window_type=fs.window_type,
                    is_user_fixed=True,
                )

    # 6. Collision Resolution with Constraints
    constraints = constraints or []
    hard_constraints = [c for c in constraints if c.availability_type == "HARD_BLOCK"]

    reason_codes: List[MealScheduleReasonCode] = []
    has_adjustments = False

    wake_min = time_to_minutes(wake_time)
    sleep_min = time_to_minutes(sleep_time)
    total_waking_minutes = (sleep_min - wake_min) % 1440
    if total_waking_minutes == 0:
        total_waking_minutes = 1440

    is_cross_midnight = sleep_min < wake_min

    if is_cross_midnight:
        reason_codes.append(MealScheduleReasonCode.CROSS_MIDNIGHT_HANDLED)

    resolved_slots: List[MealSlotDTO] = []
    
    for slot in timed_slots:
        slot_pref_min = time_to_minutes(slot.preferred_time)
        slot_duration = slot.duration_minutes
        current_start_min = slot_pref_min
        slot_reason = slot.reason_code
        slot_source = slot.schedule_source

        iteration = 0
        collision_found = True

        while collision_found and iteration < MealPolicy.MAX_SCHEDULER_ITERATIONS:
            iteration += 1
            collision_found = False
            slot_end_min = (current_start_min + slot_duration) % 1440

            # Check if current slot falls outside the waking span
            waking_offset = (current_start_min - wake_min) % 1440
            if waking_offset + slot_duration > total_waking_minutes:
                # Slot has been pushed beyond the waking day
                reason_codes.append(MealScheduleReasonCode.INSUFFICIENT_FREE_WINDOWS)
                return DailyMealScheduleDTO(
                    date=date,
                    logical_day_id=logical_day_id,
                    structure_state=structure_state,
                    step_index=step_index,
                    energy_target_kcal=total_energy_target_kcal,
                    feasibility=ScheduleFeasibilityStatus.INFEASIBLE,
                    slots=[],
                    policy_version=MealPolicy.VERSION,
                    assessment_snapshot_id=assessment_snapshot_id,
                    reason_codes=reason_codes,
                    explanation="Tidak ditemukan jendela waktu yang layak di dalam jam bangun pengguna.",
                    meal_structure_ready=False,
                    food_plan_ready=False,
                )

            for c in hard_constraints:
                c_start = (time_to_minutes(c.start_time) - c.buffer_before_minutes) % 1440
                c_end = (time_to_minutes(c.end_time) + c.buffer_after_minutes) % 1440

                if is_interval_overlapping_circular(current_start_min, slot_end_min, c_start, c_end):
                    if slot.is_user_fixed:
                        # User-fixed slots are NEVER silently moved! Explicit conflict reported.
                        reason_codes.append(MealScheduleReasonCode.FIXED_SLOT_CONFLICT)
                        return DailyMealScheduleDTO(
                            date=date,
                            logical_day_id=logical_day_id,
                            structure_state=structure_state,
                            step_index=step_index,
                            energy_target_kcal=total_energy_target_kcal,
                            feasibility=ScheduleFeasibilityStatus.INFEASIBLE,
                            slots=timed_slots,
                            policy_version=MealPolicy.VERSION,
                            assessment_snapshot_id=assessment_snapshot_id,
                            reason_codes=reason_codes,
                            explanation=f"Slot makan tetap pengguna '{slot.preferred_time}' bertabrakan dengan jadwal tidak fleksibel '{c.name}'.",
                            meal_structure_ready=False,
                            food_plan_ready=False,
                        )

                    # Shift flexible slot forward after hard constraint
                    current_start_min = (c_end + 10) % 1440
                    slot_source = ScheduleProvenance.SHIFTED_FOR_CONSTRAINT
                    slot_reason = MealScheduleReasonCode.SHIFTED_AFTER_HARD_CONSTRAINT
                    collision_found = True
                    has_adjustments = True
                    break

        if iteration >= MealPolicy.MAX_SCHEDULER_ITERATIONS:
            reason_codes.append(MealScheduleReasonCode.INSUFFICIENT_FREE_WINDOWS)
            return DailyMealScheduleDTO(
                date=date,
                logical_day_id=logical_day_id,
                structure_state=structure_state,
                step_index=step_index,
                energy_target_kcal=total_energy_target_kcal,
                feasibility=ScheduleFeasibilityStatus.INFEASIBLE,
                slots=[],
                policy_version=MealPolicy.VERSION,
                assessment_snapshot_id=assessment_snapshot_id,
                reason_codes=reason_codes,
                explanation="Tidak ditemukan jendela waktu yang layak di antara jadwal kesibukan pengguna.",
                meal_structure_ready=False,
                food_plan_ready=False,
            )

        # Update slot timing
        preferred_str = minutes_to_time(current_start_min)
        earliest_str = minutes_to_time((current_start_min - 30) % 1440)
        latest_str = minutes_to_time((current_start_min + 30) % 1440)

        resolved_slots.append(
            MealSlotDTO(
                slot_id=slot.slot_id,
                slot_type=slot.slot_type,
                sequence=slot.sequence,
                preferred_time=preferred_str,
                earliest_time=earliest_str,
                latest_time=latest_str,
                duration_minutes=slot.duration_minutes,
                target_kcal=slot.target_kcal,
                min_kcal=slot.min_kcal,
                max_kcal=slot.max_kcal,
                schedule_source=slot_source,
                reason_code=slot_reason,
                window_type=slot.window_type,
                is_user_fixed=slot.is_user_fixed,
                location_context=slot.location_context,
                prep_context=slot.prep_context,
            )
        )

    if has_adjustments:
        reason_codes.append(MealScheduleReasonCode.CONSTRAINT_COLLISION)
        feasibility_status = ScheduleFeasibilityStatus.FEASIBLE_WITH_ADJUSTMENTS
    else:
        reason_codes.append(MealScheduleReasonCode.NORMAL_BASELINE)
        feasibility_status = ScheduleFeasibilityStatus.FEASIBLE

    explanation = (
        f"Jadwal makan {len(resolved_slots)} slot berhasil disusun untuk hari bangun logis "
        f"(bangun: {wake_time}, tidur: {sleep_time}). Alokasi energi: {total_energy_target_kcal:.0f} kcal."
    )

    return DailyMealScheduleDTO(
        date=date,
        logical_day_id=logical_day_id,
        structure_state=structure_state,
        step_index=step_index,
        energy_target_kcal=total_energy_target_kcal,
        feasibility=feasibility_status,
        slots=resolved_slots,
        policy_version=MealPolicy.VERSION,
        assessment_snapshot_id=assessment_snapshot_id,
        reason_codes=reason_codes,
        explanation=explanation,
        meal_structure_ready=True,
        food_plan_ready=False,
    )
