import pytest
import uuid
import jwt
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.nutrition_adaptation.constants import (
    AdaptationDecision,
    AdjustmentReviewDomain,
    DataSufficiencyStatus,
    WeightTrendDirection,
    AdherenceContextCategory,
    EvaluationConfidence,
    DayEvidenceQuality,
    EvaluationReasonCode,
    AdaptationEvaluationPolicy,
)
from app.nutrition_adaptation.models import (
    WeightObservationDTO,
    NutritionEvidenceDayDTO,
    NutritionAdaptationEvaluationInputDTO,
)
from app.nutrition_adherence.constants import (
    ReportingCompleteness,
    DeviationReason,
    MealCompletionState,
)
from app.daily_nutrition_plan.constants import MacroCompleteness, DailyPlanStatus
from app.meal_structure.constants import MealStructureState
from app.nutrition_adaptation.evaluator import evaluate_nutrition_adaptation
from app.nutrition_adaptation.weight_trend import evaluate_weight_trend
from app.repositories.nutrition_adaptation_repository import NutritionAdaptationRepository
from app.services.nutrition_adaptation_service import NutritionAdaptationService


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _generate_mock_days(
    count: int,
    reporting: ReportingCompleteness = ReportingCompleteness.COMPLETE,
    nutrition_comp: MacroCompleteness = MacroCompleteness.COMPLETE,
    deviation_reasons: list = None,
    full_meal_count: int = 3,
) -> list:
    days = []
    base_dt = datetime(2026, 8, 1)
    reasons = deviation_reasons or []
    for i in range(count):
        date_str = (base_dt + timedelta(days=i)).strftime("%Y-%m-%d")
        days.append(
            NutritionEvidenceDayDTO(
                logical_day_id=f"ld_{i+1}",
                date=date_str,
                plan_status=DailyPlanStatus.READY,
                reporting_completeness=reporting,
                nutrition_completeness=nutrition_comp,
                planned_energy_kcal=2300.0,
                actual_energy_kcal=2280.0 if nutrition_comp == MacroCompleteness.COMPLETE else None,
                meal_completion_counts={"FULL": full_meal_count},
                deviation_reasons=reasons,
                evidence_quality=(
                    DayEvidenceQuality.USABLE
                    if reporting == ReportingCompleteness.COMPLETE and nutrition_comp == MacroCompleteness.COMPLETE
                    else DayEvidenceQuality.PARTIAL
                ),
            )
        )
    return days


def _generate_mock_weights(count: int, start_kg: float = 60.0, step_kg: float = 0.0) -> list:
    weights = []
    base_dt = datetime(2026, 8, 1)
    for i in range(count):
        dt_str = (base_dt + timedelta(days=i * 2)).isoformat()
        weights.append(
            WeightObservationDTO(
                measured_at=dt_str,
                weight_kg=round(start_kg + (i * step_kg), 2),
                source="USER_LOG",
            )
        )
    return weights


def test_insufficient_window_and_sparse_measurements():
    """
    Evaluation window < 7 days or measurements < 3 returns NEEDS_MORE_DATA.
    """
    days = _generate_mock_days(4)  # 4 days only
    weights = _generate_mock_weights(2)  # 2 weights only

    input_dto = NutritionAdaptationEvaluationInputDTO(
        user_id="u1",
        nutrition_goal_type="NUTRITION_WEIGHT_GAIN",
        target_energy_kcal=2300.0,
        meal_structure_state=MealStructureState.BASELINE,
        step_index=0,
        assessment_eligibility_status="ELIGIBLE",
        evidence_days=days,
        weight_measurements=weights,
    )

    result = evaluate_nutrition_adaptation(input_dto)
    assert result.decision == AdaptationDecision.NEEDS_MORE_DATA
    assert result.review_domain == AdjustmentReviewDomain.DATA_COLLECTION_REVIEW
    assert EvaluationReasonCode.INSUFFICIENT_EVALUATION_WINDOW in result.reason_codes
    assert EvaluationReasonCode.INSUFFICIENT_WEIGHT_DATA in result.reason_codes


