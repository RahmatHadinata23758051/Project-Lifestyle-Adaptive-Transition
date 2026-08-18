from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.models.identity import OnboardingStatus, GoalDomain, GoalPriority, GoalStatus
from app.schemas.constraints import ConstraintCategory, DayOfWeek
from app.engine.time_utils import validate_time_string


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    display_name: Optional[str] = None
    birth_date: Optional[str] = None
    sex: Optional[str] = None
    timezone: str = "Asia/Jakarta"
    height_cm: Optional[float] = None
    current_weight_kg: Optional[float] = None
    occupation_type: Optional[str] = None
    onboarding_status: OnboardingStatus = OnboardingStatus.NOT_STARTED
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    birth_date: Optional[str] = None
    sex: Optional[str] = None
    timezone: Optional[str] = None
    height_cm: Optional[float] = None
    current_weight_kg: Optional[float] = None
    occupation_type: Optional[str] = None
    onboarding_status: Optional[OnboardingStatus] = None


class GoalCreate(BaseModel):
    domain: GoalDomain = GoalDomain.SLEEP_ROUTINE
    priority: GoalPriority = GoalPriority.PRIMARY
    status: GoalStatus = GoalStatus.ACTIVE
    target_description: Optional[str] = None


class GoalResponse(BaseModel):
    id: str
    user_id: str
    domain: GoalDomain
    priority: GoalPriority
    status: GoalStatus
    target_description: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class SleepBaselineCreate(BaseModel):
    bedtime: str = Field(..., description="Waktu tidur format HH:MM")
    wake_time: str = Field(..., description="Waktu bangun format HH:MM")

    @field_validator("bedtime", "wake_time")
    @classmethod
    def check_time_format(cls, v: str) -> str:
        if not validate_time_string(v):
            raise ValueError(f"Waktu '{v}' tidak valid. Gunakan format 24 jam HH:MM (00:00 - 23:59).")
        return v


class SleepBaselineResponse(BaseModel):
    id: str
    user_id: str
    bedtime: str
    wake_time: str
    is_current: bool
    captured_at: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class FinancialProfileUpdate(BaseModel):
    weekly_food_budget: float = Field(..., ge=0.0, description="Alokasi anggaran makan mingguan")
    currency: str = "IDR"


class FinancialProfileResponse(BaseModel):
    id: str
    user_id: str
    weekly_food_budget: float
    currency: str
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class ConstraintCreate(BaseModel):
    title: str = Field(..., max_length=100)
    category: ConstraintCategory = ConstraintCategory.PERSONAL
    day_of_week: DayOfWeek = DayOfWeek.MONDAY
    start_time: str
    end_time: str
    is_flexible: bool = False

    @field_validator("start_time", "end_time")
    @classmethod
    def check_time_format(cls, v: str) -> str:
        if not validate_time_string(v):
            raise ValueError(f"Waktu '{v}' tidak valid. Gunakan format 24 jam HH:MM (00:00 - 23:59).")
        return v


class ConstraintResponse(BaseModel):
    id: str
    user_id: str
    title: str
    category: str
    day_of_week: str
    start_time: str
    end_time: str
    is_flexible: bool

    model_config = ConfigDict(from_attributes=True)
