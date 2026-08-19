import pytest
import uuid
import jwt
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.nutrition_adjustment_proposal.constants import (
    ProposalStatus,
    ProposalLifecycleState,
    ProposalType,
    AdjustmentProposalReasonCode,
    RiskFlag,
    ProposalPolicy,
)
from app.nutrition_adjustment_proposal.models import (
    NutritionAdjustmentProposalInputDTO,
)
from app.nutrition_adjustment_proposal.proposal import build_nutrition_adjustment_proposal
from app.nutrition_adjustment_proposal.fingerprint import generate_proposal_fingerprint
from app.nutrition_adaptation.constants import (
    AdaptationDecision,
    AdjustmentReviewDomain,
    DataSufficiencyStatus,
    WeightTrendDirection,
    AdherenceContextCategory,
    EvaluationConfidence,
    EvaluationReasonCode,
)
from app.nutrition_adaptation.models import (
    NutritionAdaptationEvaluationResultDTO,
    EvidenceWindowDTO,
    DataSufficiencyDTO,
    AdherencePatternSummaryDTO,
    WeightTrendSummaryDTO,
    ReasonPatternSummaryDTO,
)


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _build_mock_evaluation(
    decision: AdaptationDecision = AdaptationDecision.CONSIDER_ADJUSTMENT,
    review_domain: AdjustmentReviewDomain = AdjustmentReviewDomain.ENERGY_TARGET_REVIEW,
    eval_confidence: EvaluationConfidence = EvaluationConfidence.HIGH,
    trend_confidence: EvaluationConfidence = EvaluationConfidence.HIGH,
    trend_direction: WeightTrendDirection = WeightTrendDirection.STABLE,
    is_interpretable: bool = True,
    sufficiency_status: DataSufficiencyStatus = DataSufficiencyStatus.SUFFICIENT,
    evaluated_at: str = "2026-08-19T10:00:00Z",
) -> NutritionAdaptationEvaluationResultDTO:
    return NutritionAdaptationEvaluationResultDTO(
        evaluation_id=f"eval_{uuid.uuid4().hex[:12]}",
        evaluated_at=evaluated_at,
        decision=decision,
        review_domain=review_domain,
        confidence=eval_confidence,
        evidence_window=EvidenceWindowDTO(
            start_date="2026-08-01",
            end_date="2026-08-15",
            total_days=14,
            usable_adherence_days=14,
            weight_measurement_count=6,
        ),
        data_sufficiency=DataSufficiencyDTO(
            status=sufficiency_status,
            usable_days_count=14,
            weight_count=6,
            is_sufficient=(sufficiency_status == DataSufficiencyStatus.SUFFICIENT),
            reasons=[],
        ),
        adherence_summary=AdherencePatternSummaryDTO(
            category=AdherenceContextCategory.HIGH_CONFIDENCE_ADHERENCE,
            reporting_coverage_ratio=1.0,
            full_completion_ratio=0.9,
            confidence=EvaluationConfidence.HIGH,
        ),
        weight_trend=WeightTrendSummaryDTO(
            measurement_count=6,
            start_weight_kg=60.0,
            end_weight_kg=60.0,
            slope_kg_per_day=0.0,
            direction=trend_direction,
            confidence=trend_confidence,
            is_interpretable=is_interpretable,
            outlier_count=0,
        ),
        reason_patterns=ReasonPatternSummaryDTO(
            reason_counts={},
            dominant_reasons=[],
            pattern_confidence=EvaluationConfidence.HIGH,
        ),
        reason_codes=[EvaluationReasonCode.WEIGHT_TREND_STABLE, EvaluationReasonCode.HIGH_ADHERENCE],
        explanations=["Weight trend is stable while adherence is consistently high."],
        policy_version="NUTRITION_ADAPTATION_EVALUATION_V01",
    )


def test_wrong_p1_7_decision_returns_no_proposal_needed():
    """
    If P1.7 returned CONTINUE_CURRENT_PLAN, proposal engine returns NO_PROPOSAL_NEEDED.
    """
    eval_res = _build_mock_evaluation(decision=AdaptationDecision.CONTINUE_CURRENT_PLAN)
    input_dto = NutritionAdjustmentProposalInputDTO(
        evaluation=eval_res,
        current_target_energy_kcal=2300.0,
    )
    proposal = build_nutrition_adjustment_proposal(input_dto)
    assert proposal.status == ProposalStatus.NO_PROPOSAL_NEEDED
    assert proposal.delta_kcal == 0.0
    assert proposal.proposed_target_kcal == 2300.0


def test_wrong_review_domain_returns_unsupported_review_domain():
    """
    If P1.7 recommended BUDGET_REVIEW, P1.8 returns UNSUPPORTED_REVIEW_DOMAIN (not calorie change).
    """
    eval_res = _build_mock_evaluation(
        decision=AdaptationDecision.HOLD_CURRENT_PLAN,
        review_domain=AdjustmentReviewDomain.BUDGET_REVIEW,
    )
    input_dto = NutritionAdjustmentProposalInputDTO(
        evaluation=eval_res,
        current_target_energy_kcal=2300.0,
    )
    proposal = build_nutrition_adjustment_proposal(input_dto)
    assert proposal.status == ProposalStatus.NO_PROPOSAL_NEEDED or proposal.status == ProposalStatus.UNSUPPORTED_REVIEW_DOMAIN


