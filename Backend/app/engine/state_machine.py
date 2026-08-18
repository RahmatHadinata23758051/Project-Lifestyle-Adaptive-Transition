from typing import Optional, List, Dict, Any
from app.core.config import settings
from app.schemas.roadmap import EvaluationResult, AdaptationAction
from app.engine.time_utils import signed_time_delta


def evaluate_daily_deviation(
    target_time_str: str,
    actual_time_str: Optional[str] = None,
    did_open_app: bool = True,
) -> Dict[str, Any]:
    """
    Evaluate daily deviation between target and actual check-in time.
    NO DATA != FAILURE: Missing check-in produces NO_DATA with deviation = None.
    """
    if not did_open_app or actual_time_str is None:
        return {
            "result": EvaluationResult.NO_DATA,
            "deviation_minutes": None,
            "raw_delta_minutes": None,
            "reason": "Tidak ada data check-in untuk dievaluasi hari ini.",
        }

    raw_delta = signed_time_delta(actual_time_str, target_time_str)
    abs_delta = abs(raw_delta)

    if abs_delta <= settings.TOLERANCE_SUCCESS_MINUTES:
        result = EvaluationResult.SUCCESS
        reason = f"Target tercapai (selisih {abs_delta} menit)."
    elif abs_delta <= settings.TOLERANCE_ACCEPTABLE_MINUTES:
        result = EvaluationResult.WITHIN_TOLERANCE
        reason = f"Dalam batas toleransi wajar (selisih {abs_delta} menit)."
    elif abs_delta <= settings.TOLERANCE_MISSED_MINUTES:
        result = EvaluationResult.MISSED
        reason = f"Target meleset {abs_delta} menit."
    else:
        result = EvaluationResult.SIGNIFICANT_MISS
        reason = f"Pergeseran signifikan ({abs_delta} menit)."

    return {
        "result": result,
        "deviation_minutes": abs_delta,
        "raw_delta_minutes": raw_delta,
        "reason": reason,
    }


def resolve_next_adaptation_action(
    current_result: EvaluationResult,
    recent_history: Optional[List[EvaluationResult]] = None,
) -> AdaptationAction:
    """
    Resolve the next action for the adaptive roadmap based on current state and recent history.
    NO_DATA -> MAINTAIN_STEP (does not advance, does not regress, does not trigger recovery).
    """
    history = recent_history or []

    if current_result == EvaluationResult.NO_DATA:
        return AdaptationAction.MAINTAIN_STEP

    if current_result == EvaluationResult.SUCCESS:
        return AdaptationAction.ADVANCE_STEP

    if current_result == EvaluationResult.WITHIN_TOLERANCE:
        return AdaptationAction.MAINTAIN_STEP

    if current_result == EvaluationResult.MISSED:
        # Check if the immediately preceding evaluation was also a miss
        if history and history[-1] in (EvaluationResult.MISSED, EvaluationResult.SIGNIFICANT_MISS):
            return AdaptationAction.REDUCE_STEP_SIZE
        return AdaptationAction.HOLD_TARGET

    if current_result == EvaluationResult.SIGNIFICANT_MISS:
        return AdaptationAction.ENTER_RECOVERY

    return AdaptationAction.HOLD_TARGET
