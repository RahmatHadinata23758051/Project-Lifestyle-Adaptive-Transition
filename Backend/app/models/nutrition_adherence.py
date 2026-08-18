import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class NutritionMealCheckin(Base):
    __tablename__ = "nutrition_meal_checkins"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id = Column(String(36), nullable=False, index=True)
    plan_id = Column(String(100), nullable=False, index=True)
    logical_day_id = Column(String(50), nullable=False, index=True)
    slot_id = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    meal_occurred_at = Column(String(10), nullable=True)
    checked_in_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    actual_spend_idr = Column(Integer, nullable=True)
    deviation_reason = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    certainty = Column(String(20), nullable=False, default="EXACT")
    revision = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    actual_items = relationship("NutritionActualItem", back_populates="checkin", cascade="all, delete-orphan")


class NutritionUnplannedIntake(Base):
    __tablename__ = "nutrition_unplanned_intakes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id = Column(String(36), nullable=False, index=True)
    logical_day_id = Column(String(50), nullable=False, index=True)
    occurred_at = Column(String(10), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    actual_spend_idr = Column(Integer, nullable=True)
    reason = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    items = relationship("NutritionActualItem", back_populates="unplanned_intake", cascade="all, delete-orphan")


class NutritionActualItem(Base):
    __tablename__ = "nutrition_actual_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    checkin_id = Column(String(36), ForeignKey("nutrition_meal_checkins.id", ondelete="CASCADE"), nullable=True, index=True)
    unplanned_intake_id = Column(String(36), ForeignKey("nutrition_unplanned_intakes.id", ondelete="CASCADE"), nullable=True, index=True)
    food_item_id = Column(String(50), nullable=True)
    display_name = Column(String(255), nullable=False)
    serving_id = Column(String(50), nullable=True)
    serving_name = Column(String(100), nullable=True)
    quantity = Column(Float, nullable=False, default=1.0)
    grams = Column(Float, nullable=True)
    energy_kcal = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    carbohydrate_g = Column(Float, nullable=True)
    source_type = Column(String(50), nullable=False, default="USER_REPORTED_UNRESOLVED")
    certainty = Column(String(20), nullable=False, default="EXACT")

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    checkin = relationship("NutritionMealCheckin", back_populates="actual_items")
    unplanned_intake = relationship("NutritionUnplannedIntake", back_populates="items")
