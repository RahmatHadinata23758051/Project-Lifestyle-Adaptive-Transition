from enum import Enum
from typing import Optional, Annotated
from pydantic import BaseModel, Field, field_validator
from app.engine.time_utils import validate_time_string


TimeString = Annotated[str, Field(..., description="Time string in 24h HH:MM format (00:00 to 23:59)")]


class BodyObjective(str, Enum):
    WEIGHT_GAIN = "WEIGHT_GAIN"
    WEIGHT_LOSS = "WEIGHT_LOSS"
    MAINTENANCE = "MAINTENANCE"
    ROUTINE_ONLY = "ROUTINE_ONLY"


class CookingCapability(str, Enum):
    CAN_COOK = "CAN_COOK"
    LIMITED = "LIMITED"
    BUY_ONLY = "BUY_ONLY"


class ExerciseFacility(str, Enum):
    NO_EQUIPMENT = "NO_EQUIPMENT"
    HOME_DUMBBELL = "HOME_DUMBBELL"
    GYM_ACCESS = "GYM_ACCESS"


class CurrentSelfBaseline(BaseModel):
    bedtime: str
    wake_time: str
    current_weight: Optional[float] = Field(None, ge=30.0, le=250.0, description="Weight in kg")
    meals_per_day: int = Field(2, ge=1, le=6, description="Typical meal count per day")
    weekly_food_budget: float = Field(..., ge=0.0, description="Weekly food budget amount")
    cooking_access: CookingCapability = CookingCapability.LIMITED
    exercise_access: ExerciseFacility = ExerciseFacility.NO_EQUIPMENT

    @field_validator("bedtime", "wake_time")
    @classmethod
    def check_valid_time(cls, v: str) -> str:
        if not validate_time_string(v):
            raise ValueError(f"Invalid time format '{v}'. Expected 24h format HH:MM (00:00 to 23:59).")
        return v


class TargetSelfGoal(BaseModel):
    target_wake_time: str
    target_bedtime: Optional[str] = None
    body_objective: BodyObjective = BodyObjective.ROUTINE_ONLY
    target_weight: Optional[float] = Field(None, ge=30.0, le=250.0, description="Target weight in kg")
    duration_days: int = Field(..., ge=7, le=180, description="Requested transition duration in days")

    @field_validator("target_wake_time", "target_bedtime")
    @classmethod
    def check_valid_target_time(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not validate_time_string(v):
            raise ValueError(f"Invalid time format '{v}'. Expected 24h format HH:MM (00:00 to 23:59).")
        return v


class UserProfile(BaseModel):
    id: str
    email: str
    timezone: str = "Asia/Jakarta"
    baseline: CurrentSelfBaseline
    goal: TargetSelfGoal
    is_active: bool = True
