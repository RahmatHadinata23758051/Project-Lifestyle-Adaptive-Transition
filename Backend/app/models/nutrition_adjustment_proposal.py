import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from app.db.base import Base


class NutritionAdjustmentProposalRecord(Base):
    __tablename__ = "nutrition_adjustment_proposals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id = Column(String(36), nullable=False, index=True)
    proposal_domain = Column(String(50), nullable=False, default="ENERGY_TARGET", index=True)
    evaluation_id = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    lifecycle_state = Column(String(30), nullable=False, default="PENDING", index=True)
    proposal_type = Column(String(50), nullable=False)
    current_target_kcal = Column(Integer, nullable=False)
    proposed_target_kcal = Column(Integer, nullable=False)
    delta_kcal = Column(Integer, nullable=False)
    confidence = Column(String(20), nullable=False)
    fingerprint = Column(String(64), nullable=False, index=True)
    evidence_snapshot = Column(JSON, nullable=False, default=dict)
    risk_flags = Column(JSON, nullable=False, default=list)
    reason_codes = Column(JSON, nullable=False, default=list)
    explanations = Column(JSON, nullable=False, default=list)
    policy_versions = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(String(255), nullable=True)
