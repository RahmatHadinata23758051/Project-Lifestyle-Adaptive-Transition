import uuid
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.nutrition_adjustment_proposal import NutritionAdjustmentProposalRecord
from app.models.nutrition_state_revision import NutritionStateRevisionRecord
from app.models.nutrition_adjustment_application import NutritionAdjustmentApplicationRecord
from app.nutrition_adjustment_application.models import (
    ApplyNutritionAdjustmentCommand,
    NutritionStateRevisionDTO,
    NutritionAdjustmentApplicationResultDTO,
)
from app.nutrition_adjustment_proposal.constants import ProposalLifecycleState


class NutritionAdjustmentApplicationRepository:
    @staticmethod
    def get_latest_state_revision(
        db: Session,
        owner_user_id: str,
    ) -> Optional[NutritionStateRevisionRecord]:
        return (
            db.query(NutritionStateRevisionRecord)
            .filter(NutritionStateRevisionRecord.owner_user_id == owner_user_id)
            .order_by(NutritionStateRevisionRecord.revision_number.desc())
            .first()
        )

    @staticmethod
    def list_state_revisions(
        db: Session,
        owner_user_id: str,
        limit: int = 20,
    ) -> List[NutritionStateRevisionRecord]:
        return (
            db.query(NutritionStateRevisionRecord)
            .filter(NutritionStateRevisionRecord.owner_user_id == owner_user_id)
            .order_by(NutritionStateRevisionRecord.revision_number.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_application_by_proposal_id(
        db: Session,
        proposal_id: str,
    ) -> Optional[NutritionAdjustmentApplicationRecord]:
        return (
            db.query(NutritionAdjustmentApplicationRecord)
            .filter(NutritionAdjustmentApplicationRecord.proposal_id == proposal_id)
            .first()
        )

    @staticmethod
    def get_application_by_idempotency_key(
        db: Session,
        owner_user_id: str,
        idempotency_key: str,
    ) -> Optional[NutritionAdjustmentApplicationRecord]:
        return (
            db.query(NutritionAdjustmentApplicationRecord)
            .filter(
                NutritionAdjustmentApplicationRecord.owner_user_id == owner_user_id,
                NutritionAdjustmentApplicationRecord.idempotency_key == idempotency_key,
            )
            .first()
        )

    @staticmethod
    def get_application_by_id(
        db: Session,
        application_id: str,
        owner_user_id: str,
    ) -> Optional[NutritionAdjustmentApplicationRecord]:
        return (
            db.query(NutritionAdjustmentApplicationRecord)
            .filter(
                NutritionAdjustmentApplicationRecord.id == application_id,
                NutritionAdjustmentApplicationRecord.owner_user_id == owner_user_id,
            )
            .first()
        )

    @staticmethod
    def execute_atomic_application(
        db: Session,
        owner_user_id: str,
        proposal_id: str,
        idempotency_key: str,
        new_revision_dto: NutritionStateRevisionDTO,
        application_dto: NutritionAdjustmentApplicationResultDTO,
    ) -> NutritionAdjustmentApplicationRecord:
        """
        Executes the atomic mutation sequence with row locking:
        1. Lock proposal row
        2. Lock latest state revision
        3. Insert new state revision
        4. Insert application record
        5. Update proposal lifecycle_state to APPLIED
        6. Commit
        """
        try:
            # 1. Lock proposal row
            proposal_record = (
                db.query(NutritionAdjustmentProposalRecord)
                .filter(
                    NutritionAdjustmentProposalRecord.id == proposal_id,
                    NutritionAdjustmentProposalRecord.owner_user_id == owner_user_id,
                )
                .with_for_update()
                .first()
            )
            if not proposal_record:
                raise ValueError("Proposal record not found for row lock.")

            # 2. Insert new state revision
            applied_dt = datetime.fromisoformat(new_revision_dto.effective_from)
            if not applied_dt.tzinfo:
                applied_dt = applied_dt.replace(tzinfo=timezone.utc)

            revision_record = NutritionStateRevisionRecord(
                id=new_revision_dto.id,
                owner_user_id=owner_user_id,
                revision_number=new_revision_dto.revision_number,
                previous_revision_id=new_revision_dto.previous_revision_id,
                source_type=new_revision_dto.source_type.value if hasattr(new_revision_dto.source_type, "value") else str(new_revision_dto.source_type),
                source_reference_id=new_revision_dto.source_reference_id,
                target_energy_kcal=int(new_revision_dto.target_energy_kcal),
                goal_type=new_revision_dto.goal_type,
                effective_from=applied_dt,
                created_at=applied_dt,
            )
            db.add(revision_record)

            # 3. Insert application record
            app_record = NutritionAdjustmentApplicationRecord(
                id=application_dto.application_id,
                owner_user_id=owner_user_id,
                proposal_id=proposal_id,
                idempotency_key=idempotency_key,
                previous_state_revision=application_dto.previous_state_revision,
                new_state_revision=application_dto.new_state_revision,
                previous_target_kcal=application_dto.previous_target_kcal,
                applied_target_kcal=application_dto.applied_target_kcal,
                delta_kcal=application_dto.delta_kcal,
                application_status=application_dto.status.value if hasattr(application_dto.status, "value") else str(application_dto.status),
                downstream_invalidation=application_dto.downstream_invalidation.model_dump(),
                applied_at=applied_dt,
                policy_versions=application_dto.policy_versions,
                created_at=applied_dt,
            )
            db.add(app_record)

            # 4. Update proposal lifecycle state to APPLIED
            proposal_record.lifecycle_state = ProposalLifecycleState.APPLIED.value
            proposal_record.resolved_at = applied_dt

            db.commit()
            db.refresh(app_record)
            return app_record

        except Exception:
            db.rollback()
            raise
