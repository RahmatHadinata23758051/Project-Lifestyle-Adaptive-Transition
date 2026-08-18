from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.identity import UserGoal
from app.schemas.identity import GoalCreate


class GoalRepository:
    @staticmethod
    def get_user_goals(db: Session, user_id: str) -> List[UserGoal]:
        return db.query(UserGoal).filter(UserGoal.user_id == user_id).all()

    @staticmethod
    def create_goal(db: Session, user_id: str, data: GoalCreate) -> UserGoal:
        goal = UserGoal(
            user_id=user_id,
            domain=data.domain.value if hasattr(data.domain, "value") else str(data.domain),
            priority=data.priority.value if hasattr(data.priority, "value") else str(data.priority),
            status=data.status.value if hasattr(data.status, "value") else str(data.status),
            target_description=data.target_description,
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        return goal