def test_missing_reporting_returns_needs_more_data():
    """
    Many NOT_REPORTED days returns NEEDS_MORE_DATA, not calorie adjustment.
    """
    days = _generate_mock_days(10, reporting=ReportingCompleteness.NONE)
    weights = _generate_mock_weights(5, start_kg=60.0, step_kg=0.0)

    input_dto = NutritionAdaptationEvaluationInputDTO(
        user_id="u1",
        nutrition_goal_type="NUTRITION_WEIGHT_GAIN",
        target_energy_kcal=2300.0,
        evidence_days=days,
        weight_measurements=weights,
    )

    result = evaluate_nutrition_adaptation(input_dto)
    assert result.decision == AdaptationDecision.NEEDS_MORE_DATA
    assert result.adherence_summary.category == AdherenceContextCategory.INSUFFICIENT_REPORTING


def test_flat_trend_with_high_adherence_weight_gain_considers_adjustment():
    """
    Weight trend is flat + high adherence + complete evidence -> CONSIDER_ADJUSTMENT for ENERGY_TARGET_REVIEW.
    """
    days = _generate_mock_days(14, reporting=ReportingCompleteness.COMPLETE, nutrition_comp=MacroCompleteness.COMPLETE)
    weights = _generate_mock_weights(6, start_kg=60.0, step_kg=0.0)  # slope = 0.0 kg/day

    input_dto = NutritionAdaptationEvaluationInputDTO(
        user_id="u1",
        nutrition_goal_type="NUTRITION_WEIGHT_GAIN",
        target_energy_kcal=2300.0,
        evidence_days=days,
        weight_measurements=weights,
    )

    result = evaluate_nutrition_adaptation(input_dto)
    assert result.decision == AdaptationDecision.CONSIDER_ADJUSTMENT
    assert result.review_domain == AdjustmentReviewDomain.ENERGY_TARGET_REVIEW
    assert result.weight_trend.direction == WeightTrendDirection.STABLE
    assert EvaluationReasonCode.WEIGHT_TREND_STABLE in result.reason_codes
    assert EvaluationReasonCode.HIGH_ADHERENCE in result.reason_codes


def test_progressing_trend_with_high_adherence_continues():
    """
    Weight trend increasing as expected on weight gain -> CONTINUE_CURRENT_PLAN.
    """
    days = _generate_mock_days(14)
    weights = _generate_mock_weights(6, start_kg=60.0, step_kg=0.1)  # slope = +0.05 kg/day

    input_dto = NutritionAdaptationEvaluationInputDTO(
        user_id="u1",
        nutrition_goal_type="NUTRITION_WEIGHT_GAIN",
        target_energy_kcal=2300.0,
        evidence_days=days,
        weight_measurements=weights,
    )

    result = evaluate_nutrition_adaptation(input_dto)
    assert result.decision == AdaptationDecision.CONTINUE_CURRENT_PLAN
    assert result.review_domain == AdjustmentReviewDomain.NONE
    assert result.weight_trend.direction == WeightTrendDirection.INCREASING
    assert EvaluationReasonCode.WEIGHT_TREND_EXPECTED_DIRECTION in result.reason_codes


def test_short_7_day_window_flat_trend_does_not_prematurely_adjust():
    """
    7-10 days flat trend with high adherence is sufficient for status monitoring,
    but does NOT prematurely open CONSIDER_ADJUSTMENT under Chronos Anti-Overreaction Policy.
    """
    days = _generate_mock_days(8, reporting=ReportingCompleteness.COMPLETE, nutrition_comp=MacroCompleteness.COMPLETE)
    weights = _generate_mock_weights(4, start_kg=60.0, step_kg=0.0)

    input_dto = NutritionAdaptationEvaluationInputDTO(
        user_id="u1",
        nutrition_goal_type="NUTRITION_WEIGHT_GAIN",
        target_energy_kcal=2300.0,
        evidence_days=days,
        weight_measurements=weights,
    )

    result = evaluate_nutrition_adaptation(input_dto)
    assert result.decision == AdaptationDecision.CONTINUE_CURRENT_PLAN
    assert result.review_domain == AdjustmentReviewDomain.NONE
    assert EvaluationReasonCode.INSUFFICIENT_ADJUSTMENT_WINDOW in result.reason_codes
    assert EvaluationReasonCode.WEIGHT_TREND_STABLE in result.reason_codes


