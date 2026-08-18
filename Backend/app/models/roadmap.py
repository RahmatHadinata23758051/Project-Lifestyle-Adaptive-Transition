import uuid
from sqlalchemy import String, Float, Integer, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.schemas.roadmap import RoadmapStatus, PlanDomain, PlanItemStatus, EvaluationResult, AdaptationAction


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=RoadmapStatus.ACTIVE.value)
    start_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    target_end_date: Mapped[str] = mapped_column(String(10), nullable=False)
    total_days: Mapped[int] = mapped_column(Integer, nullable=False)
    current_day: Mapped[int] = mapped_column(Integer, default=1)
    current_step_index: Mapped[int] = mapped_column(Integer, default=0)
    current_step_size_minutes: Mapped[int] = mapped_column(Integer, default=15)

    user: Mapped["User"] = relationship("User", back_populates="roadmaps")
    plans: Mapped[list["DailyPlanRecord"]] = relationship("DailyPlanRecord", back_populates="roadmap", cascade="all, delete-orphan")


class DailyPlanRecord(Base):
    __tablename__ = "daily_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    roadmap_id: Mapped[str] = mapped_column(String(36), ForeignKey("roadmaps.id"), nullable=False)
    plan_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, default=0)
    target_bedtime: Mapped[str] = mapped_column(String(5), nullable=False)
    target_wake_time: Mapped[str] = mapped_column(String(5), nullable=False)
    budget_estimate: Mapped[float] = mapped_column(Float, default=50000.0)
    state: Mapped[str] = mapped_column(String(50), default="PLANNED")

    roadmap: Mapped["Roadmap"] = relationship("Roadmap", back_populates="plans")
    items: Mapped[list["PlanItemRecord"]] = relationship("PlanItemRecord", back_populates="daily_plan", cascade="all, delete-orphan")
    evaluation: Mapped["DailyEvaluationRecord"] = relationship("DailyEvaluationRecord", back_populates="daily_plan", uselist=False, cascade="all, delete-orphan")


class PlanItemRecord(Base):
    __tablename__ = "plan_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    daily_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("daily_plans.id"), nullable=False)
    domain: Mapped[str] = mapped_column(String(50), default=PlanDomain.WAKE.value)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    scheduled_time: Mapped[str] = mapped_column(String(5), nullable=False)
    preferred_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=15)
    is_movable: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(50), default=PlanItemStatus.PLANNED.value)
    actual_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    actual_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)

    daily_plan: Mapped["DailyPlanRecord"] = relationship("DailyPlanRecord", back_populates="items")


class DailyEvaluationRecord(Base):
    __tablename__ = "daily_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    daily_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("daily_plans.id"), nullable=False)
    evaluation_result: Mapped[str] = mapped_column(String(50), nullable=False)
    adaptation_action: Mapped[str] = mapped_column(String(50), nullable=False)
    deviation_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_delta_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_at: Mapped[str] = mapped_column(String(50), nullable=False)

    daily_plan: Mapped["DailyPlanRecord"] = relationship("DailyPlanRecord", back_populates="evaluation")
