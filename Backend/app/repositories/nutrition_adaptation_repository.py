import uuid
from typing import List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.nutrition_adaptation import NutritionAdaptationEvaluationRecord
from app.nutrition_adaptation.models import NutritionAdaptationEvaluationResultDTO


class NutritionAdaptationRepository:
    @staticmethod
    def save_evaluation(
        db: Session,
        owner_user_id: str,
        result_dto: NutritionAdaptationEvaluationResultDTO,
    ) -> NutritionAdaptationEvaluationRecord:
        eval_id = result_dto.evaluation_id or str(uuid.uuid4())
        try:
            eval_dt = datetime.fromisoformat(result_dto.evaluated_at)
        except Exception:
            eval_dt = datetime.now(timezone.utc)

        record = NutritionAdaptationEvaluationRecord(
            id=eval_id,
            owner_user_id=owner_user_id,
            evaluated_at=eval_dt,
            decision=result_dto.decision.value if hasattr(result_dto.decision, "value") else str(result_dto.decision),
            review_domain=result_dto.review_domain.value if hasattr(result_dto.review_domain, "value") else str(result_dto.review_domain),
            confidence=result_dto.confidence.value if hasattr(result_dto.confidence, "value") else str(result_dto.confidence),
            window_start=result_dto.evidence_window.start_date,
            window_end=result_dto.evidence_window.end_date,
            total_days=result_dto.evidence_window.total_days,
            usable_days=result_dto.evidence_window.usable_adherence_days,
            weight_measurements_count=result_dto.evidence_window.weight_measurement_count,
            slope_kg_per_day=result_dto.weight_trend.slope_kg_per_day,
            weight_direction=result_dto.weight_trend.direction.value if hasattr(result_dto.weight_trend.direction, "value") else str(result_dto.weight_trend.direction),
            adherence_category=result_dto.adherence_summary.category.value if hasattr(result_dto.adherence_summary.category, "value") else str(result_dto.adherence_summary.category),
            reason_codes=[r.value if hasattr(r, "value") else str(r) for r in result_dto.reason_codes],
            explanations=result_dto.explanations,
            policy_version=result_dto.policy_version,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_evaluations_for_user(
        db: Session,
        owner_user_id: str,
        limit: int = 10,
    ) -> List[NutritionAdaptationEvaluationRecord]:
        return (
            db.query(NutritionAdaptationEvaluationRecord)
            .filter(NutritionAdaptationEvaluationRecord.owner_user_id == owner_user_id)
            .order_by(NutritionAdaptationEvaluationRecord.evaluated_at.desc())
            .limit(limit)
            .all()
        )
