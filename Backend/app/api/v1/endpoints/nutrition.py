from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user, AuthenticatedUser
from app.repositories.assessment_repository import AssessmentRepository
from app.assessment.field_registry import calculate_age_from_birthdate
from app.nutrition.constants import NutritionPolicy
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
    summary="Preview deterministic energy requirement and macro targets based on 2023 DRI EER",
)
def calculate_nutrition_targets(
    payload: Optional[NutritionCalculationInput] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    known_data = AssessmentRepository.get_user_known_data(db, user_id=current_user.id)
    payload = payload or NutritionCalculationInput()

    # 1. Resolve Profile & Body Data
    birth_date_str = known_data.get("profile.birth_date")
    derived_age = calculate_age_from_birthdate(birth_date_str) if birth_date_str else None
    age = payload.age if payload.age is not None else derived_age

    sex = payload.sex or known_data.get("profile.sex")
    height_cm = payload.height_cm if payload.height_cm is not None else known_data.get("profile.height_cm")
    weight_kg = payload.current_weight_kg if payload.current_weight_kg is not None else known_data.get("nutrition.current_weight_kg")
    weekly_budget = known_data.get("nutrition.weekly_food_budget")

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

    if not eligibility_result.is_eligible:
        return NutritionCalculationResultResponse(
            user_id=current_user.id,
            policy_version=NutritionPolicy.VERSION,
            eligibility=eligibility_response,
            energy=None,
            macros=None,
            weekly_food_budget=weekly_budget,
            currency="IDR",
            bmi_context=None,
            explanation=eligibility_result.guidance or "Perhitungan nutrisi tidak dapat dilanjutkan karena status kelayakan.",
        )

    # 3. Check for missing required physical parameters (Zero Guessing Rule)
    if sex is None or height_cm is None or weight_kg is None:
        missing: list[str] = []
        if sex is None:
            missing.append("jenis kelamin (sex)")
        if height_cm is None:
            missing.append("tinggi badan (height_cm)")
        if weight_kg is None:
            missing.append("berat badan (current_weight_kg)")

        return NutritionCalculationResultResponse(
            user_id=current_user.id,
            policy_version=NutritionPolicy.VERSION,
            eligibility=NutritionEligibilityResponse(
                status=eligibility_result.status,
                is_eligible=False,
                reasons=[f"Data fisik wajib belum lengkap: {', '.join(missing)}."],
                guidance="Harap lengkapi assessment profil dan fisik sebelum menghitung target nutrisi.",
            ),
            energy=None,
            macros=None,
            weekly_food_budget=weekly_budget,
            currency="IDR",
            bmi_context=None,
            explanation="Perhitungan kebutuhan energi ditangguhkan karena data input fisik wajib belum lengkap.",
        )

    # 4. PAL Classification
    occupation = payload.occupation_type or known_data.get("profile.occupation_type")
    days_per_week = payload.available_days_per_week if payload.available_days_per_week is not None else known_data.get("activity.available_days_per_week")
    minutes_per_session = payload.minutes_per_session if payload.minutes_per_session is not None else known_data.get("activity.minutes_per_session")

    pal_result = PALClassifier.classify(
        occupation_type=occupation,
        available_days_per_week=days_per_week,
        minutes_per_session=minutes_per_session,
        pal_override=payload.pal_category,
    )

    # 5. Deterministic 2023 DRI Energy & Surplus Calculation
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
    height_m = height_cm / 100.0
    bmi = round(weight_kg / (height_m * height_m), 1)

    explanation = (
        f"Kebutuhan energi harian diestimasi sebesar ~{energy_result.rounded_display_kcal:,} kcal "
        f"menggunakan standar ilmiah 2023 DRI EER (estimasi maintenance: {energy_result.maintenance_estimate_kcal:.0f} kcal + "
        f"surplus awal bertahap: +{energy_result.starting_surplus_kcal} kcal). "
        f"Target ini adalah estimasi awal yang akan dipantau bersama tren berat badan nyata."
    )

    return NutritionCalculationResultResponse(
        user_id=current_user.id,
        policy_version=NutritionPolicy.VERSION,
        eligibility=eligibility_response,
        energy=NutritionEnergyResponse(
            method=energy_result.method,
            policy_version=energy_result.policy_version,
            pal_category=energy_result.pal_category,
            pal_reason=energy_result.pal_reason,
            maintenance_estimate_kcal=energy_result.maintenance_estimate_kcal,
            starting_surplus_kcal=energy_result.starting_surplus_kcal,
            target_kcal=energy_result.target_kcal,
            rounded_display_kcal=energy_result.rounded_display_kcal,
        ),
        macros=NutritionMacroResponse(
            protein_rda_floor_g=macro_result.protein_rda_floor_g,
            training_target_g=macro_result.training_target_g,
            amdr_percentages=macro_result.amdr_percentages,
            amdr_gram_ranges=macro_result.amdr_gram_ranges,
        ),
        weekly_food_budget=weekly_budget,
        currency="IDR",
        bmi_context=bmi,
        explanation=explanation,
    )
