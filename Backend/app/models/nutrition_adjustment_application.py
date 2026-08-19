import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON, UniqueConstraint
from app.db.base import Base


class NutritionAdjustmentApplicationRecord(Base):
    __tablename__ = "nutrition_adjustment_applications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id = Column(String(36), nullable=False, index=True)
    proposal_id = Column(String(50), nullable=False, unique=True, index=True)
    idempotency_key = Column(String(128), nullable=False, index=True)
    previous_state_revision = Column(Integer, nullable=False)
    new_state_revision = Column(Integer, nullable=False)
    previous_target_kcal = Column(Integer, nullable=False)
    applied_target_kcal = Column(Integer, nullable=False)
    delta_kcal = Column(Integer, nullable=False)
    application_status = Column(String(50), nullable=False, default="APPLIED")
    downstream_invalidation = Column(JSON, nullable=False, default=dict)
    applied_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    policy_versions = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("owner_user_id", "idempotency_key", name="uq_owner_idempotency_key"),
    )
