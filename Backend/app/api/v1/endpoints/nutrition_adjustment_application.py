from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.schemas.nutrition_adjustment_application import (
    NutritionAdjustmentApplicationResponse,
    NutritionStateRevisionResponse,
)
from app.services.nutrition_adjustment_application_service import (
    NutritionAdjustmentApplicationService,
)

router = APIRouter()


@router.get("/applications/{application_id}", response_model=NutritionAdjustmentApplicationResponse)
def get_adjustment_application(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Retrieves the details of a confirmed adjustment application record.
    """
    result = NutritionAdjustmentApplicationService.get_application(db, application_id, current_user.id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application record not found.")
    return result


@router.get("/state/revisions", response_model=List[NutritionStateRevisionResponse])
def list_nutrition_state_revisions(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Lists the chronological history of immutable nutrition state revisions for the authenticated user.
    """
    return NutritionAdjustmentApplicationService.list_state_revisions(db, current_user.id, limit)