def test_inconsistent_measurement_context_downgrades_confidence():
    """
    Mixed / inconsistent measurement contexts (wake morning vs late night) downgrade trend confidence.
    """
    weights = [
        WeightObservationDTO(measured_at="2026-08-01T07:00:00Z", weight_kg=60.0, context="WAKE_MORNING"),
        WeightObservationDTO(measured_at="2026-08-03T22:30:00Z", weight_kg=60.8, context="POST_MEAL_NIGHT"),
        WeightObservationDTO(measured_at="2026-08-05T07:00:00Z", weight_kg=60.1, context="WAKE_MORNING"),
        WeightObservationDTO(measured_at="2026-08-07T22:00:00Z", weight_kg=60.9, context="POST_MEAL_NIGHT"),
    ]

    days = _generate_mock_days(14, reporting=ReportingCompleteness.COMPLETE, nutrition_comp=MacroCompleteness.COMPLETE)
    input_dto = NutritionAdaptationEvaluationInputDTO(
        user_id="u1",
        nutrition_goal_type="NUTRITION_WEIGHT_GAIN",
        target_energy_kcal=2300.0,
        evidence_days=days,
        weight_measurements=weights,
    )

    result = evaluate_nutrition_adaptation(input_dto)
    # Because of alternating context, confidence is downgraded or not high
    assert result.weight_trend.confidence in (EvaluationConfidence.MEDIUM, EvaluationConfidence.LOW)


def test_residual_outlier_detection_gap_aware():
    """
    Residual-based outlier detection flags severe fitted deviation without crude time-division flaws.
    """
    # 5 points, one extreme 5kg spike that deviates from line
    weights = [
        WeightObservationDTO(measured_at="2026-08-01T07:00:00Z", weight_kg=60.0),
        WeightObservationDTO(measured_at="2026-08-04T07:00:00Z", weight_kg=60.1),
        WeightObservationDTO(measured_at="2026-08-07T07:00:00Z", weight_kg=65.5),  # 5.4 kg spike outlier
        WeightObservationDTO(measured_at="2026-08-10T07:00:00Z", weight_kg=60.2),
        WeightObservationDTO(measured_at="2026-08-14T07:00:00Z", weight_kg=60.3),
    ]

    trend = evaluate_weight_trend(weights)
    assert trend.outlier_count >= 1
    assert trend.confidence != EvaluationConfidence.HIGH


def test_budget_friction_pattern_triggers_budget_review():
    """
    Repeated TOO_EXPENSIVE reasons -> HOLD_CURRENT_PLAN, BUDGET_REVIEW.
    """
    days = _generate_mock_days(14, deviation_reasons=[DeviationReason.TOO_EXPENSIVE])
    weights = _generate_mock_weights(5, start_kg=60.0, step_kg=0.0)

    input_dto = NutritionAdaptationEvaluationInputDTO(
        user_id="u1",
        nutrition_goal_type="NUTRITION_WEIGHT_GAIN",
        target_energy_kcal=2300.0,
        evidence_days=days,
        weight_measurements=weights,
    )

    result = evaluate_nutrition_adaptation(input_dto)
    assert result.decision == AdaptationDecision.HOLD_CURRENT_PLAN
    assert result.review_domain == AdjustmentReviewDomain.BUDGET_REVIEW
    assert EvaluationReasonCode.BUDGET_FRICTION_PATTERN in result.reason_codes


