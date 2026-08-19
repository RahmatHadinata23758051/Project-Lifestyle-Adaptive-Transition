import uuid
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.nutrition_adjustment_proposal import NutritionAdjustmentProposalRecord
from app.nutrition_adjustment_proposal.models import NutritionAdjustmentProposalDTO
from app.nutrition_adjustment_proposal.constants import ProposalLifecycleState


class NutritionAdjustmentProposalRepository:
    @staticmethod
    def save_proposal(
        db: Session,
        owner_user_id: str,
        proposal: NutritionAdjustmentProposalDTO,
    ) -> NutritionAdjustmentProposalRecord:
        prop_id = proposal.proposal_id or str(uuid.uuid4())
        try:
            created_dt = datetime.fromisoformat(proposal.created_at)
        except Exception:
            created_dt = datetime.now(timezone.utc)

        try:
            expires_dt = datetime.fromisoformat(proposal.expires_at)
        except Exception:
            expires_dt = datetime.now(timezone.utc)

        # Atomic supersession with row-level locking to prevent race conditions
        pending_proposals = (
            db.query(NutritionAdjustmentProposalRecord)
            .filter(
                NutritionAdjustmentProposalRecord.owner_user_id == owner_user_id,
                NutritionAdjustmentProposalRecord.proposal_domain == proposal.proposal_domain,
                NutritionAdjustmentProposalRecord.lifecycle_state == ProposalLifecycleState.PENDING.value,
            )
            .with_for_update()
            .all()
        )
        for p in pending_proposals:
            p.lifecycle_state = ProposalLifecycleState.SUPERSEDED.value
            p.resolved_at = created_dt
        db.flush()

        record = NutritionAdjustmentProposalRecord(
            id=prop_id,
            owner_user_id=owner_user_id,
            proposal_domain=proposal.proposal_domain,
            evaluation_id=proposal.evidence_summary.evaluation_id,
            status=proposal.status.value if hasattr(proposal.status, "value") else str(proposal.status),
            lifecycle_state=proposal.lifecycle_state.value if hasattr(proposal.lifecycle_state, "value") else str(proposal.lifecycle_state),
            proposal_type=proposal.proposal_type.value if hasattr(proposal.proposal_type, "value") else str(proposal.proposal_type),
            current_target_kcal=int(proposal.current_target_kcal),
            proposed_target_kcal=int(proposal.proposed_target_kcal),
            delta_kcal=int(proposal.delta_kcal),
            confidence=proposal.confidence.value if hasattr(proposal.confidence, "value") else str(proposal.confidence),
            fingerprint=proposal.fingerprint,
            evidence_snapshot=proposal.evidence_summary.model_dump(),
            risk_flags=[r.value if hasattr(r, "value") else str(r) for r in proposal.risk_flags],
            reason_codes=[r.value if hasattr(r, "value") else str(r) for r in proposal.reason_codes],
            explanations=proposal.explanations,
            policy_versions=proposal.policy_versions,
            created_at=created_dt,
            expires_at=expires_dt,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_proposal_by_id(
        db: Session,
        proposal_id: str,
        owner_user_id: str,
    ) -> Optional[NutritionAdjustmentProposalRecord]:
        return (
            db.query(NutritionAdjustmentProposalRecord)
            .filter(
                NutritionAdjustmentProposalRecord.id == proposal_id,
                NutritionAdjustmentProposalRecord.owner_user_id == owner_user_id,
            )
            .first()
        )

    @staticmethod
    def get_active_pending_proposal(
        db: Session,
        owner_user_id: str,
        proposal_domain: str = "ENERGY_TARGET",
    ) -> Optional[NutritionAdjustmentProposalRecord]:
        return (
            db.query(NutritionAdjustmentProposalRecord)
            .filter(
                NutritionAdjustmentProposalRecord.owner_user_id == owner_user_id,
                NutritionAdjustmentProposalRecord.proposal_domain == proposal_domain,
                NutritionAdjustmentProposalRecord.lifecycle_state == ProposalLifecycleState.PENDING.value,
            )
            .order_by(NutritionAdjustmentProposalRecord.created_at.desc())
            .first()
        )

    @staticmethod
    def list_proposals(
        db: Session,
        owner_user_id: str,
        limit: int = 10,
    ) -> List[NutritionAdjustmentProposalRecord]:
        return (
            db.query(NutritionAdjustmentProposalRecord)
            .filter(NutritionAdjustmentProposalRecord.owner_user_id == owner_user_id)
            .order_by(NutritionAdjustmentProposalRecord.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_lifecycle_state(
        db: Session,
        proposal_id: str,
        owner_user_id: str,
        new_state: ProposalLifecycleState,
        rejection_reason: Optional[str] = None,
    ) -> Optional[NutritionAdjustmentProposalRecord]:
        record = NutritionAdjustmentProposalRepository.get_proposal_by_id(db, proposal_id, owner_user_id)
        if not record:
            return None

        record.lifecycle_state = new_state.value
        record.resolved_at = datetime.now(timezone.utc)
        if rejection_reason:
            record.rejection_reason = rejection_reason

        db.commit()
        db.refresh(record)
        return record
