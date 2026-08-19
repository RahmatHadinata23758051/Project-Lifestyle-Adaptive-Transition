from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.schemas.nutrition_adjustment_proposal import (
    NutritionAdjustmentProposalRequest,
    AcceptProposalRequest,
    RejectProposalRequest,
    NutritionAdjustmentProposalResponse,
)
from app.nutrition_adjustment_proposal.models import (
    NutritionAdjustmentProposalInputDTO,
)
from app.nutrition_adaptation.models import (
    NutritionAdaptationEvaluationResultDTO,
    EvidenceWindowDTO,
    DataSufficiencyDTO,
    AdherencePatternSummaryDTO,
    WeightTrendSummaryDTO,
    ReasonPatternSummaryDTO,
)
from app.services.nutrition_adjustment_proposal_service import (
    NutritionAdjustmentProposalService,
)

router = APIRouter()


def _request_to_input_dto(
    request: NutritionAdjustmentProposalRequest, owner_user_id: str
) -> NutritionAdjustmentProposalInputDTO:
    eval_resp = request.evaluation

    eval_dto = NutritionAdaptationEvaluationResultDTO(
        evaluation_id=eval_resp.evaluation_id,
        evaluated_at=eval_resp.evaluated_at,
        decision=eval_resp.decision,
        review_domain=eval_resp.review_domain,
        confidence=eval_resp.confidence,
        evidence_window=EvidenceWindowDTO(
            start_date=eval_resp.evidence_window.start_date,
            end_date=eval_resp.evidence_window.end_date,
            total_days=eval_resp.evidence_window.total_days,
            usable_adherence_days=eval_resp.evidence_window.usable_adherence_days,
            weight_measurement_count=eval_resp.evidence_window.weight_measurement_count,
        ),
        data_sufficiency=DataSufficiencyDTO(
            status=eval_resp.data_sufficiency.status,
            usable_days_count=eval_resp.data_sufficiency.usable_days_count,
            weight_count=eval_resp.data_sufficiency.weight_count,
            is_sufficient=eval_resp.data_sufficiency.is_sufficient,
            reasons=eval_resp.data_sufficiency.reasons,
        ),
        adherence_summary=AdherencePatternSummaryDTO(
            category=eval_resp.adherence_summary.category,
            reporting_coverage_ratio=eval_resp.adherence_summary.reporting_coverage_ratio,
            full_completion_ratio=eval_resp.adherence_summary.full_completion_ratio,
            confidence=eval_resp.adherence_summary.confidence,
        ),
        weight_trend=WeightTrendSummaryDTO(
            measurement_count=eval_resp.weight_trend.measurement_count,
            start_weight_kg=eval_resp.weight_trend.start_weight_kg,
            end_weight_kg=eval_resp.weight_trend.end_weight_kg,
            slope_kg_per_day=eval_resp.weight_trend.slope_kg_per_day,
            direction=eval_resp.weight_trend.direction,
            confidence=eval_resp.weight_trend.confidence,
            is_interpretable=eval_resp.weight_trend.is_interpretable,
            outlier_count=eval_resp.weight_trend.outlier_count,
        ),
        reason_patterns=ReasonPatternSummaryDTO(
            reason_counts=eval_resp.reason_patterns.reason_counts,
            dominant_reasons=eval_resp.reason_patterns.dominant_reasons,
            pattern_confidence=eval_resp.reason_patterns.pattern_confidence,
        ),
        reason_codes=eval_resp.reason_codes,
        explanations=eval_resp.explanations,
        policy_version=eval_resp.policy_version,
    )

    return NutritionAdjustmentProposalInputDTO(
        user_id=owner_user_id,
        evaluation=eval_dto,
        current_target_energy_kcal=request.current_target_energy_kcal,
        initial_baseline_target_energy_kcal=request.initial_baseline_target_energy_kcal,
        cumulative_adaptive_adjustment_kcal=request.cumulative_adaptive_adjustment_kcal,
        nutrition_goal_type=request.nutrition_goal_type,
        current_eligibility_status=request.current_eligibility_status,
        last_applied_adjustment_at=request.last_applied_adjustment_at,
        last_evidence_updated_at=request.last_evidence_updated_at,
        reference_time=request.reference_time,
    )


@router.post("/preview", response_model=NutritionAdjustmentProposalResponse)
def preview_adjustment_proposal(
    request: NutritionAdjustmentProposalRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    input_dto = _request_to_input_dto(request, current_user.id)
    proposal = NutritionAdjustmentProposalService.preview_proposal(input_dto)
    return proposal


@router.post("", response_model=NutritionAdjustmentProposalResponse)
def create_adjustment_proposal(
    request: NutritionAdjustmentProposalRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    input_dto = _request_to_input_dto(request, current_user.id)
    proposal = NutritionAdjustmentProposalService.create_proposal(db, current_user.id, input_dto)
    return proposal


@router.get("", response_model=List[NutritionAdjustmentProposalResponse])
def list_adjustment_proposals(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return NutritionAdjustmentProposalService.list_proposals(db, current_user.id, limit)


@router.get("/{proposal_id}", response_model=NutritionAdjustmentProposalResponse)
def get_adjustment_proposal(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    proposal = NutritionAdjustmentProposalService.get_proposal(db, proposal_id, current_user.id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found.")
    return proposal


@router.post("/{proposal_id}/accept", response_model=NutritionAdjustmentProposalResponse)
def accept_adjustment_proposal(
    proposal_id: str,
    request: Optional[AcceptProposalRequest] = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    current_target = request.current_target_energy_kcal if request else None
    current_elig = request.current_eligibility_status if request else None
    last_evid = request.last_evidence_updated_at if request else None
    try:
        updated = NutritionAdjustmentProposalService.accept_proposal(
            db,
            proposal_id,
            current_user.id,
            current_target_energy_kcal=current_target,
            current_eligibility_status=current_elig,
            last_evidence_updated_at=last_evid,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{proposal_id}/reject", response_model=NutritionAdjustmentProposalResponse)
def reject_adjustment_proposal(
    proposal_id: str,
    request: Optional[RejectProposalRequest] = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    reason = request.rejection_reason if request else None
    try:
        updated = NutritionAdjustmentProposalService.reject_proposal(db, proposal_id, current_user.id, reason)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
