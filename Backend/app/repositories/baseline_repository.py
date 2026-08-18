from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.identity import SleepBaseline
from app.schemas.identity import SleepBaselineCreate


class BaselineRepository:
    @staticmethod
    def get_current_sleep_baseline(db: Session, user_id: str) -> Optional[SleepBaseline]:
        return (
            db.query(SleepBaseline)
            .filter(SleepBaseline.user_id == user_id, SleepBaseline.is_current == True)
            .order_by(SleepBaseline.captured_at.desc())
            .first()
        )

    @staticmethod
    def get_sleep_baseline_history(db: Session, user_id: str) -> List[SleepBaseline]:
        return (
            db.query(SleepBaseline)
            .filter(SleepBaseline.user_id == user_id)
            .order_by(SleepBaseline.captured_at.desc())
            .all()
        )

    @staticmethod
    def create_sleep_baseline(db: Session, user_id: str, data: SleepBaselineCreate) -> SleepBaseline:
        """
        Preserve historical baseline (P0.16):
        Demote all existing baselines to is_current = False, then insert new current baseline.
        """
        existing_baselines = db.query(SleepBaseline).filter(SleepBaseline.user_id == user_id).all()
        for b in existing_baselines:
            b.is_current = False

        new_baseline = SleepBaseline(
            user_id=user_id,
            bedtime=data.bedtime,
            wake_time=data.wake_time,
            is_current=True,
            captured_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(new_baseline)
        db.commit()
        db.refresh(new_baseline)
        return new_baseline
