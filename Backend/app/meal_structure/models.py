from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
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


@dataclass
class MealStructureDefinition:
    main_meals: int
    snacks: int = 0


@dataclass
class BaselineMealTiming:
    slot_type: MealSlotType
    sequence: int
    preferred_time: str
    earliest_time: Optional[str] = None
    latest_time: Optional[str] = None
    duration_minutes: Optional[int] = None


@dataclass
class MealSlotDTO:
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


@dataclass
class ConstraintIntervalDTO:
    name: str
    start_time: str
    end_time: str
    availability_type: str = "HARD_BLOCK"  # HARD_BLOCK, SOFT_BLOCK, MEAL_COMPATIBLE
    buffer_before_minutes: int = 0
    buffer_after_minutes: int = 0


@dataclass
class DailyMealScheduleDTO:
    date: str
    logical_day_id: str
    structure_state: MealStructureState
    step_index: int
    energy_target_kcal: float
    feasibility: ScheduleFeasibilityStatus
    slots: List[MealSlotDTO]
    policy_version: str = MealPolicy.VERSION
    assessment_snapshot_id: Optional[str] = None
    reason_codes: List[MealScheduleReasonCode] = field(default_factory=list)
    explanation: str = ""
    meal_structure_ready: bool = True
    food_plan_ready: bool = False
