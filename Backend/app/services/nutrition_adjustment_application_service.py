from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.nutrition_adjustment_application.models import (
    ApplyNutritionAdjustmentCommand,
    NutritionAdjustmentApplicationResultDTO,
    DownstreamInvalidationDTO,
)
from app.nutrition_adjustment_application.constants import (
    ApplicationStatus,
    ApplicationReasonCode,
    ApplicationPolicy,
)
from app.nutrition_adjustment_application.validation import (
    validate_application_prerequisites,
)
from app.nutrition_adjustment_application.idempotency import (
    evaluate_idempotent_replay,
)
from app.nutrition_adjustment_application.state_transition import (
    build_applied_state_transition,
)
from app.nutrition_adjustment_proposal.models import (
    NutritionAdjustmentProposalDTO,
    EvidenceSnapshotDTO,
)
from app.models.nutrition_adjustment_proposal import NutritionAdjustmentProposalRecord
from app.models.nutrition_adjustment_application import NutritionAdjustmentApplicationRecord
from app.models.nutrition_state_revision import NutritionStateRevisionRecord
from app.repositories.nutrition_adjustment_application_repository import (
    NutritionAdjustmentApplicationRepository,
)
from app.repositories.nutrition_adjustment_proposal_repository import (
    NutritionAdjustmentProposalRepository,
)


