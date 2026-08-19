from datetime import datetime, timezone, timedelta
from typing import Optional, List
import uuid

from app.nutrition_adjustment_proposal.constants import (
    ProposalStatus,
    ProposalLifecycleState,
    ProposalType,
    AdjustmentProposalReasonCode,
    RiskFlag,
    ProposalPolicy,
)
from app.nutrition_adjustment_proposal.models import (
    EvidenceSnapshotDTO,
    NutritionAdjustmentProposalInputDTO,
    NutritionAdjustmentProposalDTO,
)
from app.nutrition_adjustment_proposal.eligibility import (
    evaluate_proposal_eligibility_and_decision_gate,
)
from app.nutrition_adjustment_proposal.confidence import (
    evaluate_proposal_confidence_gate,
)
from app.nutrition_adjustment_proposal.freshness import (
    evaluate_freshness_and_cooldown_gate,
)
from app.nutrition_adjustment_proposal.bounds import (
    calculate_bounded_energy_adjustment,
)
from app.nutrition_adjustment_proposal.fingerprint import (
    generate_proposal_fingerprint,
)
from app.nutrition_adjustment_proposal.explanations import (
    generate_proposal_explanations,
)


def build_nutrition_adjustment_proposal(
    input_dto: NutritionAdjustmentProposalInputDTO,
) -> NutritionAdjustmentProposalDTO:
    """
    Pure zero-I/O Nutrition Adjustment Proposal Builder (NUTRITION_ADJUSTMENT_PROPOSAL_V01).
    Evaluates evidence, confidence, freshness, and bounds to propose a reversible energy target change.
    Does NOT mutate user state or authoritative targets.
    """
    eval_res = input_dto.evaluation

    # Build immutable evidence snapshot
    evidence_snapshot = EvidenceSnapshotDTO(
        evaluation_id=eval_res.evaluation_id,
        decision=eval_res.decision,
        review_domain=eval_res.review_domain,
        evaluation_confidence=eval_res.confidence,
        weight_trend_direction=eval_res.weight_trend.direction,
        weight_trend_confidence=eval_res.weight_trend.confidence,
        slope_kg_per_day=eval_res.weight_trend.slope_kg_per_day,
        usable_days=eval_res.evidence_window.usable_adherence_days,
        weight_measurements_count=eval_res.evidence_window.weight_measurement_count,
        adherence_category=eval_res.adherence_summary.category,
        reason_codes=eval_res.reason_codes,
    )

    ref_dt = (
        datetime.fromisoformat(input_dto.reference_time)
        if input_dto.reference_time
        else datetime.now(timezone.utc)
    )
    created_at_str = ref_dt.isoformat()
    expires_at_str = (ref_dt + timedelta(hours=ProposalPolicy.PROPOSAL_VALIDITY_HOURS)).isoformat()

    # 1. Eligibility & Upstream Decision Gate
    elig_status, elig_reasons = evaluate_proposal_eligibility_and_decision_gate(
        evaluation=eval_res,
        current_eligibility_status=input_dto.current_eligibility_status,
        goal_type=input_dto.nutrition_goal_type,
    )
    if elig_status is not None:
        fp = generate_proposal_fingerprint(
            eval_res.evaluation_id,
            input_dto.current_target_energy_kcal,
            input_dto.current_target_energy_kcal,
            0.0,
        )
        exps = generate_proposal_explanations(
            elig_status,
            input_dto.current_target_energy_kcal,
            input_dto.current_target_energy_kcal,
            0.0,
            elig_reasons,
        )
        return NutritionAdjustmentProposalDTO(
            proposal_id=f"prop_{uuid.uuid4().hex[:16]}",
            status=elig_status,
            lifecycle_state=ProposalLifecycleState.PENDING,
            proposal_type=ProposalType.HOLD_CURRENT_TARGET,
            current_target_kcal=round(input_dto.current_target_energy_kcal, 1),
            proposed_target_kcal=round(input_dto.current_target_energy_kcal, 1),
            delta_kcal=0.0,
            confidence=eval_res.confidence,
            evidence_summary=evidence_snapshot,
            risk_flags=[],
            reason_codes=elig_reasons,
            explanations=exps,
            fingerprint=fp,
            created_at=created_at_str,
            expires_at=expires_at_str,
        )

    # 2. Confidence Gate (NUTRITION_ADJUSTMENT_CONFIDENCE_V01)
    conf_status, conf_reasons, conf_risks = evaluate_proposal_confidence_gate(eval_res)
    if conf_status is not None:
        fp = generate_proposal_fingerprint(
            eval_res.evaluation_id,
            input_dto.current_target_energy_kcal,
            input_dto.current_target_energy_kcal,
            0.0,
        )
        exps = generate_proposal_explanations(
            conf_status,
            input_dto.current_target_energy_kcal,
            input_dto.current_target_energy_kcal,
            0.0,
            conf_reasons,
        )
        return NutritionAdjustmentProposalDTO(
            proposal_id=f"prop_{uuid.uuid4().hex[:16]}",
            status=conf_status,
            lifecycle_state=ProposalLifecycleState.PENDING,
            proposal_type=ProposalType.HOLD_CURRENT_TARGET,
            current_target_kcal=round(input_dto.current_target_energy_kcal, 1),
            proposed_target_kcal=round(input_dto.current_target_energy_kcal, 1),
            delta_kcal=0.0,
            confidence=eval_res.confidence,
            evidence_summary=evidence_snapshot,
            risk_flags=conf_risks,
            reason_codes=conf_reasons,
            explanations=exps,
            fingerprint=fp,
            created_at=created_at_str,
            expires_at=expires_at_str,
        )

    # 3. Freshness and Cooldown Gate (NUTRITION_EVALUATION_FRESHNESS_V01)
    fresh_status, fresh_reasons, fresh_risks = evaluate_freshness_and_cooldown_gate(
        evaluated_at_str=eval_res.evaluated_at,
        last_applied_adjustment_at=input_dto.last_applied_adjustment_at,
        last_evidence_updated_at=input_dto.last_evidence_updated_at,
        reference_time_str=input_dto.reference_time,
    )
    if fresh_status is not None:
        fp = generate_proposal_fingerprint(
            eval_res.evaluation_id,
            input_dto.current_target_energy_kcal,
            input_dto.current_target_energy_kcal,
            0.0,
        )
        exps = generate_proposal_explanations(
            fresh_status,
            input_dto.current_target_energy_kcal,
            input_dto.current_target_energy_kcal,
            0.0,
            fresh_reasons,
        )
        return NutritionAdjustmentProposalDTO(
            proposal_id=f"prop_{uuid.uuid4().hex[:16]}",
            status=fresh_status,
            lifecycle_state=ProposalLifecycleState.PENDING,
            proposal_type=ProposalType.HOLD_CURRENT_TARGET,
            current_target_kcal=round(input_dto.current_target_energy_kcal, 1),
            proposed_target_kcal=round(input_dto.current_target_energy_kcal, 1),
            delta_kcal=0.0,
            confidence=eval_res.confidence,
            evidence_summary=evidence_snapshot,
            risk_flags=fresh_risks,
            reason_codes=fresh_reasons,
            explanations=exps,
            fingerprint=fp,
            created_at=created_at_str,
            expires_at=expires_at_str,
        )

    # 4. Bounded Energy Adjustment & Cumulative Ceiling (NUTRITION_ENERGY_ADJUSTMENT_V01)
    adj_status, delta, proposed_target, adj_reasons, adj_risks = calculate_bounded_energy_adjustment(
        current_target_kcal=input_dto.current_target_energy_kcal,
        cumulative_adaptive_adjustment_kcal=input_dto.cumulative_adaptive_adjustment_kcal,
    )

    prop_type = (
        ProposalType.ENERGY_TARGET_INCREASE
        if adj_status == ProposalStatus.PROPOSAL_READY
        else ProposalType.HOLD_CURRENT_TARGET
    )

    fp = generate_proposal_fingerprint(
        eval_res.evaluation_id,
        input_dto.current_target_energy_kcal,
        proposed_target,
        delta,
    )
    exps = generate_proposal_explanations(
        adj_status,
        input_dto.current_target_energy_kcal,
        proposed_target,
        delta,
        adj_reasons,
    )

    return NutritionAdjustmentProposalDTO(
        proposal_id=f"prop_{uuid.uuid4().hex[:16]}",
        status=adj_status,
        lifecycle_state=ProposalLifecycleState.PENDING,
        proposal_type=prop_type,
        current_target_kcal=round(input_dto.current_target_energy_kcal, 1),
        proposed_target_kcal=round(proposed_target, 1),
        delta_kcal=round(delta, 1),
        confidence=eval_res.confidence,
        evidence_summary=evidence_snapshot,
        risk_flags=adj_risks,
        reason_codes=adj_reasons,
        explanations=exps,
        fingerprint=fp,
        created_at=created_at_str,
        expires_at=expires_at_str,
    )
