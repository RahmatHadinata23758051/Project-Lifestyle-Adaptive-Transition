import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.user import User, CurrentBaseline, TargetGoal, ConstraintRecord
from app.models.roadmap import Roadmap, DailyPlanRecord, PlanItemRecord
from app.schemas.profile import CurrentSelfBaseline, TargetSelfGoal
from app.schemas.constraints import UserConstraint, DayOfWeek
from app.schemas.roadmap import PlanDomain, PlanItemStatus, RoadmapStatus
from app.engine.feasibility import evaluate_feasibility
from app.engine.step_sizing import calculate_daily_target_times
from app.engine.collision_resolver import resolve_schedule_collisions
from app.engine.budget import calculate_daily_budget_cap


def create_user_transition_roadmap(
    db: Session,
    email: str,
    baseline_data: CurrentSelfBaseline,
    goal_data: TargetSelfGoal,
    constraints_data: List[UserConstraint],
    start_date_str: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Onboard a user and generate a persisted TransitionRoadmap with daily plans.
    Adheres strictly to:
    - Day 1 = Baseline / Stabilization Day (step_index = 0, target = baseline).
    - Separation of Measurements (Wake/Bedtime) from Micro-Quests (Hydration/Movement).
    - Unambiguous meal terminology (Meal 1, Meal 2).
    """
    # 1. Feasibility Check
    feasibility = evaluate_feasibility(
        baseline_wake=baseline_data.wake_time,
        target_wake=goal_data.target_wake_time,
        duration_days=goal_data.duration_days,
        baseline_bedtime=baseline_data.bedtime,
        target_bedtime=goal_data.target_bedtime or "23:00",
    )

    # 2. Find or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.flush()

    # 3. Create or update Baseline & Goal
    if user.baseline:
        db.delete(user.baseline)
    if user.goal:
        db.delete(user.goal)
    for c in user.constraints:
        db.delete(c)
    db.flush()

    baseline_orm = CurrentBaseline(
        user_id=user.id,
        bedtime=baseline_data.bedtime,
        wake_time=baseline_data.wake_time,
        current_weight=baseline_data.current_weight,
        meals_per_day=baseline_data.meals_per_day,
        weekly_food_budget=baseline_data.weekly_food_budget,
        cooking_access=baseline_data.cooking_access.value,
        exercise_access=baseline_data.exercise_access.value,
    )
    goal_orm = TargetGoal(
        user_id=user.id,
        target_wake_time=goal_data.target_wake_time,
        target_bedtime=goal_data.target_bedtime or "23:00",
        body_objective=goal_data.body_objective.value,
        target_weight=goal_data.target_weight,
        duration_days=goal_data.duration_days,
    )
    db.add(baseline_orm)
    db.add(goal_orm)

    # 4. Save Constraints
    for c in constraints_data:
        c_orm = ConstraintRecord(
            user_id=user.id,
            title=c.title,
            category=c.category.value,
            day_of_week=c.day_of_week.value,
            start_time=c.start_time,
            end_time=c.end_time,
            is_flexible=c.is_flexible,
        )
        db.add(c_orm)

    # 5. Generate Roadmap Entity
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else datetime.now(timezone.utc)
    target_end_dt = start_dt + timedelta(days=goal_data.duration_days)

    daily_budget = calculate_daily_budget_cap(baseline_data.weekly_food_budget, total_days=7)

    roadmap_orm = Roadmap(
        user_id=user.id,
        status=RoadmapStatus.ACTIVE.value,
        start_date=start_dt.strftime("%Y-%m-%d"),
        target_end_date=target_end_dt.strftime("%Y-%m-%d"),
        total_days=goal_data.duration_days,
        current_day=1,
        current_step_index=0,
        current_step_size_minutes=15,
    )
    db.add(roadmap_orm)
    db.flush()

    # 6. Generate Daily Plans for the Roadmap
    for day_num in range(1, goal_data.duration_days + 1):
        plan_dt = start_dt + timedelta(days=day_num - 1)
        plan_date_str = plan_dt.strftime("%Y-%m-%d")

        # P0.2: Day 1 = BASELINE / STABILIZATION DAY (target matches baseline exactly)
        if day_num == 1:
            step_idx = 0
            day_target_wake = baseline_data.wake_time
            day_target_bed = baseline_data.bedtime
            plan_state = "BASELINE"
        else:
            step_idx = (day_num - 1) // 2
            target_times = calculate_daily_target_times(
                baseline_wake_str=baseline_data.wake_time,
                target_wake_str=goal_data.target_wake_time,
                baseline_bed_str=baseline_data.bedtime,
                target_bed_str=goal_data.target_bedtime or "23:00",
                current_step_index=step_idx,
                step_size_minutes=15,
            )
            day_target_wake = target_times["target_wake_time"]
            day_target_bed = target_times["target_bedtime"]
            plan_state = "PLANNED"

        daily_plan = DailyPlanRecord(
            roadmap_id=roadmap_orm.id,
            plan_date=plan_date_str,
            day_number=day_num,
            step_index=step_idx,
            target_bedtime=day_target_bed,
            target_wake_time=day_target_wake,
            budget_estimate=daily_budget,
            state=plan_state,
        )
        db.add(daily_plan)
        db.flush()

        # Generate collision-free plan items for this day
        dow_str = plan_dt.strftime("%A").upper()
        active_constraints = [c for c in constraints_data if c.day_of_week.value == dow_str]

        # P0.3 Item 1: MEASUREMENT - Bangun Tidur
        wake_item = PlanItemRecord(
            daily_plan_id=daily_plan.id,
            domain=PlanDomain.WAKE.value,
            title="Bangun Tidur",
            scheduled_time=day_target_wake,
            duration_minutes=0,
            is_critical=True,
        )
        db.add(wake_item)

        # P0.3 Item 2: MICRO-QUEST - Minum Air 1 Gelas Setelah Bangun
        hydrate_item = PlanItemRecord(
            daily_plan_id=daily_plan.id,
            domain=PlanDomain.NUTRITION.value,
            title="Minum 1 Gelas Air Setelah Bangun",
            scheduled_time=day_target_wake,
            duration_minutes=5,
            is_critical=False,
        )
        db.add(hydrate_item)

        # P1.3 Item 3: Meal 1 (Makan Siang)
        lunch_time, _ = resolve_schedule_collisions("12:30", 30, active_constraints, buffer_minutes=15)
        lunch_item = PlanItemRecord(
            daily_plan_id=daily_plan.id,
            domain=PlanDomain.NUTRITION.value,
            title="Meal 1 (Makan Siang)",
            scheduled_time=lunch_time,
            preferred_time="12:30",
            duration_minutes=30,
        )
        db.add(lunch_item)

        # Item 4: Micro-Movement (15 Menit)
        movement_time, _ = resolve_schedule_collisions("16:30", 15, active_constraints, buffer_minutes=15)
        movement_item = PlanItemRecord(
            daily_plan_id=daily_plan.id,
            domain=PlanDomain.MOVEMENT.value,
            title="Micro-Movement (15 Menit)",
            scheduled_time=movement_time,
            preferred_time="16:30",
            duration_minutes=15,
        )
        db.add(movement_item)

        # P1.3 Item 5: Meal 2 (Makan Malam)
        dinner_time, _ = resolve_schedule_collisions("19:00", 30, active_constraints, buffer_minutes=15)
        dinner_item = PlanItemRecord(
            daily_plan_id=daily_plan.id,
            domain=PlanDomain.NUTRITION.value,
            title="Meal 2 (Makan Malam)",
            scheduled_time=dinner_time,
            preferred_time="19:00",
            duration_minutes=30,
        )
        db.add(dinner_item)

        # Item 6: Persiapan Tidur (Wind-down)
        bed_item = PlanItemRecord(
            daily_plan_id=daily_plan.id,
            domain=PlanDomain.SLEEP.value,
            title="Persiapan Tidur (Redupkan Lampu)",
            scheduled_time=day_target_bed,
            duration_minutes=15,
            is_critical=True,
        )
        db.add(bed_item)

    db.commit()
    db.refresh(roadmap_orm)

    return {
        "user_id": user.id,
        "roadmap_id": roadmap_orm.id,
        "feasibility": feasibility,
        "total_days": roadmap_orm.total_days,
        "daily_budget": daily_budget,
    }


def get_active_daily_plan(db: Session, roadmap_id: str, day_number: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Get active daily plan record with transition context and items."""
    roadmap = db.query(Roadmap).filter(Roadmap.id == roadmap_id).first()
    if not roadmap:
        return None

    user = db.query(User).filter(User.id == roadmap.user_id).first()
    baseline = user.baseline if user else None
    goal = user.goal if user else None

    target_day = day_number if day_number is not None else roadmap.current_day
    daily_plan = db.query(DailyPlanRecord).filter(
        DailyPlanRecord.roadmap_id == roadmap.id,
        DailyPlanRecord.day_number == target_day,
    ).first()

    if not daily_plan:
        return None

    # Calculate actual spending today
    total_spent = sum(item.actual_cost or 0.0 for item in daily_plan.items)

    # Contextual transition state string
    if target_day == 1:
        transition_state = "BASELINE"
    elif daily_plan.state == "EVALUATED":
        transition_state = "EVALUATED"
    else:
        transition_state = "PROGRESSING" if roadmap.current_step_index > 0 else "STABILIZING"

    # Separate measurement from routine tasks
    wake_measurement = next((i for i in daily_plan.items if i.domain == PlanDomain.WAKE.value and i.is_critical), None)

    return {
        "daily_plan_id": daily_plan.id,
        "roadmap_id": roadmap.id,
        "plan_date": daily_plan.plan_date,
        "day_number": daily_plan.day_number,
        "total_days": roadmap.total_days,
        "step_index": daily_plan.step_index,
        "target_wake_time": daily_plan.target_wake_time,
        "target_bedtime": daily_plan.target_bedtime,
        "baseline_wake_time": baseline.wake_time if baseline else "10:00",
        "baseline_bedtime": baseline.bedtime if baseline else "02:00",
        "final_target_wake_time": goal.target_wake_time if goal else "07:00",
        "final_target_bedtime": goal.target_bedtime if goal else "23:00",
        "transition_state": transition_state,
        "weekly_budget": baseline.weekly_food_budget if baseline else 350000.0,
        "daily_budget": daily_plan.budget_estimate,
        "total_spent_today": total_spent,
        "remaining_budget_today": round(daily_plan.budget_estimate - total_spent, 2),
        "wake_measurement": {
            "id": wake_measurement.id if wake_measurement else None,
            "target_time": daily_plan.target_wake_time,
            "actual_time": wake_measurement.actual_time if wake_measurement else None,
            "is_recorded": wake_measurement.status == PlanItemStatus.COMPLETED.value if wake_measurement else False,
        } if wake_measurement else None,
        "items": [
            {
                "id": item.id,
                "domain": item.domain,
                "title": item.title,
                "scheduled_time": item.scheduled_time,
                "status": item.status,
                "actual_time": item.actual_time,
                "actual_cost": item.actual_cost,
                "is_critical": item.is_critical,
            }
            for item in daily_plan.items
        ],
    }