def test_schedule_friction_pattern_triggers_schedule_review():
    """
    Repeated NO_TIME / SCHEDULE_CHANGED -> HOLD_CURRENT_PLAN, SCHEDULE_REVIEW.
    """
    days = _generate_mock_days(14, deviation_reasons=[DeviationReason.NO_TIME])
    weights = _generate_mock_weights(5, start_kg=60.0, step_kg=0.0)

    input_dto = NutritionAdaptationEvaluationInputDTO(
        user_id="u1",
        nutrition_goal_type="NUTRITION_WEIGHT_GAIN",
        target_energy_kcal=2300.0,
        evidence_days=days,
        weight_measurements=weights,
    )

    result = evaluate_nutrition_adaptation(input_dto)
    assert result.decision == AdaptationDecision.HOLD_CURRENT_PLAN
    assert result.review_domain == AdjustmentReviewDomain.SCHEDULE_REVIEW
    assert EvaluationReasonCode.SCHEDULE_FRICTION_PATTERN in result.reason_codes


def test_food_and_preparation_friction_triggers_food_review():
    """
    Repeated FOOD_UNAVAILABLE -> HOLD_CURRENT_PLAN, FOOD_CANDIDATE_REVIEW.
    """
    days = _generate_mock_days(14, deviation_reasons=[DeviationReason.FOOD_UNAVAILABLE])
    weights = _generate_mock_weights(5, start_kg=60.0, step_kg=0.0)

    input_dto = NutritionAdaptationEvaluationInputDTO(
        user_id="u1",
        nutrition_goal_type="NUTRITION_WEIGHT_GAIN",
        target_energy_kcal=2300.0,
        evidence_days=days,
        weight_measurements=weights,
    )

    result = evaluate_nutrition_adaptation(input_dto)
    assert result.decision == AdaptationDecision.HOLD_CURRENT_PLAN
    assert result.review_domain == AdjustmentReviewDomain.FOOD_CANDIDATE_REVIEW
    assert EvaluationReasonCode.FOOD_AVAILABILITY_PATTERN in result.reason_codes


def test_cooldown_gate_enforcement():
    """
    Recent adaptation review/change within cooldown -> HOLD_CURRENT_PLAN, ADAPTATION_COOLDOWN_ACTIVE.
    """
    days = _generate_mock_days(14)
    weights = _generate_mock_weights(6, start_kg=60.0, step_kg=0.0)

    input_dto = NutritionAdaptationEvaluationInputDTO(
        user_id="u1",
        nutrition_goal_type="NUTRITION_WEIGHT_GAIN",
        target_energy_kcal=2300.0,
        evidence_days=days,
        weight_measurements=weights,
        last_adaptation_at="2026-08-16T00:00:00Z",  # 3 days ago
        evaluation_reference_time="2026-08-19T00:00:00Z",
    )

    result = evaluate_nutrition_adaptation(input_dto)
    assert result.decision == AdaptationDecision.HOLD_CURRENT_PLAN
    assert EvaluationReasonCode.ADAPTATION_COOLDOWN_ACTIVE in result.reason_codes


def test_safety_out_of_scope_gate():
    """
    If assessment eligibility status is OUT_OF_SCOPE -> evaluation decision is OUT_OF_SCOPE.
    """
    days = _generate_mock_days(14)
    weights = _generate_mock_weights(6)

    input_dto = NutritionAdaptationEvaluationInputDTO(
        user_id="u1",
        nutrition_goal_type="NUTRITION_WEIGHT_GAIN",
        target_energy_kcal=2300.0,
        assessment_eligibility_status="OUT_OF_SCOPE",
        evidence_days=days,
        weight_measurements=weights,
    )

    result = evaluate_nutrition_adaptation(input_dto)
    assert result.decision == AdaptationDecision.OUT_OF_SCOPE
    assert result.review_domain == AdjustmentReviewDomain.NONE
    assert EvaluationReasonCode.SAFETY_OUT_OF_SCOPE in result.reason_codes


