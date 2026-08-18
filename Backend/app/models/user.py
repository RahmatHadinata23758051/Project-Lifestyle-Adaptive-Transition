import uuid
from sqlalchemy import String, Float, Integer, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.schemas.profile import BodyObjective, CookingCapability, ExerciseFacility
from app.schemas.constraints import ConstraintCategory, DayOfWeek


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Jakarta")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    baseline: Mapped["CurrentBaseline"] = relationship("CurrentBaseline", back_populates="user", uselist=False, cascade="all, delete-orphan")
    goal: Mapped["TargetGoal"] = relationship("TargetGoal", back_populates="user", uselist=False, cascade="all, delete-orphan")
    constraints: Mapped[list["ConstraintRecord"]] = relationship("ConstraintRecord", back_populates="user", cascade="all, delete-orphan")
    roadmaps: Mapped[list["Roadmap"]] = relationship("Roadmap", back_populates="user", cascade="all, delete-orphan")


class CurrentBaseline(Base):
    __tablename__ = "baselines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    bedtime: Mapped[str] = mapped_column(String(5), nullable=False)
    wake_time: Mapped[str] = mapped_column(String(5), nullable=False)
    current_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    meals_per_day: Mapped[int] = mapped_column(Integer, default=2)
    weekly_food_budget: Mapped[float] = mapped_column(Float, default=350000.0)
    cooking_access: Mapped[str] = mapped_column(String(50), default=CookingCapability.LIMITED.value)
    exercise_access: Mapped[str] = mapped_column(String(50), default=ExerciseFacility.NO_EQUIPMENT.value)

    user: Mapped["User"] = relationship("User", back_populates="baseline")


class TargetGoal(Base):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    target_wake_time: Mapped[str] = mapped_column(String(5), nullable=False)
    target_bedtime: Mapped[str | None] = mapped_column(String(5), nullable=True)
    body_objective: Mapped[str] = mapped_column(String(50), default=BodyObjective.ROUTINE_ONLY.value)
    target_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_days: Mapped[int] = mapped_column(Integer, default=60)

    user: Mapped["User"] = relationship("User", back_populates="goal")


class ConstraintRecord(Base):
    __tablename__ = "constraints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default=ConstraintCategory.PERSONAL.value)
    day_of_week: Mapped[str] = mapped_column(String(20), default=DayOfWeek.MONDAY.value)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    is_flexible: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship("User", back_populates="constraints")
