import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.assessment.field_registry import calculate_age_from_birthdate


class AssessmentSnapshotBuilder:
    """
    Builds an immutable logical Assessment Snapshot.
    Represents the exact user state at the moment the plan/roadmap is created.
    Protects historical plans from mutating when live profiles change.
    """

    @staticmethod
    def build_snapshot(
        user_id: str,
        active_goals: List[Dict[str, Any]],
        known_data: Dict[str, Any],
        constraints: List[Dict[str, Any]],
        completeness_eval: Dict[str, Any],
    ) -> Dict[str, Any]:
        birth_date = known_data.get("profile.birth_date")
        derived_age = calculate_age_from_birthdate(birth_date)

        snapshot_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        snapshot: Dict[str, Any] = {
            "snapshot_id": snapshot_id,
            "user_id": user_id,
            "created_at": created_at,
            "active_goals": active_goals,
            "core_profile": {
                "birth_date": birth_date,
                "age": derived_age,
                "sex": known_data.get("profile.sex"),
                "height_cm": known_data.get("profile.height_cm"),
                "timezone": known_data.get("profile.timezone", "Asia/Jakarta"),
                "occupation_type": known_data.get("profile.occupation_type"),
            },
            "sleep_domain": {
                "current_bedtime": known_data.get("sleep.current_bedtime"),
                "current_wake_time": known_data.get("sleep.current_wake_time"),
                "target_wake_time": known_data.get("sleep.target_wake_time"),
                "target_bedtime": known_data.get("sleep.target_bedtime"),
                "requested_transition_duration": known_data.get("sleep.requested_transition_duration"),
                "sleep_consistency": known_data.get("sleep.sleep_consistency"),
                "caffeine_pattern": known_data.get("sleep.caffeine_pattern"),
                "screen_habit": known_data.get("sleep.screen_habit"),
            },
            "nutrition_domain": {
                "current_weight_kg": known_data.get("nutrition.current_weight_kg"),
                "meals_per_day": known_data.get("nutrition.meals_per_day"),
                "weekly_food_budget": known_data.get("nutrition.weekly_food_budget"),
                "cooking_capability": known_data.get("nutrition.cooking_capability"),
                "allergies": known_data.get("nutrition.allergies"),
                "food_restrictions": known_data.get("nutrition.food_restrictions"),
                "food_preferences": known_data.get("nutrition.food_preferences"),
                "target_weight_kg": known_data.get("nutrition.target_weight_kg"),
            },
            "activity_domain": {
                "experience_level": known_data.get("activity.experience_level"),
                "available_days_per_week": known_data.get("activity.available_days_per_week"),
                "minutes_per_session": known_data.get("activity.minutes_per_session"),
                "equipment": known_data.get("activity.equipment"),
                "physical_limitations": known_data.get("activity.physical_limitations"),
                "available_space": known_data.get("activity.available_space"),
                "workout_preference": known_data.get("activity.workout_preference"),
            },
            "constraints": constraints,
            "completeness_summary": completeness_eval,
        }
        return snapshot
