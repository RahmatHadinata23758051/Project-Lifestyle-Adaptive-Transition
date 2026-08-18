from typing import List
from app.daily_nutrition_plan.constants import (
    DailyPlanWarningCode,
    DailyPlanWarningSeverity,
    MacroCompleteness,
)
from app.daily_nutrition_plan.models import (
    DailyPlanWarningDTO,
    DailyNutritionSummaryDTO,
    DailyBudgetSummaryDTO,
)
from app.price_knowledge.constants import PriceConfidence


def derive_daily_plan_warnings(
    nutrition_summary: DailyNutritionSummaryDTO,
    budget_summary: DailyBudgetSummaryDTO,
    search_truncated: bool = False,
) -> List[DailyPlanWarningDTO]:
    """
    Produces deterministic structured warnings for the assembled Daily Nutrition Plan.
    """
    warnings: List[DailyPlanWarningDTO] = []

    if budget_summary.uses_stale_prices:
        warnings.append(
            DailyPlanWarningDTO(
                code=DailyPlanWarningCode.STALE_PRICE_USED,
                severity=DailyPlanWarningSeverity.CAUTION,
                message="One or more meal cost estimates rely on older historical price observations.",
            )
        )

    if budget_summary.price_confidence == PriceConfidence.LOW:
        warnings.append(
            DailyPlanWarningDTO(
                code=DailyPlanWarningCode.LOW_CONFIDENCE_PRICE,
                severity=DailyPlanWarningSeverity.CAUTION,
                message="Budget selection includes items with low price confidence (e.g. province-level fallback or sparse observations).",
            )
        )

    if nutrition_summary.near_match_slot_count > 0:
        warnings.append(
            DailyPlanWarningDTO(
                code=DailyPlanWarningCode.NUTRITION_NEAR_MATCH,
                severity=DailyPlanWarningSeverity.INFO,
                message=f"{nutrition_summary.near_match_slot_count} meal slot(s) use near-match candidate portions to fit budget and role constraints.",
            )
        )

    if search_truncated:
        warnings.append(
            DailyPlanWarningDTO(
                code=DailyPlanWarningCode.SEARCH_SPACE_TRUNCATED,
                severity=DailyPlanWarningSeverity.INFO,
                message="Candidate search limit was reached during budget optimization. Best feasible selection found within evaluated space.",
            )
        )

    if nutrition_summary.macro_completeness == MacroCompleteness.PARTIAL:
        warnings.append(
            DailyPlanWarningDTO(
                code=DailyPlanWarningCode.PARTIAL_MACRO_DATA,
                severity=DailyPlanWarningSeverity.INFO,
                message="Some food items have incomplete macronutrient profiles in food composition reference data.",
            )
        )

    return warnings
