import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON
from app.db.base import Base


class NutritionAdaptationEvaluationRecord(Base):
    __tablename__ = "nutrition_adaptation_evaluations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id = Column(String(36), nullable=False, index=True)
    evaluated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    decision = Column(String(50), nullable=False)
    review_domain = Column(String(50), nullable=False)
    confidence = Column(String(20), nullable=False)
    window_start = Column(String(20), nullable=False)
    window_end = Column(String(20), nullable=False)
    total_days = Column(Integer, nullable=False)
    usable_days = Column(Integer, nullable=False)
    weight_measurements_count = Column(Integer, nullable=False)
    slope_kg_per_day = Column(Float, nullable=True)
    weight_direction = Column(String(30), nullable=False)
    adherence_category = Column(String(50), nullable=False)
    reason_codes = Column(JSON, nullable=False, default=list)
    explanations = Column(JSON, nullable=False, default=list)
    policy_version = Column(String(50), nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
