import hashlib
from datetime import datetime, timezone
from app.nutrition_adaptation.constants import (
    AdaptationEvaluationPolicy,
)
from app.nutrition_adaptation.models import (
    NutritionAdaptationEvaluationInputDTO,
    NutritionAdaptationEvaluationResultDTO,
)
from app.nutrition_adaptation.evidence import build_evidence_window
from app.nutrition_adaptation.sufficiency import evaluate_data_sufficiency
from app.nutrition_adaptation.weight_trend import evaluate_weight_trend
from app.nutrition_adaptation.adherence_context import evaluate_adherence_context
from app.nutrition_adaptation.reason_patterns import evaluate_reason_patterns
from app.nutrition_adaptation.confidence import derive_overall_evaluation_confidence
from app.nutrition_adaptation.decision import evaluate_adaptation_decision
from app.nutrition_adaptation.explanations import generate_adaptation_explanations


def evaluate_nutrition_adaptation(
    input_dto: NutritionAdaptationEvaluationInputDTO,
) -> NutritionAdaptationEvaluationResultDTO:
    """
    Pure zero-I/O Nutrition Adaptation Evaluator (NUTRITION_ADAPTATION_EVALUATION_V01).
    Evaluates evidence completeness, weight trend, adherence context, and deviation reasons
    to decide if an adjustment should be considered, without mutating user state.
    """
    window = build_evidence_window(input_dto.evidence_days, input_dto.weight_measurements)
    sufficiency = evaluate_data_sufficiency(window)
    trend = evaluate_weight_trend(input_dto.weight_measurements)
    adherence = evaluate_adherence_context(input_dto.evidence_days)
    reason_patterns = evaluate_reason_patterns(input_dto.evidence_days)

    confidence = derive_overall_evaluation_confidence(sufficiency, adherence, trend)

    decision, review_domain, reason_codes = evaluate_adaptation_decision(
        goal_type=input_dto.nutrition_goal_type,
        eligibility_status=input_dto.assessment_eligibility_status,
        meal_structure_state=input_dto.meal_structure_state,
        step_index=input_dto.step_index,
        window=window,
        sufficiency=sufficiency,
        adherence=adherence,
        trend=trend,
        reason_patterns=reason_patterns,
        last_adaptation_at=input_dto.last_adaptation_at,
        current_time_str=input_dto.evaluation_reference_time,
    )

    explanations = generate_adaptation_explanations(decision, review_domain, reason_codes)

    now_iso = input_dto.evaluation_reference_time or datetime.now(timezone.utc).isoformat()
    raw_sig = f"{input_dto.user_id}:{window.start_date}:{window.end_date}:{decision}:{review_domain}:{AdaptationEvaluationPolicy.VERSION}"
    eval_id = f"eval_{hashlib.sha256(raw_sig.encode('utf-8')).hexdigest()[:16]}"

    return NutritionAdaptationEvaluationResultDTO(
        evaluation_id=eval_id,
        evaluated_at=now_iso,
        decision=decision,
        review_domain=review_domain,
        confidence=confidence,
        evidence_window=window,
        data_sufficiency=sufficiency,
        adherence_summary=adherence,
        weight_trend=trend,
        reason_patterns=reason_patterns,
        reason_codes=reason_codes,
        explanations=explanations,
        policy_version=AdaptationEvaluationPolicy.VERSION,
    )
