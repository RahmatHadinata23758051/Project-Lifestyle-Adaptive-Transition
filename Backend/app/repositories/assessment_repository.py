import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.identity import (
    Profile,
    UserGoal,
    SleepBaseline,
    FinancialProfile,
    Measurement,
    OnboardingStatus,
)
from app.models.user import User, TargetGoal, ConstraintRecord
from app.models.assessment import (
    NutritionBaseline,
    ActivityBaseline,
    AssessmentSnapshotRecord,
)
from app.assessment.router import AssessmentRouter
from app.assessment.completeness import AssessmentCompletenessEvaluator
from app.assessment.snapshot import AssessmentSnapshotBuilder
from app.schemas.assessment import AssessmentGoalInput


class AssessmentRepository:
    @staticmethod
    def get_user_known_data(db: Session, user_id: str) -> Dict[str, Any]:
        """
        Gathers all persistent user data across domains into a single key-value dictionary.
        """
        known: Dict[str, Any] = {}

        # 1. Profile
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        if profile:
            known["profile.birth_date"] = profile.birth_date
            known["profile.sex"] = profile.sex
            known["profile.height_cm"] = profile.height_cm
            known["profile.timezone"] = profile.timezone
            known["profile.occupation_type"] = profile.occupation_type
            if profile.current_weight_kg is not None:
                known["nutrition.current_weight_kg"] = profile.current_weight_kg

        # 2. Sleep Baseline & Target Goal
        sleep = (
            db.query(SleepBaseline)
            .filter(SleepBaseline.user_id == user_id, SleepBaseline.is_current == True)
            .order_by(SleepBaseline.captured_at.desc())
            .first()
        )
        if sleep:
            known["sleep.current_bedtime"] = sleep.bedtime
            known["sleep.current_wake_time"] = sleep.wake_time

        target_goal = db.query(TargetGoal).filter(TargetGoal.user_id == user_id).first()
        if target_goal:
            known["sleep.target_wake_time"] = target_goal.target_wake_time
            known["sleep.target_bedtime"] = target_goal.target_bedtime
            known["sleep.requested_transition_duration"] = target_goal.duration_days

        # 3. Nutrition Baseline
        nutrition = (
            db.query(NutritionBaseline)
            .filter(NutritionBaseline.user_id == user_id, NutritionBaseline.is_current == True)
            .order_by(NutritionBaseline.captured_at.desc())
            .first()
        )
        if nutrition:
            known["nutrition.meals_per_day"] = nutrition.meals_per_day
            known["nutrition.cooking_capability"] = nutrition.cooking_capability
            known["nutrition.allergies"] = nutrition.allergies
            known["nutrition.food_restrictions"] = nutrition.food_restrictions
            known["nutrition.food_preferences"] = nutrition.food_preferences
            known["nutrition.target_weight_kg"] = nutrition.target_weight_kg

        # 4. Financial Profile
        fp = db.query(FinancialProfile).filter(FinancialProfile.user_id == user_id).first()
        if fp:
            known["nutrition.weekly_food_budget"] = fp.weekly_food_budget

        # 5. Activity Baseline
        activity = (
            db.query(ActivityBaseline)
            .filter(ActivityBaseline.user_id == user_id, ActivityBaseline.is_current == True)
            .order_by(ActivityBaseline.captured_at.desc())
            .first()
        )
        if activity:
            known["activity.experience_level"] = activity.experience_level
            known["activity.available_days_per_week"] = activity.available_days_per_week
            known["activity.minutes_per_session"] = activity.minutes_per_session
            known["activity.equipment"] = activity.equipment_list.split(",") if activity.equipment_list else ["NONE"]
            known["activity.physical_limitations"] = activity.physical_limitations
            known["activity.available_space"] = activity.available_space
            known["activity.workout_preference"] = activity.workout_preference

        return known

    @staticmethod
    def get_active_goal_domains(db: Session, user_id: str) -> List[str]:
        goals = db.query(UserGoal).filter(UserGoal.user_id == user_id, UserGoal.status == "ACTIVE").all()
        return [g.domain for g in goals]

    @staticmethod
    def set_user_goals(db: Session, user_id: str, goals: List[AssessmentGoalInput]) -> List[UserGoal]:
        # Remove previous active goals
        db.query(UserGoal).filter(UserGoal.user_id == user_id).delete()

        created_goals: List[UserGoal] = []
        for g in goals:
            domain_str = g.domain.value if hasattr(g.domain, "value") else str(g.domain)
            priority_str = g.priority.value if hasattr(g.priority, "value") else str(g.priority)
            status_str = g.status.value if hasattr(g.status, "value") else str(g.status)

            goal_record = UserGoal(
                user_id=user_id,
                domain=domain_str,
                priority=priority_str,
                status=status_str,
                target_description=g.target_description,
            )
            db.add(goal_record)
            created_goals.append(goal_record)

        db.commit()
        for g in created_goals:
            db.refresh(g)
        return created_goals

    @staticmethod
    def ingest_answers(db: Session, user_id: str, answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stores answers into appropriate persistent models based on question key namespace.
        Preserves historical baselines (is_current = False).
        """
        # Ensure user base record exists if needed
        user_record = db.query(User).filter(User.id == user_id).first()
        if not user_record:
            user_record = User(id=user_id, email=f"{user_id}@chronos.local")
            db.add(user_record)

        # 1. Profile answers
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        if not profile:
            profile = Profile(user_id=user_id, onboarding_status=OnboardingStatus.IN_PROGRESS.value)
            db.add(profile)

        for k, v in answers.items():
            if k == "profile.birth_date":
                profile.birth_date = str(v)
            elif k == "profile.sex":
                profile.sex = str(v)
            elif k == "profile.height_cm":
                profile.height_cm = float(v)
            elif k == "profile.timezone":
                profile.timezone = str(v)
            elif k == "profile.occupation_type":
                profile.occupation_type = str(v)
            elif k == "nutrition.current_weight_kg":
                profile.current_weight_kg = float(v)
                # Store historical measurement
                m = Measurement(
                    user_id=user_id,
                    metric_type="WEIGHT",
                    value=float(v),
                    unit="kg",
                )
                db.add(m)

        # 2. Sleep Baseline answers
        if "sleep.current_bedtime" in answers or "sleep.current_wake_time" in answers:
            existing_sleeps = db.query(SleepBaseline).filter(SleepBaseline.user_id == user_id).all()
            for s in existing_sleeps:
                s.is_current = False

            bedtime = str(answers.get("sleep.current_bedtime", "02:00"))
            wake_time = str(answers.get("sleep.current_wake_time", "10:00"))
            new_sleep = SleepBaseline(
                user_id=user_id,
                bedtime=bedtime,
                wake_time=wake_time,
                is_current=True,
            )
            db.add(new_sleep)

        if "sleep.target_wake_time" in answers or "sleep.requested_transition_duration" in answers:
            tg = db.query(TargetGoal).filter(TargetGoal.user_id == user_id).first()
            if not tg:
                tg = TargetGoal(
                    user_id=user_id,
                    target_wake_time=str(answers.get("sleep.target_wake_time", "07:00")),
                    target_bedtime=str(answers.get("sleep.target_bedtime")) if answers.get("sleep.target_bedtime") else None,
                    duration_days=int(answers.get("sleep.requested_transition_duration", 30)),
                )
                db.add(tg)
            else:
                if "sleep.target_wake_time" in answers:
                    tg.target_wake_time = str(answers["sleep.target_wake_time"])
                if "sleep.target_bedtime" in answers:
                    tg.target_bedtime = str(answers["sleep.target_bedtime"])
                if "sleep.requested_transition_duration" in answers:
                    tg.duration_days = int(answers["sleep.requested_transition_duration"])

        # 3. Financial Profile answers
        if "nutrition.weekly_food_budget" in answers:
            fp = db.query(FinancialProfile).filter(FinancialProfile.user_id == user_id).first()
            if not fp:
                fp = FinancialProfile(user_id=user_id, weekly_food_budget=float(answers["nutrition.weekly_food_budget"]))
                db.add(fp)
            else:
                fp.weekly_food_budget = float(answers["nutrition.weekly_food_budget"])

        # 4. Nutrition Baseline answers
        nutrition_keys = ["nutrition.meals_per_day", "nutrition.cooking_capability", "nutrition.allergies"]
        if any(k in answers for k in nutrition_keys):
            existing_nutritions = db.query(NutritionBaseline).filter(NutritionBaseline.user_id == user_id).all()
            for n in existing_nutritions:
                n.is_current = False

            new_nutrition = NutritionBaseline(
                user_id=user_id,
                meals_per_day=int(answers.get("nutrition.meals_per_day", 3)),
                cooking_capability=str(answers.get("nutrition.cooking_capability", "LIMITED")),
                allergies=str(answers.get("nutrition.allergies", "NONE")),
                food_restrictions=answers.get("nutrition.food_restrictions"),
                food_preferences=answers.get("nutrition.food_preferences"),
                target_weight_kg=float(answers["nutrition.target_weight_kg"]) if "nutrition.target_weight_kg" in answers and answers["nutrition.target_weight_kg"] is not None else None,
                is_current=True,
            )
            db.add(new_nutrition)

        # 5. Activity Baseline answers
        activity_keys = ["activity.experience_level", "activity.available_days_per_week", "activity.minutes_per_session"]
        if any(k in answers for k in activity_keys):
            existing_activities = db.query(ActivityBaseline).filter(ActivityBaseline.user_id == user_id).all()
            for a in existing_activities:
                a.is_current = False

            equip = answers.get("activity.equipment", ["NONE"])
            equip_str = ",".join(equip) if isinstance(equip, list) else str(equip)

            new_activity = ActivityBaseline(
                user_id=user_id,
                experience_level=str(answers.get("activity.experience_level", "BEGINNER")),
                available_days_per_week=int(answers.get("activity.available_days_per_week", 3)),
                minutes_per_session=int(answers.get("activity.minutes_per_session", 30)),
                equipment_list=equip_str,
                physical_limitations=str(answers.get("activity.physical_limitations", "NONE")),
                available_space=answers.get("activity.available_space"),
                workout_preference=answers.get("activity.workout_preference"),
                is_current=True,
            )
            db.add(new_activity)

        profile.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()

        # Return updated completeness
        known_data = AssessmentRepository.get_user_known_data(db, user_id)
        # Merge immediate answers into known_data in case some are memory-only
        known_data.update(answers)
        active_goals = AssessmentRepository.get_active_goal_domains(db, user_id)
        return AssessmentCompletenessEvaluator.evaluate(active_goals, known_data)

    @staticmethod
    def create_assessment_snapshot(db: Session, user_id: str) -> Dict[str, Any]:
        """
        Creates an immutable snapshot if assessment is complete and ready.
        """
        known_data = AssessmentRepository.get_user_known_data(db, user_id)
        active_goals_records = db.query(UserGoal).filter(UserGoal.user_id == user_id, UserGoal.status == "ACTIVE").all()
        active_goals_list = [g.domain for g in active_goals_records]

        completeness = AssessmentCompletenessEvaluator.evaluate(active_goals_list, known_data)
        if not completeness["is_plan_ready"]:
            raise ValueError(f"Assessment incomplete. Missing required fields: {completeness['missing_required_fields']}")

        goals_data = [
            {"domain": g.domain, "priority": g.priority, "target_description": g.target_description}
            for g in active_goals_records
        ]
        constraints = [
            {"title": c.title, "day_of_week": c.day_of_week, "start_time": c.start_time, "end_time": c.end_time}
            for c in db.query(ConstraintRecord).filter(ConstraintRecord.user_id == user_id).all()
        ]

        snapshot_dict = AssessmentSnapshotBuilder.build_snapshot(
            user_id=user_id,
            active_goals=goals_data,
            known_data=known_data,
            constraints=constraints,
            completeness_eval=completeness,
        )

        record = AssessmentSnapshotRecord(
            id=snapshot_dict["snapshot_id"],
            user_id=user_id,
            snapshot_data=json.dumps(snapshot_dict),
            created_at=snapshot_dict["created_at"],
        )
        db.add(record)

        # Update profile onboarding status to COMPLETED
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        if profile:
            profile.onboarding_status = OnboardingStatus.COMPLETED.value

        db.commit()
        db.refresh(record)

        return {
            "snapshot_id": record.id,
            "user_id": user_id,
            "created_at": record.created_at,
            "snapshot_data": snapshot_dict,
        }
