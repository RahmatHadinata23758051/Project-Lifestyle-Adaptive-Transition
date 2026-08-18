from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.identity import Profile, OnboardingStatus
from app.schemas.identity import ProfileUpdate


class ProfileRepository:
    @staticmethod
    def get_by_user_id(db: Session, user_id: str) -> Optional[Profile]:
        return db.query(Profile).filter(Profile.user_id == user_id).first()

    @staticmethod
    def get_or_create(db: Session, user_id: str, display_name: Optional[str] = None) -> Profile:
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        if not profile:
            profile = Profile(
                user_id=user_id,
                display_name=display_name,
                onboarding_status=OnboardingStatus.NOT_STARTED.value,
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return profile

    @staticmethod
    def update(db: Session, user_id: str, data: ProfileUpdate) -> Profile:
        profile = ProfileRepository.get_or_create(db, user_id=user_id)
        update_dict = data.model_dump(exclude_unset=True)

        for key, value in update_dict.items():
            if key == "onboarding_status" and value is not None:
                setattr(profile, key, value.value if hasattr(value, "value") else str(value))
            elif value is not None:
                setattr(profile, key, value)

        profile.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        db.refresh(profile)
        return profile
