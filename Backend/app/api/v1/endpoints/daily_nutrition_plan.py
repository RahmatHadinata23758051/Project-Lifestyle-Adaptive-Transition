from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.schemas.daily_nutrition_plan import (
    DailyNutritionPlanPreviewRequest,
    DailyNutritionPlanResponse,
    DailyMealEntryResponse,
    DailyMealFoodItemResponse,
    DailyNutritionSummaryResponse,
    DailyBudgetSummaryResponse,
    DailyPlanWarningResponse,
    DailyPlanProvenanceResponse,
)
from app.daily_nutrition_plan.models import (
    DailyNutritionPlanAssemblyInputDTO,
    DailyNutritionPlanDTO,
)
from app.daily_nutrition_plan.assembler import assemble_daily_nutrition_plan
from app.food_candidates.models import FoodCandidateSetDTO, FoodCandidateItemDTO
from app.price_knowledge.models import CandidateCostEstimateDTO, ItemCostEstimateDTO
from app.budget_selection.models import (
    BudgetAwareSelectionResultDTO,
    DailyCandidateCombinationDTO,
    BudgetCandidateEvaluationDTO,
)

router = APIRouter()


@router.post(
    "/preview",
    response_model=DailyNutritionPlanResponse,
    summary="Preview assembled daily nutrition plan",
)
def preview_daily_nutrition_plan(
    payload: DailyNutritionPlanPreviewRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Convert candidates
    converted_candidates: Dict[str, FoodCandidateSetDTO] = {}
    for slot_id, c in payload.selected_candidates_by_slot.items():
        converted_candidates[slot_id] = FoodCandidateSetDTO(
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

    # Convert budget selection result
    bs = payload.budget_selection_result
    selected_comb = None
    if bs.selected_combination:
        selected_comb = DailyCandidateCombinationDTO(
            combination_id=bs.selected_combination.combination_id,
            selections={
                slot: BudgetCandidateEvaluationDTO(
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
                for slot, eval_d in bs.selected_combination.selections.items()
            },
            total_estimated_cost_idr=bs.selected_combination.total_estimated_cost_idr,
            budget_envelope_idr=bs.selected_combination.budget_envelope_idr,
            remaining_after_selection_idr=bs.selected_combination.remaining_after_selection_idr,
            price_confidence=bs.selected_combination.price_confidence,
            uses_stale_prices=bs.selected_combination.uses_stale_prices,
            nutrition_deviation_score=bs.selected_combination.nutrition_deviation_score,
            preference_score=bs.selected_combination.preference_score,
            all_strict_nutrition=bs.selected_combination.all_strict_nutrition,
        )

    bs_dto = BudgetAwareSelectionResultDTO(
        date=bs.date,
        logical_day_id=bs.logical_day_id,
        status=bs.status,
        budget_envelope_idr=bs.budget_envelope_idr,
        selected_combination=selected_comb,
        alternatives=[],
        shortfall_idr=bs.shortfall_idr,
        search_truncated=bs.search_truncated,
        explanations=bs.explanations,
        policy_versions=bs.policy_versions,
    )

    input_dto = DailyNutritionPlanAssemblyInputDTO(
        date=payload.date,
        logical_day_id=payload.logical_day_id,
        target_energy_kcal=payload.target_energy_kcal,
        nutrition_eligibility_status=payload.nutrition_eligibility_status,
        meal_schedule=payload.meal_schedule,
        budget_selection_result=bs_dto,
        selected_candidates_by_slot=converted_candidates,
        candidate_costs_by_candidate_id=converted_costs,
        policy_versions=payload.policy_versions,
        assessment_snapshot_id=payload.assessment_snapshot_id,
    )

    plan = assemble_daily_nutrition_plan(input_dto)

    # Response conversion
    nut_resp = (
        DailyNutritionSummaryResponse(
            target_energy_kcal=plan.nutrition_summary.target_energy_kcal,
            planned_energy_kcal=plan.nutrition_summary.planned_energy_kcal,
            energy_difference_kcal=plan.nutrition_summary.energy_difference_kcal,
            planned_protein_g=plan.nutrition_summary.planned_protein_g,
            planned_fat_g=plan.nutrition_summary.planned_fat_g,
            planned_carbohydrate_g=plan.nutrition_summary.planned_carbohydrate_g,
            macro_completeness=plan.nutrition_summary.macro_completeness,
            strict_match_slot_count=plan.nutrition_summary.strict_match_slot_count,
            near_match_slot_count=plan.nutrition_summary.near_match_slot_count,
        )
        if plan.nutrition_summary
        else None
    )

    bud_resp = (
        DailyBudgetSummaryResponse(
            budget_envelope_idr=plan.budget_summary.budget_envelope_idr,
            planned_cost_idr=plan.budget_summary.planned_cost_idr,
            remaining_after_plan_idr=plan.budget_summary.remaining_after_plan_idr,
            cost_completeness=plan.budget_summary.cost_completeness,
            price_confidence=plan.budget_summary.price_confidence,
            uses_stale_prices=plan.budget_summary.uses_stale_prices,
            budget_source=plan.budget_summary.budget_source,
        )
        if plan.budget_summary
        else None
    )

    entries_resp = [
        DailyMealEntryResponse(
            slot_id=e.slot_id,
            slot_type=e.slot_type,
            scheduled_time=e.scheduled_time,
            earliest_time=e.earliest_time,
            latest_time=e.latest_time,
            candidate_id=e.candidate_id,
            foods=[
                DailyMealFoodItemResponse(
                    food_item_id=f.food_item_id,
                    canonical_name=f.canonical_name,
                    role=f.role,
                    serving_name=f.serving_name,
                    grams=f.grams,
                    energy_kcal=f.energy_kcal,
                    protein_g=f.protein_g,
                    fat_g=f.fat_g,
                    carbohydrate_g=f.carbohydrate_g,
                )
                for f in e.foods
            ],
            planned_energy_kcal=e.planned_energy_kcal,
            planned_protein_g=e.planned_protein_g,
            planned_fat_g=e.planned_fat_g,
            planned_carbohydrate_g=e.planned_carbohydrate_g,
            nutrition_fit_status=e.nutrition_fit_status,
            estimated_cost_idr=e.estimated_cost_idr,
            cost_completeness=e.cost_completeness,
            price_confidence=e.price_confidence,
            uses_stale_prices=e.uses_stale_prices,
            location_context=e.location_context,
            preparation_context=e.preparation_context,
            explanations=e.explanations,
        )
        for e in plan.meal_entries
    ]

    warnings_resp = [
        DailyPlanWarningResponse(code=w.code, severity=w.severity, message=w.message)
        for w in plan.warnings
    ]

    prov_resp = DailyPlanProvenanceResponse(
        assessment_snapshot_id=plan.provenance.assessment_snapshot_id,
        nutrition_policy_version=plan.provenance.nutrition_policy_version,
        meal_structure_policy_version=plan.provenance.meal_structure_policy_version,
        food_candidate_policy_version=plan.provenance.food_candidate_policy_version,
        price_policy_version=plan.provenance.price_policy_version,
        budget_selection_policy_version=plan.provenance.budget_selection_policy_version,
        assembly_policy_version=plan.provenance.assembly_policy_version,
    )

    return DailyNutritionPlanResponse(
        plan_id=plan.plan_id,
        date=plan.date,
        logical_day_id=plan.logical_day_id,
        status=plan.status,
        nutrition_summary=nut_resp,
        budget_summary=bud_resp,
        meal_entries=entries_resp,
        warnings=warnings_resp,
        provenance=prov_resp,
        policy_versions=plan.policy_versions,
    )
