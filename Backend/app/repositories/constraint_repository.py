from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.user import ConstraintRecord
from app.schemas.identity import ConstraintCreate


class ConstraintRepository:
    @staticmethod
    def get_user_constraints(db: Session, user_id: str) -> List[ConstraintRecord]:
        return db.query(ConstraintRecord).filter(ConstraintRecord.user_id == user_id).all()

    @staticmethod
    def create_constraint(db: Session, user_id: str, data: ConstraintCreate) -> ConstraintRecord:
        constraint = ConstraintRecord(
            user_id=user_id,
            title=data.title,
            category=data.category.value if hasattr(data.category, "value") else str(data.category),
            day_of_week=data.day_of_week.value if hasattr(data.day_of_week, "value") else str(data.day_of_week),
            start_time=data.start_time,
            end_time=data.end_time,
            is_flexible=data.is_flexible,
        )
        db.add(constraint)
        db.commit()
        db.refresh(constraint)
        return constraint

    @staticmethod
    def delete_constraint(db: Session, user_id: str, constraint_id: str) -> bool:
        constraint = (
            db.query(ConstraintRecord)
            .filter(ConstraintRecord.id == constraint_id, ConstraintRecord.user_id == user_id)
            .first()
        )
        if not constraint:
            return False
        db.delete(constraint)
        db.commit()
        return True
