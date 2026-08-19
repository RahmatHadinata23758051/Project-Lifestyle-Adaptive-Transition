from typing import List
from app.nutrition_adaptation.constants import (
    AdaptationDecision,
    AdjustmentReviewDomain,
    EvaluationReasonCode,
)


def generate_adaptation_explanations(
    decision: AdaptationDecision,
    review_domain: AdjustmentReviewDomain,
    reason_codes: List[EvaluationReasonCode],
) -> List[str]:
    """
    Generates deterministic, non-judgmental factual explanations of the adaptation evaluation.
    """
    explanations: List[str] = []

    if EvaluationReasonCode.SAFETY_OUT_OF_SCOPE in reason_codes:
        explanations.append("User is outside supported nutrition scope. Adaptation evaluation suspended.")

    if EvaluationReasonCode.INSUFFICIENT_EVALUATION_WINDOW in reason_codes:
        explanations.append("Observation window is shorter than the required minimum for evaluation.")

    if EvaluationReasonCode.INSUFFICIENT_REPORTING in reason_codes:
        explanations.append("Recent check-in reporting coverage is not yet sufficient for a reliable adjustment review.")

    if EvaluationReasonCode.INSUFFICIENT_WEIGHT_DATA in reason_codes:
        explanations.append("Weight measurements are too sparse to interpret a reliable trend.")

    if EvaluationReasonCode.WEIGHT_TREND_STABLE in reason_codes:
        if EvaluationReasonCode.HIGH_ADHERENCE in reason_codes:
            explanations.append("Weight trend is stable while reported plan adherence is consistently high.")
        else:
            explanations.append("Weight trend is stable, but adherence has been mixed or incomplete.")

    if EvaluationReasonCode.WEIGHT_TREND_EXPECTED_DIRECTION in reason_codes:
        explanations.append("Weight trend is progressing in the expected direction under the current plan.")

    if EvaluationReasonCode.BUDGET_FRICTION_PATTERN in reason_codes:
        explanations.append("Multiple recent deviations were linked to food cost friction rather than calorie target mismatch.")

    if EvaluationReasonCode.SCHEDULE_FRICTION_PATTERN in reason_codes:
        explanations.append("Multiple recent deviations were linked to schedule and timing constraints.")

    if EvaluationReasonCode.FOOD_AVAILABILITY_PATTERN in reason_codes:
        explanations.append("Multiple recent deviations were linked to food unavailability.")

    if EvaluationReasonCode.ADAPTATION_COOLDOWN_ACTIVE in reason_codes:
        explanations.append("Adaptation review cooldown is active to prevent rapid target oscillation.")

    if EvaluationReasonCode.INSUFFICIENT_ADJUSTMENT_WINDOW in reason_codes:
        explanations.append("Observation period is sufficient for plan monitoring, but multi-week evidence (>= 14 days) is required before altering calorie targets.")

    if EvaluationReasonCode.INCONSISTENT_MEASUREMENT_CONTEXT in reason_codes:
        explanations.append("Weight measurement conditions (e.g., morning wake vs post-meal) were inconsistent, reducing trend confidence.")

    if not explanations:
        explanations.append("Current plan is usable and supported by available evidence.")

    return explanations
