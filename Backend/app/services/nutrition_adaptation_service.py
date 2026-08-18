from typing import List, Optional
from sqlalchemy.orm import Session
from app.nutrition_adaptation.models import (
    NutritionAdaptationEvaluationInputDTO,
    NutritionAdaptationEvaluationResultDTO,
)
from app.nutrition_adaptation.evaluator import evaluate_nutrition_adaptation
from app.repositories.nutrition_adaptation_repository import NutritionAdaptationRepository


class NutritionAdaptationService:
    @staticmethod
    def evaluate_adaptation(
        db: Session,
        owner_user_id: str,
        input_dto: NutritionAdaptationEvaluationInputDTO,
        persist: bool = False,
    ) -> NutritionAdaptationEvaluationResultDTO:
        input_dto.user_id = owner_user_id
        result = evaluate_nutrition_adaptation(input_dto)
        if persist:
            NutritionAdaptationRepository.save_evaluation(db, owner_user_id, result)
        return result

    @staticmethod
    def get_evaluation_history(
        db: Session,
        owner_user_id: str,
        limit: int = 10,
    ) -> List[dict]:
        records = NutritionAdaptationRepository.get_evaluations_for_user(db, owner_user_id, limit)
        return [
            {
                "evaluation_id": r.id,
                "evaluated_at": r.evaluated_at.isoformat() if r.evaluated_at else None,
                "decision": r.decision,
                "review_domain": r.review_domain,
                "confidence": r.confidence,
                "window_start": r.window_start,
                "window_end": r.window_end,
                "total_days": r.total_days,
                "usable_days": r.usable_days,
                "weight_measurements_count": r.weight_measurements_count,
                "slope_kg_per_day": r.slope_kg_per_day,
                "weight_direction": r.weight_direction,
                "adherence_category": r.adherence_category,
                "reason_codes": r.reason_codes,
                "explanations": r.explanations,
                "policy_version": r.policy_version,
            }
            for r in records
        ]
