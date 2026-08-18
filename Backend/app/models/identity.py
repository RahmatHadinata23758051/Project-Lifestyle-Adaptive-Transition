import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import String, Float, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class OnboardingStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class GoalDomain(str, Enum):
    SLEEP_ROUTINE = "SLEEP_ROUTINE"
    NUTRITION_WEIGHT_GAIN = "NUTRITION_WEIGHT_GAIN"
    PHYSICAL_ACTIVITY = "PHYSICAL_ACTIVITY"


class GoalPriority(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    SUPPORTING = "SUPPORTING"


class GoalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ACHIEVED = "ACHIEVED"


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    birth_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)  # MALE, FEMALE, TBD
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Jakarta")
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    occupation_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # STUDENT, WORKER, FREELANCE, TBD
    onboarding_status: Mapped[str] = mapped_column(String(50), default=OnboardingStatus.NOT_STARTED.value)
    created_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())


class UserGoal(Base):
    __tablename__ = "user_goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(50), default=GoalDomain.SLEEP_ROUTINE.value)
    priority: Mapped[str] = mapped_column(String(50), default=GoalPriority.PRIMARY.value)
    status: Mapped[str] = mapped_column(String(50), default=GoalStatus.ACTIVE.value)
    target_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())


class SleepBaseline(Base):
    __tablename__ = "sleep_baselines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    bedtime: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    wake_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    captured_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())
    created_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    weekly_food_budget: Mapped[float] = mapped_column(Float, default=350000.0)
    currency: Mapped[str] = mapped_column(String(10), default="IDR")
    created_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)  # WEIGHT, WAKE_TIME, BEDTIME, EXPENSE
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    string_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    captured_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())
    created_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())
