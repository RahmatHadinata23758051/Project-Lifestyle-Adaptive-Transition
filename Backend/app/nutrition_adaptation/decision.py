from datetime import datetime, timezone
from typing import Tuple, List, Optional
from app.nutrition_adaptation.constants import (
    AdaptationDecision,
    AdjustmentReviewDomain,
    EvaluationReasonCode,
    WeightTrendDirection,
    AdherenceContextCategory,
    AdaptationEvaluationPolicy,
)
from app.nutrition_adaptation.models import (
    DataSufficiencyDTO,
    AdherencePatternSummaryDTO,
    WeightTrendSummaryDTO,
    ReasonPatternSummaryDTO,
    EvidenceWindowDTO,
)
from app.meal_structure.constants import MealStructureState
from app.nutrition_adherence.constants import DeviationReason


def evaluate_adaptation_decision(
    goal_type: str,
    eligibility_status: str,
    meal_structure_state: MealStructureState,
    step_index: int,
    window: EvidenceWindowDTO,
    sufficiency: DataSufficiencyDTO,
    adherence: AdherencePatternSummaryDTO,
    trend: WeightTrendSummaryDTO,
    reason_patterns: ReasonPatternSummaryDTO,
    last_adaptation_at: Optional[str] = None,
    current_time_str: Optional[str] = None,
) -> Tuple[AdaptationDecision, AdjustmentReviewDomain, List[EvaluationReasonCode]]:
    """
    Evaluates pure adaptation decision without modifying user state or plan targets.
    """
    reason_codes: List[EvaluationReasonCode] = []

    # 1. Safety Gate
    norm_elig = str(eligibility_status).upper().strip()
    if any(k in norm_elig for k in ("OUT_OF_SCOPE", "NOT_ELIGIBLE", "BLOCKED")):
        reason_codes.append(EvaluationReasonCode.SAFETY_OUT_OF_SCOPE)
        return AdaptationDecision.OUT_OF_SCOPE, AdjustmentReviewDomain.NONE, reason_codes

    # 2. Unsupported Goal Gate (P1.7 v0.1 supports NUTRITION_WEIGHT_GAIN)
    if "WEIGHT_GAIN" not in goal_type.upper():
        reason_codes.append(EvaluationReasonCode.SAFETY_OUT_OF_SCOPE)
        return AdaptationDecision.OUT_OF_SCOPE, AdjustmentReviewDomain.NONE, reason_codes

    # 3. Cooldown Gate
    if last_adaptation_at:
        try:
            last_dt = datetime.fromisoformat(last_adaptation_at)
            now_dt = datetime.fromisoformat(current_time_str) if current_time_str else datetime.now(timezone.utc)
            days_since = (now_dt - last_dt).total_seconds() / 86400.0
            if days_since < AdaptationEvaluationPolicy.MIN_DAYS_BETWEEN_ADAPTATION_REVIEWS:
                reason_codes.append(EvaluationReasonCode.ADAPTATION_COOLDOWN_ACTIVE)
                return AdaptationDecision.HOLD_CURRENT_PLAN, AdjustmentReviewDomain.NONE, reason_codes
        except Exception:
            pass

    # 4. Early Transition Check
    if meal_structure_state == MealStructureState.TRANSITION and step_index < 2 and window.usable_adherence_days < AdaptationEvaluationPolicy.PREFERRED_EVALUATION_DAYS:
        reason_codes.append(EvaluationReasonCode.EARLY_TRANSITION_PHASE)
        return AdaptationDecision.CONTINUE_CURRENT_PLAN, AdjustmentReviewDomain.NONE, reason_codes

    # 5. Data Sufficiency Gate
    if not sufficiency.is_sufficient:
        if window.total_days < AdaptationEvaluationPolicy.MIN_EVALUATION_DAYS:
            reason_codes.append(EvaluationReasonCode.INSUFFICIENT_EVALUATION_WINDOW)
        if adherence.category == AdherenceContextCategory.INSUFFICIENT_REPORTING:
            reason_codes.append(EvaluationReasonCode.INSUFFICIENT_REPORTING)
        if window.weight_measurement_count < AdaptationEvaluationPolicy.MIN_WEIGHT_MEASUREMENTS:
            reason_codes.append(EvaluationReasonCode.INSUFFICIENT_WEIGHT_DATA)
        return AdaptationDecision.NEEDS_MORE_DATA, AdjustmentReviewDomain.DATA_COLLECTION_REVIEW, reason_codes

    # 6. Reason Pattern Review Domains (Budget, Schedule, Food Availability Friction)
    dominant = reason_patterns.dominant_reasons
    if DeviationReason.TOO_EXPENSIVE in dominant:
        reason_codes.append(EvaluationReasonCode.BUDGET_FRICTION_PATTERN)
        return AdaptationDecision.HOLD_CURRENT_PLAN, AdjustmentReviewDomain.BUDGET_REVIEW, reason_codes

    if any(r in dominant for r in (DeviationReason.NO_TIME, DeviationReason.SCHEDULE_CHANGED)):
        reason_codes.append(EvaluationReasonCode.SCHEDULE_FRICTION_PATTERN)
        return AdaptationDecision.HOLD_CURRENT_PLAN, AdjustmentReviewDomain.SCHEDULE_REVIEW, reason_codes

    if DeviationReason.FOOD_UNAVAILABLE in dominant:
        reason_codes.append(EvaluationReasonCode.FOOD_AVAILABILITY_PATTERN)
        return AdaptationDecision.HOLD_CURRENT_PLAN, AdjustmentReviewDomain.FOOD_CANDIDATE_REVIEW, reason_codes

    if DeviationReason.PREPARATION_DIFFICULT in dominant:
        reason_codes.append(EvaluationReasonCode.PREPARATION_FRICTION_PATTERN)
        return AdaptationDecision.HOLD_CURRENT_PLAN, AdjustmentReviewDomain.FOOD_CANDIDATE_REVIEW, reason_codes

    # 7. Adherence Context Evaluation
    if adherence.category == AdherenceContextCategory.HIGH_CONFIDENCE_ADHERENCE:
        reason_codes.append(EvaluationReasonCode.HIGH_ADHERENCE)
    elif adherence.category == AdherenceContextCategory.LOW_ADHERENCE:
        reason_codes.append(EvaluationReasonCode.LOW_ADHERENCE)
        return AdaptationDecision.HOLD_CURRENT_PLAN, AdjustmentReviewDomain.NONE, reason_codes
    else:
        reason_codes.append(EvaluationReasonCode.MIXED_ADHERENCE)

    # 8. Weight Trend Evaluation
    if not trend.is_interpretable:
        reason_codes.append(EvaluationReasonCode.WEIGHT_TREND_INDETERMINATE)
        return AdaptationDecision.NEEDS_MORE_DATA, AdjustmentReviewDomain.DATA_COLLECTION_REVIEW, reason_codes

    # Check whether observation satisfies the Chronos Anti-Overreaction Policy for adjusting targets
    is_adjustment_window_adequate = (
        window.total_days >= AdaptationEvaluationPolicy.MIN_ADJUSTMENT_EVALUATION_DAYS
        and window.usable_adherence_days >= AdaptationEvaluationPolicy.MIN_ADJUSTMENT_USABLE_DAYS
        and window.weight_measurement_count >= AdaptationEvaluationPolicy.MIN_ADJUSTMENT_WEIGHT_MEASUREMENTS
    )

    if trend.direction == WeightTrendDirection.STABLE:
        reason_codes.append(EvaluationReasonCode.WEIGHT_TREND_STABLE)
        if adherence.category == AdherenceContextCategory.HIGH_CONFIDENCE_ADHERENCE:
            if is_adjustment_window_adequate:
                # Adequate multi-week evidence + high adherence + flat weight -> open ENERGY_TARGET_REVIEW
                return AdaptationDecision.CONSIDER_ADJUSTMENT, AdjustmentReviewDomain.ENERGY_TARGET_REVIEW, reason_codes
            else:
                # 7-13 days monitoring is sufficient for status evaluation but too short for target adaptation
                reason_codes.append(EvaluationReasonCode.INSUFFICIENT_ADJUSTMENT_WINDOW)
                return AdaptationDecision.CONTINUE_CURRENT_PLAN, AdjustmentReviewDomain.NONE, reason_codes
        else:
            return AdaptationDecision.HOLD_CURRENT_PLAN, AdjustmentReviewDomain.NONE, reason_codes

    elif trend.direction == WeightTrendDirection.INCREASING:
        reason_codes.append(EvaluationReasonCode.WEIGHT_TREND_EXPECTED_DIRECTION)
        return AdaptationDecision.CONTINUE_CURRENT_PLAN, AdjustmentReviewDomain.NONE, reason_codes

    elif trend.direction == WeightTrendDirection.DECREASING:
        reason_codes.append(EvaluationReasonCode.WEIGHT_TREND_OPPOSITE_DIRECTION)
        if adherence.category == AdherenceContextCategory.HIGH_CONFIDENCE_ADHERENCE:
            if is_adjustment_window_adequate:
                return AdaptationDecision.CONSIDER_ADJUSTMENT, AdjustmentReviewDomain.ENERGY_TARGET_REVIEW, reason_codes
            else:
                reason_codes.append(EvaluationReasonCode.INSUFFICIENT_ADJUSTMENT_WINDOW)
                return AdaptationDecision.CONTINUE_CURRENT_PLAN, AdjustmentReviewDomain.NONE, reason_codes
        else:
            return AdaptationDecision.HOLD_CURRENT_PLAN, AdjustmentReviewDomain.NONE, reason_codes

    return AdaptationDecision.CONTINUE_CURRENT_PLAN, AdjustmentReviewDomain.NONE, reason_codes
