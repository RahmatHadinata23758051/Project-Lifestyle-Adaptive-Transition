from typing import List, Dict, Optional
from app.nutrition_adherence.constants import (
    MealCheckinStatus,
    MealCompletionState,
    FoodChoiceAdherence,
    TimingAdherenceStatus,
    EnergyAdherenceStatus,
    AdherencePolicy,
)
from app.nutrition_adherence.models import (
    DailyNutritionAdherenceDTO,
    SlotAdherenceDTO,
    MealCheckinDTO,
    UnplannedIntakeDTO,
)
from app.daily_nutrition_plan.models import DailyNutritionPlanDTO
from app.nutrition_adherence.timing import evaluate_timing_adherence
from app.nutrition_adherence.meal_completion import (
    derive_meal_completion_state,
    derive_food_choice_adherence,
    evaluate_energy_adherence,
)
from app.nutrition_adherence.aggregation import (
    aggregate_actual_nutrition,
    aggregate_actual_spend,
    derive_reporting_completeness,
)
from app.nutrition_adherence.explanations import generate_adherence_explanations


def evaluate_daily_nutrition_adherence(
    plan: DailyNutritionPlanDTO,
    checkins: List[MealCheckinDTO],
    unplanned_intakes: Optional[List[UnplannedIntakeDTO]] = None,
) -> DailyNutritionAdherenceDTO:
    """
    Pure zero-I/O Daily Nutrition Adherence Evaluator (NUTRITION_ADHERENCE_V01).
    Evaluates multi-dimensional adherence evidence by comparing actual observations
    against the confirmed daily nutrition plan without punitive scores.
    """
    unplanned = unplanned_intakes or []
    checkins_by_slot: Dict[str, MealCheckinDTO] = {c.slot_id: c for c in checkins}

    slot_adherences: List[SlotAdherenceDTO] = []
    reported_slot_count = 0

    planned_cost = plan.budget_summary.planned_cost_idr if plan.budget_summary else None
    planned_energy = plan.nutrition_summary.planned_energy_kcal if plan.nutrition_summary else 0.0

    for entry in plan.meal_entries:
        chk = checkins_by_slot.get(entry.slot_id)
        if chk is not None:
            reported_slot_count += 1
            comp_state = derive_meal_completion_state(chk.status)
            food_adh = derive_food_choice_adherence(chk.status)
            timing_adh = evaluate_timing_adherence(chk.meal_occurred_at, entry.earliest_time, entry.latest_time)

            if chk.status == MealCheckinStatus.SKIPPED:
                act_energy = 0.0
            else:
                resolved_energies = [i.energy_kcal for i in chk.actual_items if i.energy_kcal is not None]
                has_unresolved = any(i.energy_kcal is None for i in chk.actual_items)
                if has_unresolved or not chk.actual_items:
                    act_energy = sum(resolved_energies) if resolved_energies else None
                else:
                    act_energy = sum(resolved_energies)

            energy_adh = evaluate_energy_adherence(act_energy, entry.planned_energy_kcal)

            slot_adherences.append(
                SlotAdherenceDTO(
                    slot_id=entry.slot_id,
                    slot_type=entry.slot_type.value if hasattr(entry.slot_type, "value") else str(entry.slot_type),
                    scheduled_time=entry.scheduled_time,
                    meal_completion=comp_state,
                    timing_adherence=timing_adh,
                    food_choice_adherence=food_adh,
                    energy_adherence=energy_adh,
                    planned_energy_kcal=entry.planned_energy_kcal,
                    actual_energy_kcal=act_energy,
                    planned_cost_idr=entry.estimated_cost_idr,
                    actual_spend_idr=chk.actual_spend_idr,
                    deviation_reason=chk.deviation_reason,
                    explanations=[],
                )
            )
        else:
            # Slot not checked in
            slot_adherences.append(
                SlotAdherenceDTO(
                    slot_id=entry.slot_id,
                    slot_type=entry.slot_type.value if hasattr(entry.slot_type, "value") else str(entry.slot_type),
                    scheduled_time=entry.scheduled_time,
                    meal_completion=MealCompletionState.NOT_REPORTED,
                    timing_adherence=TimingAdherenceStatus.UNKNOWN,
                    food_choice_adherence=FoodChoiceAdherence.NOT_REPORTED,
                    energy_adherence=EnergyAdherenceStatus.UNKNOWN,
                    planned_energy_kcal=entry.planned_energy_kcal,
                    actual_energy_kcal=None,
                    planned_cost_idr=entry.estimated_cost_idr,
                    actual_spend_idr=None,
                    deviation_reason=None,
                    explanations=["Meal slot was not reported."],
                )
            )

    reporting_completeness = derive_reporting_completeness(reported_slot_count, len(plan.meal_entries))
    actual_nut_summary = aggregate_actual_nutrition(checkins, unplanned)
    actual_spend_summary = aggregate_actual_spend(checkins, unplanned)

    energy_diff = (
        round(actual_nut_summary.energy_kcal - planned_energy, 1)
        if actual_nut_summary.energy_kcal is not None
        else None
    )

    explanations = generate_adherence_explanations(slot_adherences, unplanned, reporting_completeness)

    return DailyNutritionAdherenceDTO(
        logical_day_id=plan.logical_day_id,
        date=plan.date,
        plan_id=plan.plan_id,
        reporting_completeness=reporting_completeness,
        planned_energy_kcal=planned_energy,
        actual_nutrition_summary=actual_nut_summary,
        energy_difference_kcal=energy_diff,
        planned_cost_idr=planned_cost,
        actual_spend_summary=actual_spend_summary,
        slot_adherences=slot_adherences,
        unplanned_intakes=unplanned,
        explanations=explanations,
        policy_version=AdherencePolicy.VERSION,
    )
