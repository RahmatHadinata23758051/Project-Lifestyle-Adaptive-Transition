from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.repositories.assessment_repository import AssessmentRepository
from app.assessment.field_registry import calculate_age_from_birthdate
from app.nutrition.constants import (
    NutritionPolicy,
    CalculationSource,
    PALAssessmentStatus,
    PALResolutionMethod,
)
from app.nutrition.eligibility import NutritionEligibilityEvaluator
from app.nutrition.pal import PALClassifier
from app.nutrition.energy import EnergyCalculator
from app.nutrition.macros import MacroCalculator
from app.schemas.nutrition import (
    NutritionCalculationInput,
    NutritionCalculationResultResponse,
    NutritionEligibilityResponse,
    NutritionEnergyResponse,
    NutritionMacroResponse,
)

router = APIRouter()


@router.post(
    "/calculate",
    response_model=NutritionCalculationResultResponse,
    summary="Preview deterministic energy requirement and macro targets based on 2023 DRI EER (Live Preview)",
)
def calculate_nutrition_targets(
    payload: Optional[NutritionCalculationInput] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Live Preview endpoint for nutrition energy & macro targets.
    NOTE: This endpoint is for live preview calculation and does not create an official immutable nutrition plan.
    """
    known_data = AssessmentRepository.get_user_known_data(db, user_id=current_user.id)
    payload = payload or NutritionCalculationInput()

    # 1. Resolve Profile & Body Data
    birth_date_str = known_data.get("profile.birth_date")
    derived_age = calculate_age_from_birthdate(birth_date_str) if birth_date_str else None
    age = payload.age if payload.age is not None else derived_age

    sex = payload.sex or known_data.get("profile.sex")
    height_cm = payload.height_cm if payload.height_cm is not None else known_data.get("profile.height_cm")
    weight_kg = payload.current_weight_kg if payload.current_weight_kg is not None else known_data.get("nutrition.current_weight_kg")
    
    # IDR Integer Semantics
    raw_budget = payload.weekly_food_budget if payload.weekly_food_budget is not None else known_data.get("nutrition.weekly_food_budget")
    weekly_budget: Optional[int] = int(round(raw_budget)) if raw_budget is not None else None

    # 2. Evaluate Conservative Eligibility Safety Gate
    eligibility_result = NutritionEligibilityEvaluator.evaluate(
        age=age,
        is_pregnant_or_lactating=payload.is_pregnant_or_lactating,
        has_prescribed_medical_diet=payload.has_prescribed_medical_diet,
        has_eating_disorder_history=payload.has_eating_disorder_history,
        has_unexplained_weight_loss=payload.has_unexplained_weight_loss,
        has_major_metabolic_condition=payload.has_major_metabolic_condition,
    )

    eligibility_response = NutritionEligibilityResponse(
        status=eligibility_result.status,
        is_eligible=eligibility_result.is_eligible,
        reasons=eligibility_result.reasons,
        guidance=eligibility_result.guidance,
    )

    # 3. Resolve PAL (Zero-Guessing Principle)
    pal_input = payload.confirmed_pal_category or payload.pal_category or known_data.get("nutrition.pal_category")
    pal_result = PALClassifier.classify(confirmed_pal_category=pal_input)

    # 4. Check Calculation Readiness vs Plan Readiness
    missing_calc: List[str] = []
    if age is None:
        missing_calc.append("age")
    if sex is None:
        missing_calc.append("sex")
    if height_cm is None:
        missing_calc.append("height_cm")
    if weight_kg is None:
        missing_calc.append("current_weight_kg")
    if pal_result.status != PALAssessmentStatus.RESOLVED:
        missing_calc.append("pal_category")

    missing_plan: List[str] = list(missing_calc)
    if weekly_budget is None:
        missing_plan.append("weekly_food_budget")

    calculation_ready = eligibility_result.is_eligible and (len(missing_calc) == 0)
    plan_ready = calculation_ready and (len(missing_plan) == 0)

    # If calculation is not ready, return early with null energy/macros
    if not calculation_ready:
        explanation = (
            eligibility_result.guidance
            if not eligibility_result.is_eligible
            else f"Perhitungan kebutuhan energi belum dapat dilakukan. Data yang diperlukan belum lengkap: {', '.join(missing_calc)}."
        )
        return NutritionCalculationResultResponse(
            user_id=current_user.id,
            calculation_source=CalculationSource.LIVE_PREVIEW,
            energy_method=NutritionPolicy.EER_METHOD,
            pal_resolution_method=pal_result.resolution_method,
            policy_version=NutritionPolicy.VERSION,
            assessment_snapshot_id=None,
            calculation_ready=False,
            plan_ready=False,
            missing_for_calculation=missing_calc,
            missing_for_plan=missing_plan,
            eligibility=eligibility_response,
            energy=None,
            macros=None,
            weekly_food_budget=weekly_budget,
            currency="IDR",
            bmi_context=None,
            explanation=explanation,
        )

    # 5. Deterministic 2023 DRI Energy & Surplus Calculation
    assert pal_result.category is not None
    energy_result = EnergyCalculator.calculate_weight_gain_target(
        sex=str(sex),
        age=int(age),
        height_cm=float(height_cm),
        weight_kg=float(weight_kg),
        pal=pal_result.category,
        pal_reason=pal_result.reason,
        starting_surplus_kcal=payload.starting_surplus_kcal,
    )

    # 6. Macronutrient References & Guardrails
    macro_result = MacroCalculator.calculate_macro_reference(
        weight_kg=float(weight_kg),
        target_kcal=energy_result.target_kcal,
    )

    # 7. BMI Context
    height_m = float(height_cm) / 100.0
    bmi = round(float(weight_kg) / (height_m * height_m), 1)

    surplus_info = (
        f"surplus awal bertahap disesuaikan: +{energy_result.applied_surplus_kcal} kcal (dibatasi dari permintaan {energy_result.requested_surplus_kcal} kcal)"
        if energy_result.surplus_was_adjusted
        else f"surplus awal bertahap: +{energy_result.applied_surplus_kcal} kcal"
    )

    explanation = (
        f"Kebutuhan energi harian diestimasi sebesar ~{energy_result.rounded_display_kcal:,} kcal "
        f"menggunakan standar ilmiah 2023 DRI EER (estimasi maintenance: {energy_result.maintenance_estimate_kcal:.0f} kcal + "
        f"{surplus_info}). "
        f"Target ini adalah estimasi awal yang akan dipantau bersama tren berat badan nyata."
    )

    return NutritionCalculationResultResponse(
        user_id=current_user.id,
        calculation_source=CalculationSource.LIVE_PREVIEW,
        energy_method=NutritionPolicy.EER_METHOD,
        pal_resolution_method=pal_result.resolution_method,
        policy_version=NutritionPolicy.VERSION,
        assessment_snapshot_id=None,
        calculation_ready=True,
        plan_ready=plan_ready,
        missing_for_calculation=[],
        missing_for_plan=missing_plan,
        eligibility=eligibility_response,
        energy=NutritionEnergyResponse(
            method=energy_result.method,
            policy_version=energy_result.policy_version,
            pal_category=energy_result.pal_category,
            pal_reason=energy_result.pal_reason,
            maintenance_estimate_kcal=energy_result.maintenance_estimate_kcal,
            requested_surplus_kcal=energy_result.requested_surplus_kcal,
            applied_surplus_kcal=energy_result.applied_surplus_kcal,
            surplus_was_adjusted=energy_result.surplus_was_adjusted,
            target_kcal=energy_result.target_kcal,
            rounded_display_kcal=energy_result.rounded_display_kcal,
        ),
        macros=NutritionMacroResponse(
            protein_rda_reference_g=macro_result.protein_rda_reference_g,
            training_target_g=macro_result.training_target_g,
            amdr_percentages=macro_result.amdr_percentages,
            amdr_gram_ranges=macro_result.amdr_gram_ranges,
        ),
        weekly_food_budget=weekly_budget,
        currency="IDR",
        bmi_context=bmi,
        explanation=explanation,
    )
