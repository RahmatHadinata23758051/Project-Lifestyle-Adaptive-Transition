from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.meal_structure.constants import (
    MealSlotType,
    MealWindowType,
    MealStructureState,
    ScheduleFeasibilityStatus,
    ScheduleProvenance,
    MealScheduleReasonCode,
    MealLocationContext,
    PreparationAvailabilityContext,
    MealPolicy,
)


class MealSlotResponse(BaseModel):
    slot_id: str
    slot_type: MealSlotType
    sequence: int
    preferred_time: str
    earliest_time: str
    latest_time: str
    duration_minutes: int
    target_kcal: float
    min_kcal: float
    max_kcal: float
    schedule_source: ScheduleProvenance
    reason_code: MealScheduleReasonCode
    window_type: MealWindowType = MealWindowType.FLEXIBLE
    is_user_fixed: bool = False
    location_context: MealLocationContext = MealLocationContext.UNKNOWN
    prep_context: PreparationAvailabilityContext = PreparationAvailabilityContext.UNKNOWN

    model_config = ConfigDict(from_attributes=True)


class BaselineMealTimingInput(BaseModel):
    slot_type: MealSlotType = MealSlotType.MAIN_MEAL
    sequence: int
    preferred_time: str
    earliest_time: Optional[str] = None
    latest_time: Optional[str] = None
    duration_minutes: Optional[int] = None


class ConstraintIntervalInput(BaseModel):
    name: str
    start_time: str
    end_time: str
    availability_type: str = "HARD_BLOCK"
    buffer_before_minutes: int = 0
    buffer_after_minutes: int = 0


class MealStructurePreviewInput(BaseModel):
    date: str = "2026-08-19"
    wake_time: Optional[str] = None
    sleep_time: Optional[str] = None
    total_energy_target_kcal: Optional[float] = None
    baseline_meals_per_day: Optional[int] = Field(None, ge=1, le=10)
    baseline_snacks_per_day: Optional[int] = Field(None, ge=0, le=10)
    step_index: int = Field(0, ge=0)
    structure_state: MealStructureState = MealStructureState.BASELINE
    baseline_timings: List[BaselineMealTimingInput] = []
    constraints: List[ConstraintIntervalInput] = []
    custom_energy_shares: Optional[List[float]] = None
    minimum_slot_gap_minutes: Optional[int] = None


class DailyMealScheduleResponse(BaseModel):
    date: str
    logical_day_id: str
    structure_state: MealStructureState
    step_index: int
    energy_target_kcal: float
    feasibility: ScheduleFeasibilityStatus
    slots: List[MealSlotResponse]
    policy_version: str = MealPolicy.VERSION
    assessment_snapshot_id: Optional[str] = None
    reason_codes: List[MealScheduleReasonCode] = []
    explanation: str
    meal_structure_ready: bool
    food_plan_ready: bool = False

    model_config = ConfigDict(from_attributes=True)