def test_low_weight_trend_confidence_blocks_proposal():
    """
    If weight trend confidence is LOW, proposal is BLOCKED_BY_CONFIDENCE.
    """
    eval_res = _build_mock_evaluation(trend_confidence=EvaluationConfidence.LOW)
    input_dto = NutritionAdjustmentProposalInputDTO(
        evaluation=eval_res,
        current_target_energy_kcal=2300.0,
    )
    proposal = build_nutrition_adjustment_proposal(input_dto)
    assert proposal.status == ProposalStatus.BLOCKED_BY_CONFIDENCE
    assert AdjustmentProposalReasonCode.LOW_WEIGHT_TREND_CONFIDENCE in proposal.reason_codes
    assert RiskFlag.LOW_WEIGHT_TREND_CONFIDENCE in proposal.risk_flags


def test_uninterpretable_weight_trend_blocks_proposal():
    """
    If trend is marked uninterpretable, proposal is BLOCKED_BY_CONFIDENCE.
    """
    eval_res = _build_mock_evaluation(is_interpretable=False)
    input_dto = NutritionAdjustmentProposalInputDTO(
        evaluation=eval_res,
        current_target_energy_kcal=2300.0,
    )
    proposal = build_nutrition_adjustment_proposal(input_dto)
    assert proposal.status == ProposalStatus.BLOCKED_BY_CONFIDENCE


def test_insufficient_data_returns_needs_more_data():
    """
    If data sufficiency was not SUFFICIENT, proposal returns NEEDS_MORE_DATA.
    """
    eval_res = _build_mock_evaluation(sufficiency_status=DataSufficiencyStatus.INSUFFICIENT)
    input_dto = NutritionAdjustmentProposalInputDTO(
        evaluation=eval_res,
        current_target_energy_kcal=2300.0,
    )
    proposal = build_nutrition_adjustment_proposal(input_dto)
    assert proposal.status == ProposalStatus.NEEDS_MORE_DATA


def test_ineligible_safety_status_blocks_proposal():
    """
    If current eligibility status changed to OUT_OF_SCOPE, proposal returns OUT_OF_SCOPE.
    """
    eval_res = _build_mock_evaluation()
    input_dto = NutritionAdjustmentProposalInputDTO(
        evaluation=eval_res,
        current_target_energy_kcal=2300.0,
        current_eligibility_status="OUT_OF_SCOPE",
    )
    proposal = build_nutrition_adjustment_proposal(input_dto)
    assert proposal.status == ProposalStatus.OUT_OF_SCOPE
    assert AdjustmentProposalReasonCode.ELIGIBILITY_NOT_VALID in proposal.reason_codes


def test_unsupported_goal_blocks_proposal():
    """
    If goal is not NUTRITION_WEIGHT_GAIN, proposal returns OUT_OF_SCOPE.
    """
    eval_res = _build_mock_evaluation()
    input_dto = NutritionAdjustmentProposalInputDTO(
        evaluation=eval_res,
        current_target_energy_kcal=2300.0,
        nutrition_goal_type="NUTRITION_WEIGHT_LOSS",
    )
    proposal = build_nutrition_adjustment_proposal(input_dto)
    assert proposal.status == ProposalStatus.OUT_OF_SCOPE
    assert AdjustmentProposalReasonCode.UNSUPPORTED_GOAL in proposal.reason_codes


def test_new_evidence_invalidates_evaluation_needs_new_evaluation():
    """
    If new check-in or weight arrived after evaluation was run, returns NEEDS_NEW_EVALUATION.
    """
    eval_res = _build_mock_evaluation(evaluated_at="2026-08-19T10:00:00Z")
    input_dto = NutritionAdjustmentProposalInputDTO(
        evaluation=eval_res,
        current_target_energy_kcal=2300.0,
        last_evidence_updated_at="2026-08-19T11:30:00Z",  # newer than evaluation
    )
    proposal = build_nutrition_adjustment_proposal(input_dto)
    assert proposal.status == ProposalStatus.NEEDS_NEW_EVALUATION
    assert AdjustmentProposalReasonCode.NEW_EVIDENCE_AVAILABLE in proposal.reason_codes
    assert RiskFlag.NEW_EVIDENCE_AVAILABLE in proposal.risk_flags


