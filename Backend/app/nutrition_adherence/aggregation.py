from typing import List, Optional
from app.nutrition_adherence.constants import (
    ReportingCompleteness,
    MealCheckinStatus,
)
from app.nutrition_adherence.models import (
    MealCheckinDTO,
    UnplannedIntakeDTO,
    ActualNutritionSummaryDTO,
    ActualSpendSummaryDTO,
)
from app.daily_nutrition_plan.constants import MacroCompleteness
from app.price_knowledge.constants import CostCompleteness


def aggregate_actual_nutrition(
    checkins: List[MealCheckinDTO],
    unplanned_intakes: List[UnplannedIntakeDTO],
) -> ActualNutritionSummaryDTO:
    """
    Aggregates observed actual energy and nutrients across planned checkins and unplanned intakes.
    Invariant: unknown != 0. If any item is unresolved, completeness is PARTIAL.
    """
    total_energy = 0.0
    total_protein = 0.0
    total_fat = 0.0
    total_carbs = 0.0
    macro_partial = False
    resolved_count = 0
    unresolved_count = 0

    all_items = []
    for chk in checkins:
        if chk.status != MealCheckinStatus.SKIPPED:
            all_items.extend(chk.actual_items)
    for unp in unplanned_intakes:
        all_items.extend(unp.items)

    if not all_items:
        # If all reported meals were SKIPPED
        all_skipped = all(chk.status == MealCheckinStatus.SKIPPED for chk in checkins) if checkins else False
        if all_skipped:
            return ActualNutritionSummaryDTO(
                energy_kcal=0.0,
                protein_g=0.0,
                fat_g=0.0,
                carbohydrate_g=0.0,
                completeness=MacroCompleteness.COMPLETE,
                resolved_item_count=0,
                unresolved_item_count=0,
            )
        return ActualNutritionSummaryDTO(
            energy_kcal=None,
            protein_g=None,
            fat_g=None,
            carbohydrate_g=None,
            completeness=MacroCompleteness.PARTIAL,
            resolved_item_count=0,
            unresolved_item_count=0,
        )

    for item in all_items:
        if item.energy_kcal is not None:
            resolved_count += 1
            total_energy += item.energy_kcal
        else:
            unresolved_count += 1
            macro_partial = True

        if item.protein_g is not None:
            total_protein += item.protein_g
        else:
            macro_partial = True

        if item.fat_g is not None:
            total_fat += item.fat_g
        else:
            macro_partial = True

        if item.carbohydrate_g is not None:
            total_carbs += item.carbohydrate_g
        else:
            macro_partial = True

    return ActualNutritionSummaryDTO(
        energy_kcal=round(total_energy, 1) if not macro_partial else round(total_energy, 1),
        protein_g=round(total_protein, 1) if not macro_partial else None,
        fat_g=round(total_fat, 1) if not macro_partial else None,
        carbohydrate_g=round(total_carbs, 1) if not macro_partial else None,
        completeness=MacroCompleteness.PARTIAL if macro_partial else MacroCompleteness.COMPLETE,
        resolved_item_count=resolved_count,
        unresolved_item_count=unresolved_count,
    )


def aggregate_actual_spend(
    checkins: List[MealCheckinDTO],
    unplanned_intakes: List[UnplannedIntakeDTO],
) -> ActualSpendSummaryDTO:
    """
    Aggregates observed actual spend across checkins and unplanned intakes.
    """
    total_spend = 0
    reported_count = 0
    missing_count = 0

    for chk in checkins:
        if chk.status != MealCheckinStatus.NOT_REPORTED:
            reported_count += 1
            if chk.actual_spend_idr is not None:
                total_spend += chk.actual_spend_idr
            else:
                missing_count += 1

    for unp in unplanned_intakes:
        reported_count += 1
        if unp.actual_spend_idr is not None:
            total_spend += unp.actual_spend_idr
        else:
            missing_count += 1

    if reported_count == 0:
        completeness = CostCompleteness.UNAVAILABLE
        known_spend = None
    elif missing_count == 0:
        completeness = CostCompleteness.COMPLETE
        known_spend = total_spend
    elif total_spend > 0:
        completeness = CostCompleteness.PARTIAL
        known_spend = total_spend
    else:
        completeness = CostCompleteness.UNAVAILABLE
        known_spend = None

    return ActualSpendSummaryDTO(
        known_spend_idr=known_spend,
        completeness=completeness,
        reported_meal_count=reported_count,
        missing_spend_count=missing_count,
    )


def derive_reporting_completeness(
    reported_slot_count: int,
    total_planned_slots: int,
) -> ReportingCompleteness:
    if total_planned_slots == 0:
        return ReportingCompleteness.NONE
    if reported_slot_count >= total_planned_slots:
        return ReportingCompleteness.COMPLETE
    elif reported_slot_count > 0:
        return ReportingCompleteness.PARTIAL
    return ReportingCompleteness.NONE
