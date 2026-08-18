from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.schemas.nutrition_adherence import (
    MealCheckinRequest,
    MealCheckinResponse,
    UnplannedIntakeRequest,
    UnplannedIntakeResponse,
    DailyNutritionAdherenceResponse,
    EvaluateAdherencePreviewRequest,
)
from app.nutrition_adherence.models import (
    MealCheckinDTO,
    ActualFoodItemDTO,
    UnplannedIntakeDTO,
)
from app.daily_nutrition_plan.models import (
    DailyNutritionPlanDTO,
    DailyMealEntryDTO,
    DailyMealFoodItemDTO,
    DailyNutritionSummaryDTO,
    DailyBudgetSummaryDTO,
    DailyPlanProvenanceDTO,
)
from app.services.nutrition_adherence_service import NutritionAdherenceService
from app.repositories.nutrition_adherence_repository import NutritionAdherenceRepository
from app.nutrition_adherence.adherence import evaluate_daily_nutrition_adherence

router = APIRouter()


@router.post("/meals", response_model=MealCheckinResponse, status_code=status.HTTP_201_CREATED)
def record_meal_checkin(
    request: MealCheckinRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    owner_user_id = current_user.id

    checked_in_at_str = request.checked_in_at or datetime.now(timezone.utc).isoformat()

    items = [
        ActualFoodItemDTO(
            food_item_id=it.food_item_id,
            display_name=it.display_name,
            serving_id=it.serving_id,
            serving_name=it.serving_name,
            grams=it.grams,
            quantity=it.quantity,
            energy_kcal=it.energy_kcal,
            protein_g=it.protein_g,
            fat_g=it.fat_g,
            carbohydrate_g=it.carbohydrate_g,
            source_type=it.source_type,
            certainty=it.certainty,
        )
        for it in request.actual_items
    ]

    checkin_dto = MealCheckinDTO(
        plan_id=request.plan_id,
        logical_day_id=request.logical_day_id,
        slot_id=request.slot_id,
        status=request.status,
        meal_occurred_at=request.meal_occurred_at,
        checked_in_at=checked_in_at_str,
        actual_items=items,
        actual_spend_idr=request.actual_spend_idr,
        deviation_reason=request.deviation_reason,
        notes=request.notes,
        certainty=request.certainty,
    )

    try:
        saved = NutritionAdherenceService.record_meal_checkin(db, owner_user_id, checkin_dto)
        return saved
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/unplanned", response_model=UnplannedIntakeResponse, status_code=status.HTTP_201_CREATED)
def record_unplanned_intake(
    request: UnplannedIntakeRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    owner_user_id = current_user.id

    rec_at = request.recorded_at or datetime.now(timezone.utc).isoformat()

    items = [
        ActualFoodItemDTO(
            food_item_id=it.food_item_id,
            display_name=it.display_name,
            serving_id=it.serving_id,
            serving_name=it.serving_name,
            grams=it.grams,
            quantity=it.quantity,
            energy_kcal=it.energy_kcal,
            protein_g=it.protein_g,
            fat_g=it.fat_g,
            carbohydrate_g=it.carbohydrate_g,
            source_type=it.source_type,
            certainty=it.certainty,
        )
        for it in request.items
    ]

    intake_dto = UnplannedIntakeDTO(
        logical_day_id=request.logical_day_id,
        occurred_at=request.occurred_at,
        recorded_at=rec_at,
        items=items,
        actual_spend_idr=request.actual_spend_idr,
        reason=request.reason,
        notes=request.notes,
    )

    try:
        saved = NutritionAdherenceService.record_unplanned_intake(db, owner_user_id, intake_dto)
        return saved
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/adherence/preview", response_model=DailyNutritionAdherenceResponse)
def preview_daily_adherence(
    payload: EvaluateAdherencePreviewRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Pure in-memory preview of daily adherence against a plan.
    """
    plan_d = payload.plan
    converted_entries = [
        DailyMealEntryDTO(
            slot_id=e.slot_id,
            slot_type=e.slot_type,
            scheduled_time=e.scheduled_time,
            earliest_time=e.earliest_time,
            latest_time=e.latest_time,
            candidate_id=e.candidate_id,
            foods=[
                DailyMealFoodItemDTO(
                    food_item_id=f.food_item_id,
                    canonical_name=f.canonical_name,
                    role=getattr(f, "role", "STAPLE"),
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
            preparation_context=e.preparation_context,
            explanations=e.explanations,
        )
        for e in plan_d.meal_entries
    ]

    plan_dto = DailyNutritionPlanDTO(
        plan_id=plan_d.plan_id,
        date=plan_d.date,
        logical_day_id=plan_d.logical_day_id,
        status=plan_d.status,
        nutrition_summary=(
            DailyNutritionSummaryDTO(
                target_energy_kcal=plan_d.nutrition_summary.target_energy_kcal,
                planned_energy_kcal=plan_d.nutrition_summary.planned_energy_kcal,
                energy_difference_kcal=plan_d.nutrition_summary.energy_difference_kcal,
                planned_protein_g=plan_d.nutrition_summary.planned_protein_g,
                planned_fat_g=plan_d.nutrition_summary.planned_fat_g,
                planned_carbohydrate_g=plan_d.nutrition_summary.planned_carbohydrate_g,
                macro_completeness=plan_d.nutrition_summary.macro_completeness,
                strict_match_slot_count=plan_d.nutrition_summary.strict_match_slot_count,
                near_match_slot_count=plan_d.nutrition_summary.near_match_slot_count,
            )
            if plan_d.nutrition_summary
            else None
        ),
        budget_summary=(
            DailyBudgetSummaryDTO(
                budget_envelope_idr=plan_d.budget_summary.budget_envelope_idr,
                planned_cost_idr=plan_d.budget_summary.planned_cost_idr,
                remaining_after_plan_idr=plan_d.budget_summary.remaining_after_plan_idr,
                cost_completeness=plan_d.budget_summary.cost_completeness,
                price_confidence=plan_d.budget_summary.price_confidence,
                uses_stale_prices=plan_d.budget_summary.uses_stale_prices,
                budget_source=plan_d.budget_summary.budget_source,
            )
            if plan_d.budget_summary
            else None
        ),
        meal_entries=converted_entries,
        warnings=[],
        provenance=(
            DailyPlanProvenanceDTO(
                assessment_snapshot_id=plan_d.provenance.assessment_snapshot_id,
                nutrition_policy_version=plan_d.provenance.nutrition_policy_version,
                meal_structure_policy_version=plan_d.provenance.meal_structure_policy_version,
                food_candidate_policy_version=plan_d.provenance.food_candidate_policy_version,
                price_policy_version=plan_d.provenance.price_policy_version,
                budget_selection_policy_version=plan_d.provenance.budget_selection_policy_version,
                assembly_policy_version=plan_d.provenance.assembly_policy_version,
            )
            if plan_d.provenance
            else DailyPlanProvenanceDTO(
                nutrition_policy_version="NUTRITION_V0_1",
                meal_structure_policy_version="MEAL_STRUCTURE_TRANSITION_V01",
                food_candidate_policy_version="FOOD_CANDIDATE_P1_2",
                price_policy_version="PRICE_KNOWLEDGE_P1_3",
                budget_selection_policy_version="BUDGET_SELECTION_P1_4",
                assembly_policy_version="DAILY_NUTRITION_PLAN_ASSEMBLY_P1_5",
            )
        ),
        policy_versions=plan_d.policy_versions,
    )

    checkin_dtos = [
        MealCheckinDTO(
            plan_id=c.plan_id,
            logical_day_id=c.logical_day_id,
            slot_id=c.slot_id,
            status=c.status,
            meal_occurred_at=c.meal_occurred_at,
            checked_in_at=c.checked_in_at or datetime.now(timezone.utc).isoformat(),
            actual_items=[
                ActualFoodItemDTO(
                    food_item_id=it.food_item_id,
                    display_name=it.display_name,
                    serving_id=it.serving_id,
                    serving_name=it.serving_name,
                    grams=it.grams,
                    quantity=it.quantity,
                    energy_kcal=it.energy_kcal,
                    protein_g=it.protein_g,
                    fat_g=it.fat_g,
                    carbohydrate_g=it.carbohydrate_g,
                    source_type=it.source_type,
                    certainty=it.certainty,
                )
                for it in c.actual_items
            ],
            actual_spend_idr=c.actual_spend_idr,
            deviation_reason=c.deviation_reason,
            notes=c.notes,
            certainty=c.certainty,
        )
        for c in payload.checkins
    ]

    unplanned_dtos = [
        UnplannedIntakeDTO(
            logical_day_id=u.logical_day_id,
            occurred_at=u.occurred_at,
            recorded_at=u.recorded_at or datetime.now(timezone.utc).isoformat(),
            items=[
                ActualFoodItemDTO(
                    food_item_id=it.food_item_id,
                    display_name=it.display_name,
                    serving_id=it.serving_id,
                    serving_name=it.serving_name,
                    grams=it.grams,
                    quantity=it.quantity,
                    energy_kcal=it.energy_kcal,
                    protein_g=it.protein_g,
                    fat_g=it.fat_g,
                    carbohydrate_g=it.carbohydrate_g,
                    source_type=it.source_type,
                    certainty=it.certainty,
                )
                for it in u.items
            ],
            actual_spend_idr=u.actual_spend_idr,
            reason=u.reason,
            notes=u.notes,
        )
        for u in payload.unplanned_intakes
    ]

    adherence_dto = evaluate_daily_nutrition_adherence(plan_dto, checkin_dtos, unplanned_dtos)
    return adherence_dto