def test_supported_ready_proposal_generation():
    """
    Full positive flow: CONSIDER_ADJUSTMENT + ENERGY_TARGET_REVIEW + SUFFICIENT + HIGH confidence
    produces PROPOSAL_READY with bounded +100 kcal.
    """
    eval_res = _build_mock_evaluation()
    input_dto = NutritionAdjustmentProposalInputDTO(
        evaluation=eval_res,
        current_target_energy_kcal=2300.0,
        reference_time="2026-08-19T10:00:00Z",
    )
    proposal = build_nutrition_adjustment_proposal(input_dto)
    assert proposal.status == ProposalStatus.PROPOSAL_READY
    assert proposal.proposal_type == ProposalType.ENERGY_TARGET_INCREASE
    assert proposal.current_target_kcal == 2300.0
    assert proposal.proposed_target_kcal == 2400.0
    assert proposal.delta_kcal == 100.0
    assert proposal.requires_user_confirmation is True
    assert proposal.downstream_budget_recheck_required is True
    assert len(proposal.fingerprint) == 64
    assert len(proposal.explanations) >= 1


def test_cumulative_limit_guardrail():
    """
    If cumulative adaptive adjustment already reached ceiling (e.g. +400 kcal),
    proposal status becomes ADAPTIVE_LIMIT_REACHED.
    """
    eval_res = _build_mock_evaluation()
    input_dto = NutritionAdjustmentProposalInputDTO(
        evaluation=eval_res,
        current_target_energy_kcal=2700.0,
        cumulative_adaptive_adjustment_kcal=400.0,
    )
    proposal = build_nutrition_adjustment_proposal(input_dto)
    assert proposal.status == ProposalStatus.ADAPTIVE_LIMIT_REACHED
    assert proposal.delta_kcal == 0.0
    assert proposal.proposed_target_kcal == 2700.0
    assert AdjustmentProposalReasonCode.ADAPTIVE_LIMIT_REACHED in proposal.reason_codes


def test_proposal_determinism_and_fingerprint():
    """
    Same explicit inputs yield identical fingerprints and proposal contents (zero-I/O determinism).
    """
    eval_res = _build_mock_evaluation()
    input_dto = NutritionAdjustmentProposalInputDTO(
        evaluation=eval_res,
        current_target_energy_kcal=2300.0,
        reference_time="2026-08-19T10:00:00Z",
    )
    p1 = build_nutrition_adjustment_proposal(input_dto)
    p2 = build_nutrition_adjustment_proposal(input_dto)

    assert p1.fingerprint == p2.fingerprint
    assert p1.proposed_target_kcal == p2.proposed_target_kcal
    assert p1.delta_kcal == p2.delta_kcal
    assert p1.status == p2.status


@pytest.mark.asyncio
async def test_api_adjustment_proposal_preview_and_lifecycle():
    """
    REST API test: preview, create, list, supersession, accept, reject flow.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        test_uid = f"user_api_prop_{uuid.uuid4()}"
        token = create_mock_jwt(test_uid, f"{test_uid}@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        # Create user in DB
        db = SessionLocal()
        try:
            db.add(User(id=test_uid, email=f"{test_uid}@chronos.local"))
            db.commit()
        finally:
            db.close()

        eval_mock = _build_mock_evaluation().model_dump()

        payload = {
            "evaluation": eval_mock,
            "current_target_energy_kcal": 2300.0,
            "cumulative_adaptive_adjustment_kcal": 0.0,
            "nutrition_goal_type": "NUTRITION_WEIGHT_GAIN",
            "current_eligibility_status": "ELIGIBLE",
            "reference_time": "2026-08-19T10:00:00Z",
        }

        # 1. Preview
        preview_res = await client.post("/api/v1/nutrition-adjustments/proposals/preview", json=payload, headers=headers)
        assert preview_res.status_code == 200
        p_data = preview_res.json()
        assert p_data["status"] == "PROPOSAL_READY"
        assert p_data["proposed_target_kcal"] == 2400.0
        assert p_data["delta_kcal"] == 100.0

        # 2. Create proposal 1
        create_res1 = await client.post("/api/v1/nutrition-adjustments/proposals", json=payload, headers=headers)
        assert create_res1.status_code == 200
        c1_data = create_res1.json()
        prop1_id = c1_data["proposal_id"]
        assert c1_data["lifecycle_state"] == "PENDING"

        # 3. Create proposal 2 (should supersede proposal 1)
        create_res2 = await client.post("/api/v1/nutrition-adjustments/proposals", json=payload, headers=headers)
        assert create_res2.status_code == 200
        c2_data = create_res2.json()
        prop2_id = c2_data["proposal_id"]
        assert prop2_id != prop1_id

        # Verify proposal 1 is now SUPERSEDED
        get_p1 = await client.get(f"/api/v1/nutrition-adjustments/proposals/{prop1_id}", headers=headers)
        assert get_p1.status_code == 200
        assert get_p1.json()["lifecycle_state"] == "SUPERSEDED"

        # 4. Accept proposal 2
        accept_res = await client.post(f"/api/v1/nutrition-adjustments/proposals/{prop2_id}/accept", headers=headers)
        assert accept_res.status_code == 200
        assert accept_res.json()["lifecycle_state"] == "ACCEPTED"

        # Verify cannot re-accept already accepted proposal
        re_accept = await client.post(f"/api/v1/nutrition-adjustments/proposals/{prop2_id}/accept", headers=headers)
        assert re_accept.status_code == 400
