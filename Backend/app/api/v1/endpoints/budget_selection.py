from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.schemas.budget_selection import (
    BudgetContextInput,
    BudgetAwareSelectionPreviewResponse,
    DailyCandidateCombinationResponse,
    BudgetCandidateEvaluationResponse,
)
from app.schemas.food_candidates import FoodCandidateSetResponse
from app.schemas.price_knowledge import CandidateCostPreviewResponse
from app.budget_selection.models import (
    BudgetAwareSelectionInputDTO,
    BudgetContextDTO,
    BudgetCandidateEvaluationDTO,
    DailyCandidateCombinationDTO,
)
from app.budget_selection.selector import select_budget_aware_candidates
from app.food_candidates.models import FoodCandidateSetDTO, FoodCandidateItemDTO
from app.price_knowledge.models import CandidateCostEstimateDTO, ItemCostEstimateDTO

router = APIRouter()


class BudgetSelectionPreviewRequest(BaseModel):
    date: str
    logical_day_id: str
    slot_ids: List[str]
    candidates_by_slot: Dict[str, List[FoodCandidateSetResponse]]
    candidate_costs_by_candidate_id: Dict[str, CandidateCostPreviewResponse]
    budget_context: Optional[BudgetContextInput] = None
    user_preferences_by_food_id: Optional[Dict[str, int]] = None


@router.post(
    "/preview",
    response_model=BudgetAwareSelectionPreviewResponse,
    summary="Preview budget-aware candidate selection across active meal slots",
)
def preview_budget_selection(
    payload: BudgetSelectionPreviewRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Convert candidates
    converted_candidates: Dict[str, List[FoodCandidateSetDTO]] = {}
    for slot_id, c_list in payload.candidates_by_slot.items():
        converted_candidates[slot_id] = [
            FoodCandidateSetDTO(
                candidate_id=c.candidate_id,
                slot_id=c.slot_id,
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
                    for i in c.items
                ],
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
            for c in c_list
        ]

    # Convert candidate costs
    converted_costs: Dict[str, CandidateCostEstimateDTO] = {}
    for cid, cost in payload.candidate_costs_by_candidate_id.items():
        converted_costs[cid] = CandidateCostEstimateDTO(
            candidate_id=cost.candidate_id,
            estimated_cost_idr=cost.estimated_cost_idr,
            known_subtotal_idr=cost.known_subtotal_idr,
            cost_completeness=cost.cost_completeness,
            priced_item_count=cost.priced_item_count,
            total_item_count=cost.total_item_count,
            item_costs=[
                ItemCostEstimateDTO(
                    food_item_id=ic.food_item_id,
                    canonical_name=ic.canonical_name,
                    grams=ic.grams,
                    estimated_cost_idr=ic.estimated_cost_idr,
                    resolution_status=ic.resolution_status,
                    confidence=ic.confidence,
                    location_match=ic.location_match,
                    source_observation_ids=ic.source_observation_ids,
                    price_basis_applied=ic.price_basis_applied,
                )
                for ic in cost.item_costs
            ],
            confidence=cost.confidence,
            uses_stale_prices=cost.uses_stale_prices,
            price_policy_version=cost.price_policy_version,
        )

    # Convert budget context
    ctx_dto = None
    if payload.budget_context:
        ctx_dto = BudgetContextDTO(
            currency_code=payload.budget_context.currency_code,
            budget_period=payload.budget_context.budget_period,
            total_food_budget_idr=payload.budget_context.total_food_budget_idr,
            spent_food_budget_idr=payload.budget_context.spent_food_budget_idr,
            remaining_food_budget_idr=payload.budget_context.remaining_food_budget_idr,
            period_days_remaining=payload.budget_context.period_days_remaining,
            explicit_today_budget_idr=payload.budget_context.explicit_today_budget_idr,
            budget_source=payload.budget_context.budget_source,
        )

    input_dto = BudgetAwareSelectionInputDTO(
        date=payload.date,
        logical_day_id=payload.logical_day_id,
        slot_ids=payload.slot_ids,
        candidates_by_slot=converted_candidates,
        candidate_costs_by_candidate_id=converted_costs,
        budget_context=ctx_dto,
        user_preferences_by_food_id=payload.user_preferences_by_food_id,
    )

    result = select_budget_aware_candidates(input_dto)

    def comb_to_response(c: DailyCandidateCombinationDTO) -> DailyCandidateCombinationResponse:
        return DailyCandidateCombinationResponse(
            combination_id=c.combination_id,
            selections={
                slot: BudgetCandidateEvaluationResponse(
                    candidate_id=eval_d.candidate_id,
                    slot_id=eval_d.slot_id,
                    estimated_cost_idr=eval_d.estimated_cost_idr,
                    budget_status=eval_d.budget_status,
                    price_confidence=eval_d.price_confidence,
                    uses_stale_prices=eval_d.uses_stale_prices,
                    nutrition_fit_status=eval_d.nutrition_fit_status,
                    preference_score=eval_d.preference_score,
                    absolute_energy_deviation=eval_d.absolute_energy_deviation,
                    explanations=eval_d.explanations,
                )
                for slot, eval_d in c.selections.items()
            },
            total_estimated_cost_idr=c.total_estimated_cost_idr,
            budget_envelope_idr=c.budget_envelope_idr,
            remaining_after_selection_idr=c.remaining_after_selection_idr,
            price_confidence=c.price_confidence,
            uses_stale_prices=c.uses_stale_prices,
            nutrition_deviation_score=c.nutrition_deviation_score,
            preference_score=c.preference_score,
            all_strict_nutrition=c.all_strict_nutrition,
        )

    sel_resp = comb_to_response(result.selected_combination) if result.selected_combination else None
    alt_resps = [comb_to_response(a) for a in result.alternatives]

    return BudgetAwareSelectionPreviewResponse(
        date=result.date,
        logical_day_id=result.logical_day_id,
        status=result.status,
        budget_envelope_idr=result.budget_envelope_idr,
        selected_combination=sel_resp,
        alternatives=alt_resps,
        shortfall_idr=result.shortfall_idr,
        search_truncated=result.search_truncated,
        explanations=result.explanations,
        policy_versions=result.policy_versions,
    )
