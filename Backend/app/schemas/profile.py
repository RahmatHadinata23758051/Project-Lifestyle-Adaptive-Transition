from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


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
    bedtime: str = Field(..., description="Current bedtime in HH:MM format", pattern=r"^\d{2}:\d{2}$")
    wake_time: str = Field(..., description="Current wake time in HH:MM format", pattern=r"^\d{2}:\d{2}$")
    current_weight: Optional[float] = Field(None, ge=30.0, le=250.0, description="Weight in kg")
    meals_per_day: int = Field(2, ge=1, le=6, description="Typical meal count per day")
    weekly_food_budget: float = Field(..., ge=0.0, description="Weekly food budget amount")
    cooking_access: CookingCapability = CookingCapability.LIMITED
    exercise_access: ExerciseFacility = ExerciseFacility.NO_EQUIPMENT


class TargetSelfGoal(BaseModel):
    target_wake_time: str = Field(..., description="Target wake time in HH:MM format", pattern=r"^\d{2}:\d{2}$")
    target_bedtime: Optional[str] = Field(None, description="Target bedtime in HH:MM format", pattern=r"^\d{2}:\d{2}$")
    body_objective: BodyObjective = BodyObjective.ROUTINE_ONLY
    target_weight: Optional[float] = Field(None, ge=30.0, le=250.0, description="Target weight in kg")
    duration_days: int = Field(..., ge=7, le=180, description="Requested transition duration in days")


class UserProfile(BaseModel):
    id: str
    email: str
    timezone: str = "Asia/Jakarta"
    baseline: CurrentSelfBaseline
    goal: TargetSelfGoal
    is_active: bool = True
