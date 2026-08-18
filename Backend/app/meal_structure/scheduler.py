from typing import List, Optional
from app.engine.time_utils import (
    time_to_minutes,
    minutes_to_time,
    validate_time_string,
)
from app.meal_structure.constants import (
    MealSlotType,
    MealStructureState,
    MealWindowType,
    ScheduleFeasibilityStatus,
    ScheduleProvenance,
    MealScheduleReasonCode,
    MealPolicy,
)
from app.meal_structure.models import (
    MealSlotDTO,
    BaselineMealTiming,
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


def is_time_inside_window_circular(
    start_min: int,
    duration: int,
    earliest_min: int,
    latest_min: int,
) -> bool:
    """
    Validates whether the slot [start_min, start_min + duration] fits entirely
    inside the declared window [earliest_min, latest_min] in circular time (P0.4).
    """
    end_min = (start_min + duration) % 1440
    window_span = (latest_min - earliest_min) % 1440
    if window_span == 0:
        window_span = 1440

    offset_start = (start_min - earliest_min) % 1440
    offset_end = (end_min - earliest_min) % 1440

    return (offset_start <= window_span) and (offset_end <= window_span) and (offset_start <= offset_end or offset_end == 0)


def schedule_daily_meals(
    date: str,
    wake_time: Optional[str],
    sleep_time: Optional[str],
    total_energy_target_kcal: float,
    baseline_meals_per_day: int = 2,
    baseline_snacks_per_day: int = 0,
    step_index: int = 0,
    structure_state: MealStructureState = MealStructureState.BASELINE,
    baseline_timings: Optional[List[BaselineMealTiming]] = None,
    constraints: Optional[List[ConstraintIntervalDTO]] = None,
    fixed_slots: Optional[List[MealSlotDTO]] = None,
    custom_energy_shares: Optional[List[float]] = None,
    minimum_slot_gap_minutes: Optional[int] = None,
    assessment_snapshot_id: Optional[str] = None,
) -> DailyMealScheduleDTO:
    """
    Pure deterministic hardened meal scheduler (P1.1 Hardening).
    - Preserves known baseline timings (P0.1).
    - Dynamically transitions from baseline to target (P0.2).
    - Enforces slot-to-slot spacing based on slot intervals (P0.3).
    - Preserves original window boundaries strictly (P0.4).
    - Rejects equal wake/sleep and short waking spans without silent buffer shrinking (H1, H2).
    - Fully supports cross-midnight logical waking days.
    """
    logical_day_id = f"day_{date}"
    min_gap = minimum_slot_gap_minutes or MealPolicy.DEFAULT_MINIMUM_SLOT_GAP_MINUTES

    # 1. Zero-Guessing Checks for Missing Timing Context
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

    validate_time_string(wake_time)
    validate_time_string(sleep_time)

    # 2. Hardening H2: wake_time == sleep_time is NOT a 24h waking day
    if wake_time == sleep_time:
        return DailyMealScheduleDTO(
            date=date,
            logical_day_id=logical_day_id,
            structure_state=structure_state,
            step_index=step_index,
            energy_target_kcal=total_energy_target_kcal,
            feasibility=ScheduleFeasibilityStatus.NEEDS_MORE_DATA,
            slots=[],
            reason_codes=[MealScheduleReasonCode.INVALID_WAKING_PERIOD],
            explanation="Waktu bangun dan waktu tidur tidak boleh sama.",
            meal_structure_ready=False,
            food_plan_ready=False,
        )

    wake_min = time_to_minutes(wake_time)
    sleep_min = time_to_minutes(sleep_time)
    total_waking_minutes = (sleep_min - wake_min) % 1440
    if total_waking_minutes == 0:
        total_waking_minutes = 1440

    # 3. Hardening H1: Check short waking span without silently shrinking policy buffers
    min_required_span = MealPolicy.DEFAULT_WAKE_BUFFER_MINUTES + MealPolicy.DEFAULT_SLEEP_BUFFER_MINUTES + 30
    if total_waking_minutes < min_required_span:
        return DailyMealScheduleDTO(
            date=date,
            logical_day_id=logical_day_id,
            structure_state=structure_state,
            step_index=step_index,
            energy_target_kcal=total_energy_target_kcal,
            feasibility=ScheduleFeasibilityStatus.INFEASIBLE,
            slots=[],
            reason_codes=[MealScheduleReasonCode.INSUFFICIENT_FREE_WINDOWS],
            explanation="Rentang waktu bangun terlalu pendek untuk menampung buffer bangun dan tidur yang memadai.",
            meal_structure_ready=False,
            food_plan_ready=False,
        )

    # 4. Derive Structure Slots (P0.1 & P0.2)
    raw_slots = calculate_meal_structure_slots(
        baseline_meals_per_day=baseline_meals_per_day,
        baseline_snacks_per_day=baseline_snacks_per_day,
        step_index=step_index,
        structure_state=structure_state,
        baseline_timings=baseline_timings,
    )

    # 5. Distribute Energy Targets
    allocated_slots = allocate_slot_energy_targets(
        total_target_kcal=total_energy_target_kcal,
        slots=raw_slots,
        custom_shares=custom_energy_shares,
    )

    # 6. Generate Initial Timing Windows
    timed_slots = calculate_initial_slot_timings(
        wake_time=wake_time,
        sleep_time=sleep_time,
        slots=allocated_slots,
    )

    # 7. Integrate User-Fixed Slots
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
                    window_type=MealWindowType.FIXED,
                    is_user_fixed=True,
                )

    # 8. Constraint and Spacing Collision Resolution inside declared windows (P0.3 & P0.4)
    constraints = constraints or []
    hard_constraints = [c for c in constraints if c.availability_type == "HARD_BLOCK"]

    reason_codes: List[MealScheduleReasonCode] = []
    has_adjustments = False

    is_cross_midnight = sleep_min < wake_min
    if is_cross_midnight:
        reason_codes.append(MealScheduleReasonCode.CROSS_MIDNIGHT_HANDLED)

    resolved_slots: List[MealSlotDTO] = []
    
    for slot in timed_slots:
        slot_pref_min = time_to_minutes(slot.preferred_time)
        earliest_min = time_to_minutes(slot.earliest_time)
        latest_min = time_to_minutes(slot.latest_time)
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

            # P0.4: Check if current_start_min is within the slot's original window bounds
            if not is_time_inside_window_circular(current_start_min, slot_duration, earliest_min, latest_min):
                reason_codes.append(MealScheduleReasonCode.OUTSIDE_ORIGINAL_WINDOW)
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
                    explanation=f"Slot '{slot.slot_id}' tidak dapat dijadwalkan di dalam jendela waktu aslinya ({slot.earliest_time}–{slot.latest_time}).",
                    meal_structure_ready=False,
                    food_plan_ready=False,
                )

            # Check constraint overlap
            for c in hard_constraints:
                c_start = (time_to_minutes(c.start_time) - c.buffer_before_minutes) % 1440
                c_end = (time_to_minutes(c.end_time) + c.buffer_after_minutes) % 1440

                if is_interval_overlapping_circular(current_start_min, slot_end_min, c_start, c_end):
                    if slot.is_user_fixed or slot.window_type == MealWindowType.FIXED:
                        # User-fixed / FIXED slots are NEVER silently moved! Explicit conflict reported.
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
                            explanation=f"Slot tetap '{slot.preferred_time}' bertabrakan dengan jadwal tidak fleksibel '{c.name}'.",
                            meal_structure_ready=False,
                            food_plan_ready=False,
                        )

                    # Try shifting forward after constraint
                    current_start_min = (c_end + MealPolicy.CONSTRAINT_SHIFT_STEP_MINUTES) % 1440
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

        # Update slot timing preserving original window bounds (P0.4)
        preferred_str = minutes_to_time(current_start_min)

        resolved_slots.append(
            MealSlotDTO(
                slot_id=slot.slot_id,
                slot_type=slot.slot_type,
                sequence=slot.sequence,
                preferred_time=preferred_str,
                earliest_time=slot.earliest_time,  # Preserved original window earliest
                latest_time=slot.latest_time,      # Preserved original window latest
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

    # 9. P0.3: Multi-Slot Spacing Enforcement (Slot End -> Next Slot Start)
    if len(resolved_slots) > 1:
        for i in range(len(resolved_slots) - 1):
            s_curr = resolved_slots[i]
            s_next = resolved_slots[i + 1]

            curr_end = (time_to_minutes(s_curr.preferred_time) + s_curr.duration_minutes) % 1440
            next_start = time_to_minutes(s_next.preferred_time)

            gap = (next_start - curr_end) % 1440
            if gap < min_gap:
                # Spacing violation
                reason_codes.append(MealScheduleReasonCode.MEAL_SPACING_CONFLICT)
                return DailyMealScheduleDTO(
                    date=date,
                    logical_day_id=logical_day_id,
                    structure_state=structure_state,
                    step_index=step_index,
                    energy_target_kcal=total_energy_target_kcal,
                    feasibility=ScheduleFeasibilityStatus.INFEASIBLE,
                    slots=resolved_slots,
                    policy_version=MealPolicy.VERSION,
                    assessment_snapshot_id=assessment_snapshot_id,
                    reason_codes=reason_codes,
                    explanation=f"Jarak jeda antar makan ({gap} menit) lebih kecil dari batas minimum ({min_gap} menit).",
                    meal_structure_ready=False,
                    food_plan_ready=False,
                )

    if has_adjustments:
        reason_codes.append(MealScheduleReasonCode.CONSTRAINT_COLLISION)
        feasibility_status = ScheduleFeasibilityStatus.FEASIBLE_WITH_ADJUSTMENTS
    else:
        if baseline_timings and (structure_state == MealStructureState.BASELINE or step_index == 0):
            reason_codes.append(MealScheduleReasonCode.BASELINE_TIME_PRESERVED)
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
