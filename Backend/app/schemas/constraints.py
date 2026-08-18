from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


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
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Start time in HH:MM")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="End time in HH:MM")
    is_flexible: bool = False


class FinancialProfile(BaseModel):
    weekly_food_budget: float = Field(..., ge=0.0)
    daily_budget_cap: float = Field(..., ge=0.0)
    currency: str = "IDR"
    current_spent: float = 0.0
