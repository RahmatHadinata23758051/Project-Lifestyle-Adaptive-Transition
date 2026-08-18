from typing import List
from app.nutrition_adaptation.constants import DayEvidenceQuality, AdaptationEvaluationPolicy
from app.nutrition_adherence.constants import ReportingCompleteness
from app.daily_nutrition_plan.constants import MacroCompleteness, DailyPlanStatus
from app.nutrition_adaptation.models import (
    NutritionEvidenceDayDTO,
    WeightObservationDTO,
    EvidenceWindowDTO,
)


def classify_day_evidence_quality(
    plan_status: DailyPlanStatus,
    reporting_completeness: ReportingCompleteness,
    nutrition_completeness: MacroCompleteness,
) -> DayEvidenceQuality:
    """
    Evaluates the usable quality of a single logical day's adherence evidence.
    """
    if plan_status in (DailyPlanStatus.NOT_ELIGIBLE, DailyPlanStatus.INFEASIBLE):
        return DayEvidenceQuality.UNUSABLE

    if reporting_completeness == ReportingCompleteness.NONE:
        return DayEvidenceQuality.UNUSABLE

    if (
        reporting_completeness == ReportingCompleteness.COMPLETE
        and nutrition_completeness == MacroCompleteness.COMPLETE
    ):
        return DayEvidenceQuality.USABLE

    return DayEvidenceQuality.PARTIAL


def build_evidence_window(
    days: List[NutritionEvidenceDayDTO],
    weight_measurements: List[WeightObservationDTO],
) -> EvidenceWindowDTO:
    """
    Derives evidence window span and counts.
    """
    if not days:
        return EvidenceWindowDTO(
            start_date="",
            end_date="",
            total_days=0,
            usable_adherence_days=0,
            weight_measurement_count=len(weight_measurements),
        )

    sorted_days = sorted(days, key=lambda d: d.date)
    start_date = sorted_days[0].date
    end_date = sorted_days[-1].date
    total_days = len(sorted_days)
    usable_days = sum(1 for d in days if d.evidence_quality == DayEvidenceQuality.USABLE)

    return EvidenceWindowDTO(
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        usable_adherence_days=usable_days,
        weight_measurement_count=len(weight_measurements),
    )
