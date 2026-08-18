from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RoadmapStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    RECALCULATING = "RECALCULATING"


class PlanDomain(str, Enum):
    SLEEP = "SLEEP"
    WAKE = "WAKE"
    NUTRITION = "NUTRITION"
    MOVEMENT = "MOVEMENT"
    BODY = "BODY"


class PlanItemStatus(str, Enum):
    PLANNED = "PLANNED"
    COMPLETED = "COMPLETED"
    LATE_COMPLETED = "LATE_COMPLETED"
    SKIPPED = "SKIPPED"
    MISSED = "MISSED"


class EvaluationResult(str, Enum):
    SUCCESS = "SUCCESS"
    WITHIN_TOLERANCE = "WITHIN_TOLERANCE"
    MISSED = "MISSED"
    SIGNIFICANT_MISS = "SIGNIFICANT_MISS"


class AdaptationAction(str, Enum):
    ADVANCE_STEP = "ADVANCE_STEP"
    MAINTAIN_STEP = "MAINTAIN_STEP"
    HOLD_TARGET = "HOLD_TARGET"
    REDUCE_STEP_SIZE = "REDUCE_STEP_SIZE"
    ENTER_RECOVERY = "ENTER_RECOVERY"


class PlanItem(BaseModel):
    id: str
    daily_plan_id: str
    domain: PlanDomain
    title: str
    scheduled_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    status: PlanItemStatus = PlanItemStatus.PLANNED
    actual_time: Optional[str] = None
    actual_cost: Optional[float] = None
    item_metadata: Dict[str, Any] = Field(default_factory=dict)
    is_critical: bool = False


class DailyPlan(BaseModel):
    id: str
    roadmap_id: str
    plan_date: str = Field(..., description="Date in YYYY-MM-DD format")
    day_number: int
    target_bedtime: str
    target_wake_time: str
    budget_estimate: float
    items: List[PlanItem] = Field(default_factory=list)
    state: str = "PLANNED"


class DailyEvaluation(BaseModel):
    id: str
    daily_plan_id: str
    evaluation_result: EvaluationResult
    adaptation_action: AdaptationAction
    deviation_minutes: int
    reason: str
    evaluated_at: str


class TransitionRoadmap(BaseModel):
    id: str
    user_id: str
    status: RoadmapStatus = RoadmapStatus.ACTIVE
    start_date: str
    target_end_date: str
    total_days: int
    current_day: int = 1
    current_step_size_minutes: int = 15
    plans: List[DailyPlan] = Field(default_factory=list)
