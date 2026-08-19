import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, UniqueConstraint
from app.db.base import Base


class NutritionStateRevisionRecord(Base):
    __tablename__ = "nutrition_state_revisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id = Column(String(36), nullable=False, index=True)
    revision_number = Column(Integer, nullable=False, index=True)
    previous_revision_id = Column(String(36), nullable=True)
    source_type = Column(String(50), nullable=False, default="USER_CONFIRMED_ADJUSTMENT")
    source_reference_id = Column(String(50), nullable=True)
    target_energy_kcal = Column(Integer, nullable=False)
    goal_type = Column(String(50), nullable=False, default="NUTRITION_WEIGHT_GAIN")
    effective_from = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("owner_user_id", "revision_number", name="uq_owner_nutrition_revision"),
    )
