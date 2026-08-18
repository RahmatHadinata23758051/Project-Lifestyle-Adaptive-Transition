from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from app.engine.time_utils import validate_time_string


class ConstraintCategory(str, Enum):
    SCHOOL = "SCHOOL"
    UNIVERSITY = "UNIVERSITY"
    WORK = "WORK"
    COMMUTE = "COMMUTE"
    WORSHIP = "WORSHIP"
    FAMILY = "FAMILY"
    PERSONAL = "PERSONAL"


class DayOfWeek(str, Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class UserConstraint(BaseModel):
    id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=100)
    category: ConstraintCategory
    day_of_week: DayOfWeek
    start_time: str
    end_time: str
    is_flexible: bool = False

    @field_validator("start_time", "end_time")
    @classmethod
    def check_valid_time(cls, v: str) -> str:
        if not validate_time_string(v):
            raise ValueError(f"Invalid time format '{v}'. Expected 24h format HH:MM (00:00 to 23:59).")
        return v


class FinancialProfile(BaseModel):
    weekly_food_budget: float = Field(..., ge=0.0)
    daily_budget_cap: float = Field(..., ge=0.0)
    currency: str = "IDR"
    current_spent: float = 0.0
