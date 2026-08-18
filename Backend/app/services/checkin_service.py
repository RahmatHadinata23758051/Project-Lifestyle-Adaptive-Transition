from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.roadmap import Roadmap, DailyPlanRecord, PlanItemRecord, DailyEvaluationRecord
from app.schemas.roadmap import PlanItemStatus, EvaluationResult, AdaptationAction, PlanDomain
from app.engine.state_machine import evaluate_daily_deviation, resolve_next_adaptation_action
from app.engine.step_sizing import calculate_daily_target_times


def process_item_checkin(
    db: Session,
    item_id: str,
    actual_time_str: Optional[str] = None,
    actual_cost: Optional[float] = None,
    is_late: bool = False,
) -> Dict[str, Any]:
    """
    Process 1-tap check-in on a plan item.
    """
    item = db.query(PlanItemRecord).filter(PlanItemRecord.id == item_id).first()
    if not item:
        raise ValueError(f"Plan item '{item_id}' not found.")

    now_str = actual_time_str or datetime.now().strftime("%H:%M")
    
    if item.status in (PlanItemStatus.COMPLETED.value, PlanItemStatus.LATE_COMPLETED.value):
        # Toggle back to PLANNED
        item.status = PlanItemStatus.PLANNED.value
        item.actual_time = None
        item.actual_cost = None
    else:
        item.status = PlanItemStatus.LATE_COMPLETED.value if is_late else PlanItemStatus.COMPLETED.value
        item.actual_time = now_str
        item.actual_cost = actual_cost

    db.commit()
    db.refresh(item)

    return {
        "item_id": item.id,
        "status": item.status,
        "actual_time": item.actual_time,
        "actual_cost": item.actual_cost,
    }


def evaluate_daily_plan_completion(
    db: Session,
    daily_plan_id: str,
    did_open_app: bool = True,
) -> Dict[str, Any]:
    """
    Run end-of-day evaluation for a daily plan and apply adaptation action to the roadmap.
    """
    daily_plan = db.query(DailyPlanRecord).filter(DailyPlanRecord.id == daily_plan_id).first()
    if not daily_plan:
        raise ValueError(f"Daily plan '{daily_plan_id}' not found.")

    roadmap = db.query(Roadmap).filter(Roadmap.id == daily_plan.roadmap_id).first()
    if not roadmap:
        raise ValueError(f"Roadmap '{daily_plan.roadmap_id}' not found.")

    # Find the critical wake item check-in
    wake_item = next((i for i in daily_plan.items if i.domain == PlanDomain.WAKE.value), None)
    actual_wake_time = wake_item.actual_time if (wake_item and wake_item.status in (PlanItemStatus.COMPLETED.value, PlanItemStatus.LATE_COMPLETED.value)) else None

    # 1. Run deviation evaluation
    eval_dict = evaluate_daily_deviation(
        target_time_str=daily_plan.target_wake_time,
        actual_time_str=actual_wake_time,
        did_open_app=did_open_app,
    )

    # 2. Fetch recent evaluation history for this roadmap
    past_eval_records = (
        db.query(DailyEvaluationRecord)
        .join(DailyPlanRecord)
        .filter(DailyPlanRecord.roadmap_id == roadmap.id, DailyPlanRecord.day_number < daily_plan.day_number)
        .order_by(DailyPlanRecord.day_number.asc())
        .all()
    )
    history: List[EvaluationResult] = [EvaluationResult(r.evaluation_result) for r in past_eval_records]

    # 3. Resolve next action
    action = resolve_next_adaptation_action(
        current_result=eval_dict["result"],
        recent_history=history,
    )

    # 4. Save or update evaluation record
    eval_record = db.query(DailyEvaluationRecord).filter(DailyEvaluationRecord.daily_plan_id == daily_plan.id).first()
    now_iso = datetime.now(timezone.utc).isoformat()
    if not eval_record:
        eval_record = DailyEvaluationRecord(
            daily_plan_id=daily_plan.id,
            evaluation_result=eval_dict["result"].value,
            adaptation_action=action.value,
            deviation_minutes=eval_dict["deviation_minutes"],
            raw_delta_minutes=eval_dict["raw_delta_minutes"],
            reason=eval_dict["reason"],
            evaluated_at=now_iso,
        )
        db.add(eval_record)
    else:
        eval_record.evaluation_result = eval_dict["result"].value
        eval_record.adaptation_action = action.value
        eval_record.deviation_minutes = eval_dict["deviation_minutes"]
        eval_record.raw_delta_minutes = eval_dict["raw_delta_minutes"]
        eval_record.reason = eval_dict["reason"]
        eval_record.evaluated_at = now_iso

    # 5. Update roadmap state and progress step index
    if action == AdaptationAction.ADVANCE_STEP:
        roadmap.current_step_index += 1
    elif action == AdaptationAction.REDUCE_STEP_SIZE:
        roadmap.current_step_size_minutes = max(5, roadmap.current_step_size_minutes - 5)
    # HOLD_TARGET and MAINTAIN_STEP keep current_step_index untouched

    if daily_plan.day_number < roadmap.total_days:
        roadmap.current_day = daily_plan.day_number + 1

    daily_plan.state = "EVALUATED"
    db.commit()

    return {
        "daily_plan_id": daily_plan.id,
        "evaluation_result": eval_dict["result"].value,
        "adaptation_action": action.value,
        "deviation_minutes": eval_dict["deviation_minutes"],
        "reason": eval_dict["reason"],
        "updated_roadmap_day": roadmap.current_day,
        "updated_step_index": roadmap.current_step_index,
    }
