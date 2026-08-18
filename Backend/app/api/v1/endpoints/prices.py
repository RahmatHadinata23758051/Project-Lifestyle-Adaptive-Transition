from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.repositories.price_knowledge_repository import PriceKnowledgeRepository
from app.price_knowledge.models import LocationDTO
from app.price_knowledge.resolver import resolve_food_price
from app.price_knowledge.candidate_cost import estimate_candidate_cost
from app.food_candidates.models import FoodCandidateSetDTO, FoodCandidateItemDTO
from app.schemas.price_knowledge import (
    FoodPriceObservationResponse,
    ResolveFoodPriceInput,
    ResolveFoodPriceResponse,
    CandidateCostPreviewResponse,
    CandidateItemCostResponse,
)
from app.schemas.food_candidates import FoodCandidateSetResponse

router = APIRouter()


@router.get(
    "/foods/{food_id}",
    response_model=List[FoodPriceObservationResponse],
    summary="Get recorded price observations for a food item",
)
def get_food_price_observations(
    food_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    observations = PriceKnowledgeRepository.get_observations_for_food(
        db=db,
        food_item_id=food_id,
        user_id=current_user.id,
    )
    return observations


@router.post(
    "/resolve",
    response_model=ResolveFoodPriceResponse,
    summary="Resolve deterministic price estimate for a requested food quantity",
)
def resolve_price(
    payload: ResolveFoodPriceInput,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    observations = PriceKnowledgeRepository.get_observations_for_food(
        db=db,
        food_item_id=payload.food_item_id,
        user_id=current_user.id,
    )

    user_loc = (
        LocationDTO(
            country=payload.user_location.country,
            province=payload.user_location.province,
            city_regency=payload.user_location.city_regency,
            district=payload.user_location.district,
            market_or_store=payload.user_location.market_or_store,
        )
        if payload.user_location
        else None
    )

    result = resolve_food_price(
        food_item_id=payload.food_item_id,
        requested_quantity=payload.requested_quantity,
        requested_unit=payload.requested_unit,
        user_location=user_loc,
        observations=observations,
        include_promotions=payload.include_promotions,
    )

    return result


@router.post(
    "/candidate-cost-preview",
    response_model=CandidateCostPreviewResponse,
    summary="Estimate candidate set food cost without budget optimization",
)
def preview_candidate_cost(
    candidate: FoodCandidateSetResponse,
    user_location: Optional[LocationDTO] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    food_ids = [item.food_item_id for item in candidate.items]
    observations = PriceKnowledgeRepository.get_observations_for_foods(
        db=db,
        food_item_ids=food_ids,
        user_id=current_user.id,
    )

    candidate_dto = FoodCandidateSetDTO(
        candidate_id=candidate.candidate_id,
        slot_id=candidate.slot_id,
        items=[
            FoodCandidateItemDTO(
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
            for i in candidate.items
        ],
        total_energy_kcal=candidate.total_energy_kcal,
        total_protein_g=candidate.total_protein_g,
        total_fat_g=candidate.total_fat_g,
        total_carbohydrate_g=candidate.total_carbohydrate_g,
        energy_deviation_kcal=candidate.energy_deviation_kcal,
        absolute_energy_deviation=candidate.absolute_energy_deviation,
        match_status=candidate.match_status,
        explanations=candidate.explanations,
        preparation_complexity=candidate.preparation_complexity,
        source_quality=candidate.source_quality,
        macro_data_partial=candidate.macro_data_partial,
    )

    cost_estimate = estimate_candidate_cost(
        candidate=candidate_dto,
        user_location=user_location,
        observations=observations,
    )

    item_cost_responses = [
        CandidateItemCostResponse(
            food_item_id=ic.food_item_id,
            canonical_name=ic.canonical_name,
            grams=ic.grams,
            estimated_cost_idr=ic.estimated_cost_idr,
            resolution_status=ic.resolution_status,
            confidence=ic.confidence,
            location_match=ic.location_match,
            source_observation_ids=ic.source_observation_ids,
        )
        for ic in cost_estimate.item_costs
    ]

    return CandidateCostPreviewResponse(
        candidate_id=cost_estimate.candidate_id,
        estimated_cost_idr=cost_estimate.estimated_cost_idr,
        known_subtotal_idr=cost_estimate.known_subtotal_idr,
        cost_completeness=cost_estimate.cost_completeness,
        priced_item_count=cost_estimate.priced_item_count,
        total_item_count=cost_estimate.total_item_count,
        item_costs=item_cost_responses,
        confidence=cost_estimate.confidence,
        price_policy_version=cost_estimate.price_policy_version,
    )
