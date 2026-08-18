from typing import Dict, List, Optional, Any
from app.daily_nutrition_plan.constants import (
    DailyPlanStatus,
    DailyPlanPolicy,
)
from app.meal_structure.constants import MealSlotType
from app.daily_nutrition_plan.models import (
    DailyNutritionPlanAssemblyInputDTO,
    DailyNutritionPlanDTO,
    DailyMealEntryDTO,
    DailyMealFoodItemDTO,
)
from app.daily_nutrition_plan.validation import (
    validate_nutrition_eligibility,
    validate_meal_schedule_feasibility,
    validate_budget_selection_status,
    validate_slot_integrity,
    validate_cost_consistency,
)
from app.daily_nutrition_plan.ordering import order_meal_entries_by_waking_day
from app.daily_nutrition_plan.aggregation import (
    aggregate_daily_nutrition,
    aggregate_daily_budget,
)
from app.daily_nutrition_plan.warnings import derive_daily_plan_warnings
from app.daily_nutrition_plan.provenance import (
    build_daily_plan_provenance,
    generate_deterministic_plan_id,
)
from app.price_knowledge.constants import PriceConfidence, CostCompleteness


def assemble_daily_nutrition_plan(
    input_dto: DailyNutritionPlanAssemblyInputDTO,
) -> DailyNutritionPlanDTO:
    """
    Pure zero-I/O Daily Nutrition Plan Assembler (DAILY_NUTRITION_PLAN_ASSEMBLY_P1_5).
    Assembles a coherent user-facing daily nutrition plan from already validated upstream domain outputs.
    Does NOT recalculate calories, schedule, prices, or budget selection.
    """
    provenance = build_daily_plan_provenance(
        policy_versions=input_dto.policy_versions,
        assessment_snapshot_id=input_dto.assessment_snapshot_id,
    )
    policy_versions_dict = {
        "nutrition_policy_version": provenance.nutrition_policy_version,
        "meal_structure_policy_version": provenance.meal_structure_policy_version,
        "food_candidate_policy_version": provenance.food_candidate_policy_version,
        "price_policy_version": provenance.price_policy_version,
        "budget_selection_policy_version": provenance.budget_selection_policy_version,
        "assembly_policy_version": provenance.assembly_policy_version,
    }

    # 1. Nutrition Eligibility Gate
    nut_gate = validate_nutrition_eligibility(input_dto.nutrition_eligibility_status)
    if nut_gate is not None:
        plan_id = generate_deterministic_plan_id(input_dto.logical_day_id, [], provenance)
        return DailyNutritionPlanDTO(
            plan_id=plan_id,
            date=input_dto.date,
            logical_day_id=input_dto.logical_day_id,
            status=nut_gate,
            nutrition_summary=None,
            budget_summary=None,
            meal_entries=[],
            warnings=[],
            provenance=provenance,
            policy_versions=policy_versions_dict,
        )

    # 2. Meal Schedule Feasibility Gate
    sched = input_dto.meal_schedule
    sched_status = (
        getattr(sched, "feasibility", None)
        or getattr(sched, "status", None)
        or (sched.get("feasibility") if isinstance(sched, dict) else None)
        or (sched.get("status") if isinstance(sched, dict) else "FEASIBLE")
    )
    sched_gate = validate_meal_schedule_feasibility(str(sched_status))
    if sched_gate is not None:
        plan_id = generate_deterministic_plan_id(input_dto.logical_day_id, [], provenance)
        return DailyNutritionPlanDTO(
            plan_id=plan_id,
            date=input_dto.date,
            logical_day_id=input_dto.logical_day_id,
            status=sched_gate,
            nutrition_summary=None,
            budget_summary=None,
            meal_entries=[],
            warnings=[],
            provenance=provenance,
            policy_versions=policy_versions_dict,
        )

    # 3. Budget Selection Gate
    bs_result = input_dto.budget_selection_result
    bs_gate = validate_budget_selection_status(bs_result.status)
    if bs_gate is not None:
        plan_id = generate_deterministic_plan_id(input_dto.logical_day_id, [], provenance)
        return DailyNutritionPlanDTO(
            plan_id=plan_id,
            date=input_dto.date,
            logical_day_id=input_dto.logical_day_id,
            status=bs_gate,
            nutrition_summary=None,
            budget_summary=None,
            meal_entries=[],
            warnings=[],
            provenance=provenance,
            policy_versions=policy_versions_dict,
        )

    # 4. Logical Day Alignment Check
    sched_day_id = getattr(sched, "logical_day_id", None) or (sched.get("logical_day_id") if isinstance(sched, dict) else input_dto.logical_day_id)
    if sched_day_id != input_dto.logical_day_id or bs_result.logical_day_id != input_dto.logical_day_id:
        plan_id = generate_deterministic_plan_id(input_dto.logical_day_id, [], provenance)
        return DailyNutritionPlanDTO(
            plan_id=plan_id,
            date=input_dto.date,
            logical_day_id=input_dto.logical_day_id,
            status=DailyPlanStatus.INFEASIBLE,
            nutrition_summary=None,
            budget_summary=None,
            meal_entries=[],
            warnings=[],
            provenance=provenance,
            policy_versions=policy_versions_dict,
        )

    # 5. Extract active slots from schedule
    slots_data = getattr(sched, "slots", None) or (sched.get("slots", []) if isinstance(sched, dict) else [])
    active_slot_map = {}
    active_slot_ids = []
    for s in slots_data:
        s_id = getattr(s, "slot_id", None) or (s.get("slot_id") if isinstance(s, dict) else None)
        if s_id:
            active_slot_map[s_id] = s
            active_slot_ids.append(s_id)

    # 6. Slot Integrity Check
    slot_valid, slot_err = validate_slot_integrity(active_slot_ids, input_dto.selected_candidates_by_slot)
    if not slot_valid:
        plan_id = generate_deterministic_plan_id(input_dto.logical_day_id, [], provenance)
        return DailyNutritionPlanDTO(
            plan_id=plan_id,
            date=input_dto.date,
            logical_day_id=input_dto.logical_day_id,
            status=DailyPlanStatus.INFEASIBLE,
            nutrition_summary=None,
            budget_summary=None,
            meal_entries=[],
            warnings=[],
            provenance=provenance,
            policy_versions=policy_versions_dict,
        )

    # 7. Cost Consistency Check
    bs_total = bs_result.selected_combination.total_estimated_cost_idr if bs_result.selected_combination else None
    cost_valid, cost_err = validate_cost_consistency(
        input_dto.selected_candidates_by_slot,
        input_dto.candidate_costs_by_candidate_id,
        bs_total,
    )
    if not cost_valid:
        plan_id = generate_deterministic_plan_id(input_dto.logical_day_id, [], provenance)
        return DailyNutritionPlanDTO(
            plan_id=plan_id,
            date=input_dto.date,
            logical_day_id=input_dto.logical_day_id,
            status=DailyPlanStatus.INFEASIBLE,
            nutrition_summary=None,
            budget_summary=None,
            meal_entries=[],
            warnings=[],
            provenance=provenance,
            policy_versions=policy_versions_dict,
        )

    # 8. Assemble Meal Entries
    meal_entries: List[DailyMealEntryDTO] = []
    selected_candidate_ids: List[str] = []

    for slot_id in active_slot_ids:
        slot_info = active_slot_map[slot_id]
        cand = input_dto.selected_candidates_by_slot[slot_id]
        selected_candidate_ids.append(cand.candidate_id)
        cost_dto = input_dto.candidate_costs_by_candidate_id.get(cand.candidate_id)

        raw_stype = getattr(slot_info, "slot_type", None) or (slot_info.get("slot_type") if isinstance(slot_info, dict) else None) or MealSlotType.MAIN_MEAL
        if isinstance(raw_stype, str):
            try:
                s_type = MealSlotType(raw_stype)
            except ValueError:
                s_type = MealSlotType.MAIN_MEAL
        else:
            s_type = raw_stype

        sched_time = (
            getattr(slot_info, "preferred_time", None)
            or getattr(slot_info, "target_time", None)
            or getattr(slot_info, "scheduled_time", None)
            or (slot_info.get("preferred_time") or slot_info.get("target_time") or slot_info.get("scheduled_time") if isinstance(slot_info, dict) else "12:00")
        )
        earliest_t = getattr(slot_info, "earliest_time", None) or (slot_info.get("earliest_time") if isinstance(slot_info, dict) else None)
        latest_t = getattr(slot_info, "latest_time", None) or (slot_info.get("latest_time") if isinstance(slot_info, dict) else None)

        food_items: List[DailyMealFoodItemDTO] = [
            DailyMealFoodItemDTO(
                food_item_id=item.food_item_id,
                canonical_name=item.canonical_name,
                role=item.role,
                serving_name=item.serving_name,
                grams=item.grams,
                energy_kcal=item.energy_kcal,
                protein_g=item.protein_g,
                fat_g=item.fat_g,
                carbohydrate_g=item.carbohydrate_g,
            )
            for item in cand.items
        ]

        entry = DailyMealEntryDTO(
            slot_id=slot_id,
            slot_type=s_type,
            scheduled_time=sched_time,
            earliest_time=earliest_t,
            latest_time=latest_t,
            candidate_id=cand.candidate_id,
            foods=food_items,
            planned_energy_kcal=cand.total_energy_kcal,
            planned_protein_g=cand.total_protein_g,
            planned_fat_g=cand.total_fat_g,
            planned_carbohydrate_g=cand.total_carbohydrate_g,
            nutrition_fit_status=cand.match_status,
            estimated_cost_idr=cost_dto.estimated_cost_idr if cost_dto else None,
            cost_completeness=cost_dto.cost_completeness if cost_dto else CostCompleteness.UNAVAILABLE,
            price_confidence=cost_dto.confidence if cost_dto else PriceConfidence.UNKNOWN,
            uses_stale_prices=cost_dto.uses_stale_prices if cost_dto else False,
            location_context=None,
            preparation_context=cand.preparation_complexity,
            explanations=cand.explanations,
        )
        meal_entries.append(entry)

    # 9. Chronological Waking-Day Ordering
    wake_time = getattr(sched, "wake_time", None) or (sched.get("wake_time") if isinstance(sched, dict) else None)
    ordered_entries = order_meal_entries_by_waking_day(meal_entries, wake_time)

    # 10. Aggregations
    nutrition_summary = aggregate_daily_nutrition(input_dto.selected_candidates_by_slot, input_dto.target_energy_kcal)
    budget_source = bs_result.selected_combination.selections[active_slot_ids[0]].budget_status if (bs_result.selected_combination and active_slot_ids) else None
    budget_summary = aggregate_daily_budget(
        candidates_by_slot=input_dto.selected_candidates_by_slot,
        candidate_costs_by_candidate_id=input_dto.candidate_costs_by_candidate_id,
        budget_envelope_idr=bs_result.budget_envelope_idr,
    )

    # 11. Warnings & Status
    warnings = derive_daily_plan_warnings(
        nutrition_summary=nutrition_summary,
        budget_summary=budget_summary,
        search_truncated=bs_result.search_truncated,
    )

    final_status = DailyPlanStatus.READY_WITH_WARNINGS if warnings else DailyPlanStatus.READY

    plan_id = generate_deterministic_plan_id(input_dto.logical_day_id, selected_candidate_ids, provenance)

    return DailyNutritionPlanDTO(
        plan_id=plan_id,
        date=input_dto.date,
        logical_day_id=input_dto.logical_day_id,
        status=final_status,
        nutrition_summary=nutrition_summary,
        budget_summary=budget_summary,
        meal_entries=ordered_entries,
        warnings=warnings,
        provenance=provenance,
        policy_versions=policy_versions_dict,
    )
