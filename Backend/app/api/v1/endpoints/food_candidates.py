from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.repositories.food_repository import FoodRepository
from app.repositories.assessment_repository import AssessmentRepository
from app.services.food_knowledge_service import FoodKnowledgeService
from app.meal_structure.models import MealSlotDTO
from app.meal_structure.constants import MealWindowType, ScheduleProvenance, MealScheduleReasonCode
from app.food_candidates.models import CandidateGenerationInputDTO
from app.food_candidates.generator import generate_food_candidates
from app.schemas.food_candidates import (
    FoodCandidatePreviewInput,
    FoodCandidateGenerationResponse,
    FoodCandidateSetResponse,
    FoodCandidateItemResponse,
)

router = APIRouter()


@router.post(
    "/preview",
    response_model=FoodCandidateGenerationResponse,
    summary="Generate deterministic candidate food combinations to fill a meal slot target",
)
def preview_food_candidates(
    payload: FoodCandidatePreviewInput,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    known_data = AssessmentRepository.get_user_known_data(db, user_id=current_user.id)

    # 1. Resolve Allergies & Cooking Capability
    user_allergies = payload.user_allergies or known_data.get("nutrition.allergies") or []
    if isinstance(user_allergies, str):
        user_allergies = [a.strip() for a in user_allergies.split(",") if a.strip()]

    cooking_capability = (
        payload.cooking_capability
        or known_data.get("nutrition.cooking_capability")
        or "CAN_COOK"
    )

    # 2. Build Slot DTO
    min_kcal = payload.min_kcal if payload.min_kcal is not None else round(payload.target_kcal * 0.85, 1)
    max_kcal = payload.max_kcal if payload.max_kcal is not None else round(payload.target_kcal * 1.15, 1)

    slot_dto = MealSlotDTO(
        slot_id=payload.slot_id,
        slot_type=payload.slot_type,
        sequence=1,
        preferred_time="12:00",
        earliest_time="11:15",
        latest_time="12:45",
        duration_minutes=30,
        target_kcal=payload.target_kcal,
        min_kcal=min_kcal,
        max_kcal=max_kcal,
        schedule_source=ScheduleProvenance.DERIVED,
        reason_code=MealScheduleReasonCode.NORMAL_BASELINE,
        window_type=MealWindowType.FLEXIBLE,
    )

    # 3. Retrieve Food Knowledge Records (Outside Pure Engine)
    food_records = FoodRepository.search_foods(
        db=db,
        query="",
        is_active_only=True,
        limit=100,
    )
    food_dtos = [FoodKnowledgeService.record_to_dto(rec) for rec in food_records]

    # 4. Invoke Pure Engine
    input_dto = CandidateGenerationInputDTO(
        slot=slot_dto,
        food_pool=food_dtos,
        user_allergies=user_allergies,
        user_restrictions=payload.user_restrictions,
        cooking_capability=cooking_capability,
        user_equipment=payload.user_equipment,
    )

    result_dto = generate_food_candidates(input_dto)

    candidate_responses: List[FoodCandidateSetResponse] = []
    for c in result_dto.candidates:
        item_responses = [
            FoodCandidateItemResponse(
                food_item_id=i.food_item_id,
                canonical_name=i.canonical_name,
                role=i.role,
                serving_id=i.serving_id,
                serving_name=i.serving_name,
                grams=i.grams,
                energy_kcal=i.energy_kcal,
                protein_g=i.protein_g,
                fat_g=i.fat_g,
                carbohydrate_g=i.carbohydrate_g,
            )
            for i in c.items
        ]
        candidate_responses.append(
            FoodCandidateSetResponse(
                candidate_id=c.candidate_id,
                slot_id=c.slot_id,
                items=item_responses,
                total_energy_kcal=c.total_energy_kcal,
                total_protein_g=c.total_protein_g,
                total_fat_g=c.total_fat_g,
                total_carbohydrate_g=c.total_carbohydrate_g,
                energy_deviation_kcal=c.energy_deviation_kcal,
                absolute_energy_deviation=c.absolute_energy_deviation,
                match_status=c.match_status,
                explanations=c.explanations,
                preparation_complexity=c.preparation_complexity,
                source_quality=c.source_quality,
                macro_data_partial=c.macro_data_partial,
            )
        )

    return FoodCandidateGenerationResponse(
        slot_id=result_dto.slot_id,
        status=result_dto.status,
        candidate_count=result_dto.candidate_count,
        candidates=candidate_responses,
        rejected_counts_by_reason=result_dto.rejected_counts_by_reason,
        search_truncated=result_dto.search_truncated,
        policy_version=result_dto.policy_version,
    )
