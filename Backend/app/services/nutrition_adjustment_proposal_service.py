from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.nutrition_adjustment_proposal.models import (
    NutritionAdjustmentProposalInputDTO,
    NutritionAdjustmentProposalDTO,
)
from app.nutrition_adjustment_proposal.constants import (
    ProposalLifecycleState,
    ProposalStatus,
)
from app.nutrition_adjustment_proposal.proposal import build_nutrition_adjustment_proposal
from app.repositories.nutrition_adjustment_proposal_repository import (
    NutritionAdjustmentProposalRepository,
)


class NutritionAdjustmentProposalService:
    @staticmethod
    def preview_proposal(
        input_dto: NutritionAdjustmentProposalInputDTO,
    ) -> NutritionAdjustmentProposalDTO:
        return build_nutrition_adjustment_proposal(input_dto)

    @staticmethod
    def create_proposal(
        db: Session,
        owner_user_id: str,
        input_dto: NutritionAdjustmentProposalInputDTO,
    ) -> NutritionAdjustmentProposalDTO:
        input_dto.user_id = owner_user_id
        proposal = build_nutrition_adjustment_proposal(input_dto)
        record = NutritionAdjustmentProposalRepository.save_proposal(db, owner_user_id, proposal)
        proposal.proposal_id = record.id
        return proposal

    @staticmethod
    def get_proposal(
        db: Session,
        proposal_id: str,
        owner_user_id: str,
    ) -> Optional[Dict[str, Any]]:
        record = NutritionAdjustmentProposalRepository.get_proposal_by_id(db, proposal_id, owner_user_id)
        if not record:
            return None
        return NutritionAdjustmentProposalService._record_to_dict(record)

    @staticmethod
    def list_proposals(
        db: Session,
        owner_user_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        records = NutritionAdjustmentProposalRepository.list_proposals(db, owner_user_id, limit)
        return [NutritionAdjustmentProposalService._record_to_dict(r) for r in records]

    @staticmethod
    def accept_proposal(
        db: Session,
        proposal_id: str,
        owner_user_id: str,
    ) -> Dict[str, Any]:
        record = NutritionAdjustmentProposalRepository.get_proposal_by_id(db, proposal_id, owner_user_id)
        if not record:
            raise ValueError("Proposal not found.")

        if record.lifecycle_state != ProposalLifecycleState.PENDING.value:
            raise ValueError(f"Proposal cannot be accepted from state '{record.lifecycle_state}'.")

        # Expiration check
        now_dt = datetime.now(timezone.utc)
        if record.expires_at:
            exp_dt = record.expires_at if record.expires_at.tzinfo else record.expires_at.replace(tzinfo=timezone.utc)
            if now_dt > exp_dt:
                NutritionAdjustmentProposalRepository.update_lifecycle_state(
                    db, proposal_id, owner_user_id, ProposalLifecycleState.EXPIRED
                )
                raise ValueError("Proposal has expired and cannot be accepted.")

        updated = NutritionAdjustmentProposalRepository.update_lifecycle_state(
            db, proposal_id, owner_user_id, ProposalLifecycleState.ACCEPTED
        )
        return NutritionAdjustmentProposalService._record_to_dict(updated)

    @staticmethod
    def reject_proposal(
        db: Session,
        proposal_id: str,
        owner_user_id: str,
        rejection_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        record = NutritionAdjustmentProposalRepository.get_proposal_by_id(db, proposal_id, owner_user_id)
        if not record:
            raise ValueError("Proposal not found.")

        if record.lifecycle_state != ProposalLifecycleState.PENDING.value:
            raise ValueError(f"Proposal cannot be rejected from state '{record.lifecycle_state}'.")

        updated = NutritionAdjustmentProposalRepository.update_lifecycle_state(
            db, proposal_id, owner_user_id, ProposalLifecycleState.REJECTED, rejection_reason=rejection_reason
        )
        return NutritionAdjustmentProposalService._record_to_dict(updated)

    @staticmethod
    def _record_to_dict(record) -> Dict[str, Any]:
        return {
            "proposal_id": record.id,
            "evaluation_id": record.evaluation_id,
            "status": record.status,
            "lifecycle_state": record.lifecycle_state,
            "proposal_type": record.proposal_type,
            "current_target_kcal": record.current_target_kcal,
            "proposed_target_kcal": record.proposed_target_kcal,
            "delta_kcal": record.delta_kcal,
            "confidence": record.confidence,
            "fingerprint": record.fingerprint,
            "evidence_summary": record.evidence_snapshot,
            "risk_flags": record.risk_flags,
            "reason_codes": record.reason_codes,
            "explanations": record.explanations,
            "policy_versions": record.policy_versions,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "expires_at": record.expires_at.isoformat() if record.expires_at else None,
            "resolved_at": record.resolved_at.isoformat() if record.resolved_at else None,
            "rejection_reason": record.rejection_reason,
            "requires_user_confirmation": True,
            "downstream_budget_recheck_required": True,
        }
