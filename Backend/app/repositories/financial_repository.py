from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.identity import FinancialProfile
from app.schemas.identity import FinancialProfileUpdate


class FinancialRepository:
    @staticmethod
    def get_by_user_id(db: Session, user_id: str) -> Optional[FinancialProfile]:
        return db.query(FinancialProfile).filter(FinancialProfile.user_id == user_id).first()

    @staticmethod
    def get_or_create(db: Session, user_id: str, default_budget: float = 350000.0) -> FinancialProfile:
        fp = db.query(FinancialProfile).filter(FinancialProfile.user_id == user_id).first()
        if not fp:
            fp = FinancialProfile(
                user_id=user_id,
                weekly_food_budget=default_budget,
                currency="IDR",
            )
            db.add(fp)
            db.commit()
            db.refresh(fp)
        return fp

    @staticmethod
    def update(db: Session, user_id: str, data: FinancialProfileUpdate) -> FinancialProfile:
        fp = FinancialRepository.get_or_create(db, user_id=user_id)
        fp.weekly_food_budget = data.weekly_food_budget
        fp.currency = data.currency
        fp.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        db.refresh(fp)
        return fp