class NutritionAdjustmentApplicationService:
    @staticmethod
    def apply_adjustment(
        db: Session,
        owner_user_id: str,
        command: ApplyNutritionAdjustmentCommand,
        current_eligibility_status: str = "ELIGIBLE",
        last_evidence_updated_at: Optional[str] = None,
    ) -> NutritionAdjustmentApplicationResultDTO:
        # 1. Load authoritative proposal
        prop_record = NutritionAdjustmentProposalRepository.get_proposal_by_id(
            db, command.proposal_id, owner_user_id
        )
        if not prop_record:
            raise ValueError(f"Proposal '{command.proposal_id}' not found for user.")

        # 2. Check Idempotency via existing application records
        existing_app_by_prop = NutritionAdjustmentApplicationRepository.get_application_by_proposal_id(
            db, command.proposal_id
        )
        existing_app_by_key = NutritionAdjustmentApplicationRepository.get_application_by_idempotency_key(
            db, owner_user_id, command.idempotency_key
        )

        app_dto_by_prop = (
            NutritionAdjustmentApplicationService._record_to_result_dto(existing_app_by_prop)
            if existing_app_by_prop
            else None
        )
        app_dto_by_key = (
            NutritionAdjustmentApplicationService._record_to_result_dto(existing_app_by_key)
            if existing_app_by_key
            else None
        )

        idemp_status, idemp_result, idemp_reason = evaluate_idempotent_replay(
            command, app_dto_by_prop, app_dto_by_key
        )
        if idemp_status == ApplicationStatus.IDEMPOTENCY_CONFLICT:
            raise ValueError(f"Idempotency conflict: key '{command.idempotency_key}' was previously used for another proposal.")
        if idemp_status == ApplicationStatus.ALREADY_APPLIED and idemp_result is not None:
            return idemp_result

        # Convert record to Proposal DTO for pure validation
        proposal_dto = NutritionAdjustmentApplicationService._record_to_proposal_dto(prop_record)

        # 3. Determine current authoritative state revision and target
        latest_rev = NutritionAdjustmentApplicationRepository.get_latest_state_revision(db, owner_user_id)
        if latest_rev:
            current_revision_number = int(latest_rev.revision_number)
            current_revision_id = latest_rev.id
            current_target_kcal = int(latest_rev.target_energy_kcal)
        else:
            # Baseline state before any adjustment: revision 1 with proposal current target
            current_revision_number = 1
            current_revision_id = None
            current_target_kcal = int(proposal_dto.current_target_kcal)

        # 4. Calculate cumulative adaptive adjustment applied so far
        applied_sum = (
            db.query(func.coalesce(func.sum(NutritionAdjustmentApplicationRecord.delta_kcal), 0))
            .filter(
                NutritionAdjustmentApplicationRecord.owner_user_id == owner_user_id,
                NutritionAdjustmentApplicationRecord.application_status == ApplicationStatus.APPLIED.value,
            )
            .scalar()
        )
        current_cumulative_delta = int(applied_sum or 0)

        # 5. Run Pure Prerequisite Validation
        val_status, val_reasons, val_exps = validate_application_prerequisites(
            command=command,
            command_user_id=owner_user_id,
            proposal=proposal_dto,
            proposal_owner_user_id=prop_record.owner_user_id,
            current_authoritative_target_kcal=current_target_kcal,
            current_authoritative_revision=current_revision_number,
            current_cumulative_adaptive_delta_kcal=current_cumulative_delta,
            current_eligibility_status=current_eligibility_status,
            last_evidence_updated_at=last_evidence_updated_at,
            reference_time_str=command.reference_time,
        )
        if val_status is not None:
            err_msg = val_exps[0] if val_exps else f"Validation failed with status {val_status.value}"
            raise ValueError(f"[{val_status.value}] {err_msg}")

        # 6. Build Pure State Transition
        new_rev_dto, app_result_dto = build_applied_state_transition(
            command=command,
            proposal=proposal_dto,
            owner_user_id=owner_user_id,
            previous_revision_number=current_revision_number,
            previous_revision_id=current_revision_id,
            reference_time_str=command.reference_time,
        )

        # 7. Execute Atomic Repository Transaction
        app_record = NutritionAdjustmentApplicationRepository.execute_atomic_application(
            db=db,
            owner_user_id=owner_user_id,
            proposal_id=command.proposal_id,
            idempotency_key=command.idempotency_key,
            new_revision_dto=new_rev_dto,
            application_dto=app_result_dto,
        )

        return NutritionAdjustmentApplicationService._record_to_result_dto(app_record)

    @staticmethod
    def get_application(
        db: Session,
        application_id: str,
        owner_user_id: str,
    ) -> Optional[NutritionAdjustmentApplicationResultDTO]:
        record = NutritionAdjustmentApplicationRepository.get_application_by_id(
            db, application_id, owner_user_id
        )
        if not record:
            return None
        return NutritionAdjustmentApplicationService._record_to_result_dto(record)

    @staticmethod
    def list_state_revisions(
        db: Session,
        owner_user_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        records = NutritionAdjustmentApplicationRepository.list_state_revisions(
            db, owner_user_id, limit
        )
        return [
            {
                "id": r.id,
                "owner_user_id": r.owner_user_id,
                "revision_number": int(r.revision_number),
                "previous_revision_id": r.previous_revision_id,
                "source_type": r.source_type,
                "source_reference_id": r.source_reference_id,
                "target_energy_kcal": int(r.target_energy_kcal),
                "goal_type": r.goal_type,
                "effective_from": r.effective_from.isoformat() if r.effective_from else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]

    @staticmethod
    def _record_to_result_dto(
        record: NutritionAdjustmentApplicationRecord,
    ) -> NutritionAdjustmentApplicationResultDTO:
        inval_dict = record.downstream_invalidation or {}
        inval_dto = DownstreamInvalidationDTO(
            source_revision=inval_dict.get("source_revision", record.previous_state_revision),
            target_revision=inval_dict.get("target_revision", record.new_state_revision),
            meal_structure_invalidated=inval_dict.get("meal_structure_invalidated", True),
            food_candidates_invalidated=inval_dict.get("food_candidates_invalidated", True),
            budget_selection_invalidated=inval_dict.get("budget_selection_invalidated", True),
            daily_plan_invalidated=inval_dict.get("daily_plan_invalidated", True),
            requires_downstream_regeneration=inval_dict.get("requires_downstream_regeneration", True),
            reason=inval_dict.get("reason", "Energy target mutated; downstream plan artifacts require regeneration."),
        )

        return NutritionAdjustmentApplicationResultDTO(
            application_id=record.id,
            proposal_id=record.proposal_id,
            status=ApplicationStatus(record.application_status),
            previous_target_kcal=int(record.previous_target_kcal),
            applied_target_kcal=int(record.applied_target_kcal),
            delta_kcal=int(record.delta_kcal),
            previous_state_revision=int(record.previous_state_revision),
            new_state_revision=int(record.new_state_revision),
            downstream_invalidation=inval_dto,
            applied_at=record.applied_at.isoformat() if record.applied_at else "",
            audit_reference=record.idempotency_key,
            reason_codes=[ApplicationReasonCode.USER_CONFIRMED_ENERGY_INCREASE],
            explanations=[
                f"Applied +{record.delta_kcal} kcal energy target adjustment ({record.previous_target_kcal} -> {record.applied_target_kcal} kcal/day).",
            ],
            policy_versions=record.policy_versions or {},
        )

    @staticmethod
    def _record_to_proposal_dto(
        record: NutritionAdjustmentProposalRecord,
    ) -> NutritionAdjustmentProposalDTO:
        evid_data = record.evidence_snapshot or {}
        evidence_snapshot = EvidenceSnapshotDTO(
            evaluation_id=evid_data.get("evaluation_id", record.evaluation_id),
            decision=evid_data.get("decision", "CONSIDER_ADJUSTMENT"),
            review_domain=evid_data.get("review_domain", "ENERGY_TARGET_REVIEW"),
            evaluation_confidence=evid_data.get("evaluation_confidence", "HIGH"),
            weight_trend_direction=evid_data.get("weight_trend_direction", "STABLE"),
            weight_trend_confidence=evid_data.get("weight_trend_confidence", "HIGH"),
            slope_kg_per_day=evid_data.get("slope_kg_per_day"),
            usable_days=evid_data.get("usable_days", 14),
            weight_measurements_count=evid_data.get("weight_measurements_count", 4),
            adherence_category=evid_data.get("adherence_category", "HIGH_CONFIDENCE_ADHERENCE"),
            reason_codes=evid_data.get("reason_codes", []),
        )

        created_str = ""
        if record.created_at:
            dt = record.created_at if record.created_at.tzinfo else record.created_at.replace(tzinfo=timezone.utc)
            created_str = dt.isoformat()
        expires_str = ""
        if record.expires_at:
            dt = record.expires_at if record.expires_at.tzinfo else record.expires_at.replace(tzinfo=timezone.utc)
            expires_str = dt.isoformat()

        return NutritionAdjustmentProposalDTO(
            proposal_id=record.id,
            proposal_domain=getattr(record, "proposal_domain", "ENERGY_TARGET"),
            status=record.status,
            lifecycle_state=record.lifecycle_state,
            proposal_type=record.proposal_type,
            current_target_kcal=int(record.current_target_kcal),
            proposed_target_kcal=int(record.proposed_target_kcal),
            delta_kcal=int(record.delta_kcal),
            confidence=record.confidence,
            evidence_summary=evidence_snapshot,
            risk_flags=record.risk_flags or [],
            reason_codes=record.reason_codes or [],
            explanations=record.explanations or [],
            fingerprint=record.fingerprint,
            created_at=created_str,
            expires_at=expires_str,
            resolved_at=record.resolved_at.isoformat() if record.resolved_at else None,
            rejection_reason=record.rejection_reason,
            requires_user_confirmation=True,
            downstream_budget_recheck_required=True,
            policy_versions=record.policy_versions or {},
        )
