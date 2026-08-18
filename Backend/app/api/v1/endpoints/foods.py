from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.services.food_knowledge_service import FoodKnowledgeService
from app.schemas.food_knowledge import (
    FoodSearchResponse,
    FoodItemResponse,
    ServingCalculationInput,
    ServingCalculationResponse,
)

router = APIRouter()


@router.get(
    "/search",
    response_model=FoodSearchResponse,
    summary="Search food reference items with deterministic canonical and alias matching",
)
def search_foods(
    q: str = Query("", description="Search term for food name or alias"),
    category: Optional[str] = Query(None, description="Optional category filter"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    results_dto = FoodKnowledgeService.search_foods(
        db=db,
        query=q,
        category=category,
        limit=limit,
        offset=offset,
    )
    return FoodSearchResponse(
        total_matches=len(results_dto),
        query=q,
        results=[FoodItemResponse.model_validate(dto) for dto in results_dto],
    )


@router.get(
    "/{food_id}",
    response_model=FoodItemResponse,
    summary="Get full food detail including nutrients, basis, servings, allergens, and source provenance",
)
def get_food_detail(
    food_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dto = FoodKnowledgeService.get_food_detail(db=db, food_id=food_id)
    if not dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Food item dengan ID '{food_id}' tidak ditemukan.",
        )
    return FoodItemResponse.model_validate(dto)


@router.post(
    "/{food_id}/calculate-serving",
    response_model=ServingCalculationResponse,
    summary="Deterministically scale nutrients for a specified weight in grams or predefined serving unit",
)
def calculate_serving(
    food_id: str,
    payload: ServingCalculationInput,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        calc_result = FoodKnowledgeService.calculate_serving_nutrients(
            db=db,
            food_id=food_id,
            grams=payload.grams,
            serving_id=payload.serving_id,
            serving_count=payload.serving_count,
        )
        return ServingCalculationResponse.model_validate(calc_result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