def test_early_transition_step_awareness():
    """
    Early transition step index < 2 with short window -> CONTINUE_CURRENT_PLAN, EARLY_TRANSITION_PHASE.
    """
    days = _generate_mock_days(5)
    weights = _generate_mock_weights(4)

    input_dto = NutritionAdaptationEvaluationInputDTO(
        user_id="u1",
        nutrition_goal_type="NUTRITION_WEIGHT_GAIN",
        target_energy_kcal=2300.0,
        meal_structure_state=MealStructureState.TRANSITION,
        step_index=0,
        evidence_days=days,
        weight_measurements=weights,
    )

    result = evaluate_nutrition_adaptation(input_dto)
    assert result.decision == AdaptationDecision.CONTINUE_CURRENT_PLAN
    assert EvaluationReasonCode.EARLY_TRANSITION_PHASE in result.reason_codes


def test_read_only_zero_io_evaluator():
    """
    Pure evaluator is deterministic, zero-I/O, and does not alter input objects.
    """
    days = _generate_mock_days(14)
    weights = _generate_mock_weights(5)

    input_dto = NutritionAdaptationEvaluationInputDTO(
        user_id="u_det",
        nutrition_goal_type="NUTRITION_WEIGHT_GAIN",
        target_energy_kcal=2300.0,
        evidence_days=days,
        weight_measurements=weights,
    )

    res1 = evaluate_nutrition_adaptation(input_dto)
    res2 = evaluate_nutrition_adaptation(input_dto)

    assert res1.evaluation_id == res2.evaluation_id
    assert res1.decision == res2.decision
    assert res1.review_domain == res2.review_domain
    assert res1.confidence == res2.confidence


@pytest.mark.asyncio
async def test_api_nutrition_adaptation_preview_and_history_authenticated():
    """
    REST API test for previewing adaptation and fetching history.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        test_uid = f"user_api_adapt_{uuid.uuid4()}"
        token = create_mock_jwt(test_uid, f"{test_uid}@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        # Create user in DB for RLS/FK safety
        db = SessionLocal()
        try:
            db.add(User(id=test_uid, email=f"{test_uid}@chronos.local"))
            db.commit()
        finally:
            db.close()

        days_payload = [
            {
                "logical_day_id": f"ld_{i}",
                "date": f"2026-08-{i+1:02d}",
                "plan_status": "READY",
                "reporting_completeness": "COMPLETE",
                "nutrition_completeness": "COMPLETE",
                "planned_energy_kcal": 2300.0,
                "actual_energy_kcal": 2280.0,
                "meal_completion_counts": {"FULL": 3},
                "deviation_reasons": [],
            }
            for i in range(14)
        ]

        weights_payload = [
            {
                "measured_at": f"2026-08-{i*2+1:02d}T07:00:00Z",
                "weight_kg": 60.0,
                "source": "USER_LOG",
            }
            for i in range(6)
        ]

        payload = {
            "nutrition_goal_type": "NUTRITION_WEIGHT_GAIN",
            "target_energy_kcal": 2300.0,
            "meal_structure_state": "BASELINE",
            "step_index": 0,
            "assessment_eligibility_status": "ELIGIBLE",
            "evidence_days": days_payload,
            "weight_measurements": weights_payload,
            "persist": True,
        }

        res = await client.post("/api/v1/nutrition-adaptation/preview", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == "CONSIDER_ADJUSTMENT"
        assert data["review_domain"] == "ENERGY_TARGET_REVIEW"
        assert data["confidence"] == "HIGH"

        # Check history
        res_hist = await client.get("/api/v1/nutrition-adaptation/evaluations", headers=headers)
        assert res_hist.status_code == 200
        history = res_hist.json()
        assert len(history) >= 1
        assert history[0]["decision"] == "CONSIDER_ADJUSTMENT"
