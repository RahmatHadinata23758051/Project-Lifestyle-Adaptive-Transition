import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class NutritionBaseline(Base):
    __tablename__ = "nutrition_baselines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    meals_per_day: Mapped[int] = mapped_column(Integer, default=3)
    cooking_capability: Mapped[str] = mapped_column(String(50), default="LIMITED")
    allergies: Mapped[str] = mapped_column(String(255), default="NONE")
    food_restrictions: Mapped[str | None] = mapped_column(String(255), nullable=True)
    food_preferences: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    captured_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())
    created_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())


class ActivityBaseline(Base):
    __tablename__ = "activity_baselines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    experience_level: Mapped[str] = mapped_column(String(50), default="BEGINNER")
    available_days_per_week: Mapped[int] = mapped_column(Integer, default=3)
    minutes_per_session: Mapped[int] = mapped_column(Integer, default=30)
    equipment_list: Mapped[str] = mapped_column(Text, default="NONE")  # JSON or comma-separated
    physical_limitations: Mapped[str] = mapped_column(String(255), default="NONE")
    available_space: Mapped[str | None] = mapped_column(String(50), nullable=True)
    workout_preference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    captured_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())
    created_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())


class AssessmentSnapshotRecord(Base):
    __tablename__ = "assessment_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    snapshot_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON formatted snapshot
    created_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())
