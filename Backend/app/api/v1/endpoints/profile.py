from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.repositories.profile_repository import ProfileRepository
from app.schemas.identity import ProfileResponse, ProfileUpdate

router = APIRouter()


@router.get("", response_model=ProfileResponse, summary="Get current authenticated user profile")
def get_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = ProfileRepository.get_or_create(db, user_id=current_user.id)
    return profile


@router.patch("", response_model=ProfileResponse, summary="Update editable profile fields")
def update_profile(
    payload: ProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = ProfileRepository.update(db, user_id=current_user.id, data=payload)
    return updated
