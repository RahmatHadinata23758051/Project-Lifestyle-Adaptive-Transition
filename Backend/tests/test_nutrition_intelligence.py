import pytest
import jwt
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.nutrition.constants import (
    PhysicalActivityCategory,
    PALAssessmentStatus,
    PALResolutionMethod,
    CalculationSource,
    NutritionEligibilityStatus,
    NutritionPolicy,
)
from app.nutrition.energy import EnergyCalculator
from app.nutrition.macros import MacroCalculator
from app.nutrition.eligibility import NutritionEligibilityEvaluator
from app.nutrition.pal import PALClassifier


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_male_eer_calculations_2023_dri_accuracy():
    # Male, Age 22, Height 175 cm, Weight 60 kg
    age, height, weight = 22, 175.0, 60.0

    eer_inactive = EnergyCalculator.calculate_eer("MALE", age, height, weight, PhysicalActivityCategory.INACTIVE)
    assert eer_inactive == 2498.31

    eer_low = EnergyCalculator.calculate_eer("MALE", age, height, weight, PhysicalActivityCategory.LOW_ACTIVE)
    assert eer_low == 2692.11

    eer_active = EnergyCalculator.calculate_eer("MALE", age, height, weight, PhysicalActivityCategory.ACTIVE)
    assert eer_active == 2862.16

    eer_very_active = EnergyCalculator.calculate_eer("MALE", age, height, weight, PhysicalActivityCategory.VERY_ACTIVE)
    assert eer_very_active == 3122.21


def test_female_eer_calculations_2023_dri_accuracy():
    # Female, Age 25, Height 160 cm, Weight 48 kg
    age, height, weight = 25, 160.0, 48.0

    eer_inactive = EnergyCalculator.calculate_eer("FEMALE", age, height, weight, PhysicalActivityCategory.INACTIVE)
    assert eer_inactive == 1886.93

    eer_low = EnergyCalculator.calculate_eer("FEMALE", age, height, weight, PhysicalActivityCategory.LOW_ACTIVE)
    assert eer_low == 2039.24

    eer_active = EnergyCalculator.calculate_eer("FEMALE", age, height, weight, PhysicalActivityCategory.ACTIVE)
    assert eer_active == 2173.72

    eer_very_active = EnergyCalculator.calculate_eer("FEMALE", age, height, weight, PhysicalActivityCategory.VERY_ACTIVE)
    assert eer_very_active == 2390.66


def test_official_dri_published_example_regression():
    # 2023 DRI Published Example:
    # Female, Age 22, Height 165 cm, Weight 63 kg, PAL: LOW_ACTIVE
    # Formula: 575.77 - (7.01 * 22) + (6.60 * 165) + (12.14 * 63) = 2275.37 kcal/day
    eer = EnergyCalculator.calculate_eer(
        sex="FEMALE",
        age=22,
        height_cm=165.0,
        weight_kg=63.0,
        pal=PhysicalActivityCategory.LOW_ACTIVE,
    )
    assert eer == pytest.approx(2275, abs=1)


def test_weight_gain_surplus_transparency_and_bounds():
    # 1. Normal surplus within bound (300 kcal)
    result = EnergyCalculator.calculate_weight_gain_target(
        sex="MALE",
        age=20,
        height_cm=170.0,
        weight_kg=55.0,
        pal=PhysicalActivityCategory.LOW_ACTIVE,
        starting_surplus_kcal=300,
    )
    assert result.requested_surplus_kcal == 300
    assert result.applied_surplus_kcal == 300
    assert result.surplus_was_adjusted is False
    assert result.target_kcal == round(result.maintenance_estimate_kcal + 300, 2)
    assert result.rounded_display_kcal % 50 == 0

    # 2. Requested surplus above bound (800 kcal -> capped to 500 kcal)
    capped_res = EnergyCalculator.calculate_weight_gain_target(
        sex="MALE",
        age=20,
        height_cm=170.0,
        weight_kg=55.0,
        pal=PhysicalActivityCategory.LOW_ACTIVE,
        starting_surplus_kcal=800,
    )
    assert capped_res.requested_surplus_kcal == 800
    assert capped_res.applied_surplus_kcal == 500
    assert capped_res.surplus_was_adjusted is True
    assert capped_res.target_kcal == round(capped_res.maintenance_estimate_kcal + 500, 2)


def test_protein_rda_reference_and_amdr_macro_calculations():
    protein_ref = MacroCalculator.calculate_protein_rda_reference(weight_kg=50.0)
    assert protein_ref == 40.0  # 0.8 * 50

    macros = MacroCalculator.calculate_macro_reference(weight_kg=50.0, target_kcal=2400.0)
    assert macros.protein_rda_reference_g == 40.0
    assert macros.training_target_g is None  # TBD in v0.1

    # Check AMDR percentage boundaries
    assert macros.amdr_percentages["carbohydrate_percent"] == [45, 65]
    assert macros.amdr_percentages["fat_percent"] == [20, 35]
    assert macros.amdr_percentages["protein_percent"] == [10, 35]

    # Check Gram ranges computed from 2400 kcal
    # Carb: (2400 * 0.45)/4 = 270g, (2400 * 0.65)/4 = 390g
    assert macros.amdr_gram_ranges["carbohydrate_g"] == [270, 390]


def test_eligibility_safety_screening_and_wording():
    # 1. Underage < 19
    res_underage = NutritionEligibilityEvaluator.evaluate(age=18)
    assert res_underage.status == NutritionEligibilityStatus.OUT_OF_SCOPE
    assert not res_underage.is_eligible

    # 2. Adult 19+ -> Eligible
    res_adult = NutritionEligibilityEvaluator.evaluate(age=19)
    assert res_adult.status == NutritionEligibilityStatus.ELIGIBLE
    assert res_adult.is_eligible

    # 3. Pregnancy / Lactation
    res_preg = NutritionEligibilityEvaluator.evaluate(age=24, is_pregnant_or_lactating=True)
    assert res_preg.status == NutritionEligibilityStatus.OUT_OF_SCOPE
    assert not res_preg.is_eligible

    # 4. Medical diet or eating disorder
    res_med = NutritionEligibilityEvaluator.evaluate(age=22, has_prescribed_medical_diet=True)
    assert res_med.status == NutritionEligibilityStatus.OUT_OF_SCOPE
    assert not res_med.is_eligible

    # 5. Unexplained weight loss (Reason wording hardening check)
    res_unexplained = NutritionEligibilityEvaluator.evaluate(age=23, has_unexplained_weight_loss=True)
    assert res_unexplained.status == NutritionEligibilityStatus.PROFESSIONAL_GUIDANCE_RECOMMENDED
    assert not res_unexplained.is_eligible
    assert res_unexplained.reasons == ["Penurunan berat badan yang tidak dapat dijelaskan."]


def test_pal_classification_zero_guessing_and_validation():
    # 1. Missing PAL / no context -> UNDETERMINED (never assumes INACTIVE)
    pal_missing = PALClassifier.classify()
    assert pal_missing.status == PALAssessmentStatus.UNDETERMINED
    assert pal_missing.category is None

    # 2. Exercise minutes alone must NOT automatically become final PAL
    pal_mins_only = PALClassifier.classify(available_days_per_week=4, minutes_per_session=45)
    assert pal_mins_only.status == PALAssessmentStatus.UNDETERMINED
    assert pal_mins_only.category is None

    # 3. Explicit confirmed PAL -> RESOLVED
    for cat in PhysicalActivityCategory:
        pal_confirmed = PALClassifier.classify(confirmed_pal_category=cat)
        assert pal_confirmed.status == PALAssessmentStatus.RESOLVED
        assert pal_confirmed.category == cat
        assert pal_confirmed.resolution_method == PALResolutionMethod.USER_CONFIRMED

    # 4. String-based valid confirmed PAL
    pal_str = PALClassifier.classify(confirmed_pal_category="ACTIVE")
    assert pal_str.status == PALAssessmentStatus.RESOLVED
    assert pal_str.category == PhysicalActivityCategory.ACTIVE

    # 5. Invalid PAL -> INVALID
    pal_invalid = PALClassifier.classify(confirmed_pal_category="SUPER_ATHLETE_EXTREME")
    assert pal_invalid.status == PALAssessmentStatus.INVALID
    assert pal_invalid.category is None
    assert not pal_invalid.is_valid


@pytest.mark.asyncio
async def test_readiness_calculation_ready_vs_plan_ready():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-readiness-test", "readiness@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        # Case B: PAL is missing -> calculation_ready = False, plan_ready = False, energy = None
        res_no_pal = await client.post(
            "/api/v1/nutrition/calculate",
            json={
                "age": 22,
                "sex": "MALE",
                "height_cm": 175.0,
                "current_weight_kg": 60.0,
                # pal_category is omitted
            },
            headers=headers,
        )
        assert res_no_pal.status_code == 200
        data_no_pal = res_no_pal.json()
        assert data_no_pal["calculation_ready"] is False
        assert data_no_pal["plan_ready"] is False
        assert "pal_category" in data_no_pal["missing_for_calculation"]
        assert data_no_pal["energy"] is None
        assert data_no_pal["macros"] is None

        # Case A: Physical data + PAL complete, Budget missing -> calculation_ready = True, plan_ready = False
        res_no_budget = await client.post(
            "/api/v1/nutrition/calculate",
            json={
                "age": 22,
                "sex": "MALE",
                "height_cm": 175.0,
                "current_weight_kg": 60.0,
                "confirmed_pal_category": "LOW_ACTIVE",
                # weekly_food_budget omitted
            },
            headers=headers,
        )
        assert res_no_budget.status_code == 200
        data_no_budget = res_no_budget.json()
        assert data_no_budget["calculation_ready"] is True
        assert data_no_budget["plan_ready"] is False
        assert data_no_budget["missing_for_calculation"] == []
        assert data_no_budget["missing_for_plan"] == ["weekly_food_budget"]
        assert data_no_budget["energy"] is not None
        assert data_no_budget["macros"] is not None

        # Case C: All complete (including IDR integer budget) -> calculation_ready = True, plan_ready = True
        res_full = await client.post(
            "/api/v1/nutrition/calculate",
            json={
                "age": 22,
                "sex": "MALE",
                "height_cm": 175.0,
                "current_weight_kg": 60.0,
                "confirmed_pal_category": "LOW_ACTIVE",
                "weekly_food_budget": 450000,
            },
            headers=headers,
        )
        assert res_full.status_code == 200
        data_full = res_full.json()
        assert data_full["calculation_ready"] is True
        assert data_full["plan_ready"] is True
        assert data_full["missing_for_calculation"] == []
        assert data_full["missing_for_plan"] == []
        assert data_full["weekly_food_budget"] == 450000


@pytest.mark.asyncio
async def test_api_nutrition_calculate_endpoint_authenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-nutrition-calc", "nutrition@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Update Core Profile
        await client.patch(
            "/api/v1/profile",
            json={
                "birth_date": "2002-01-01",  # Age 24 in 2026
                "sex": "MALE",
                "height_cm": 174.0,
                "current_weight_kg": 56.0,
                "occupation_type": "STUDENT",
            },
            headers=headers,
        )

        # 2. Update Financial Profile with integer IDR
        await client.put(
            "/api/v1/user-state/financial-profile",
            json={"weekly_food_budget": 450000, "currency": "IDR"},
            headers=headers,
        )

        # 3. Call Calculation Endpoint with confirmed PAL
        calc_payload = {
            "confirmed_pal_category": "ACTIVE",
            "starting_surplus_kcal": 300,
        }
        res_calc = await client.post("/api/v1/nutrition/calculate", json=calc_payload, headers=headers)
        assert res_calc.status_code == 200
        data = res_calc.json()

        assert data["calculation_source"] == "LIVE_PREVIEW"
        assert data["energy_method"] == "DRI_EER_2023"
        assert data["pal_resolution_method"] == "USER_CONFIRMED"
        assert data["policy_version"] == NutritionPolicy.VERSION
        assert data["calculation_ready"] is True
        assert data["plan_ready"] is True
        assert data["eligibility"]["is_eligible"] is True
        assert data["energy"]["method"] == "DRI_EER_2023"
        assert data["energy"]["pal_category"] == "ACTIVE"
        assert data["energy"]["requested_surplus_kcal"] == 300
        assert data["energy"]["applied_surplus_kcal"] == 300
        assert data["energy"]["surplus_was_adjusted"] is False
        assert data["energy"]["target_kcal"] > 2000.0
        assert data["macros"]["protein_rda_reference_g"] == round(56.0 * 0.8, 1)
        assert data["weekly_food_budget"] == 450000
        assert data["bmi_context"] == round(56.0 / (1.74 * 1.74), 1)
        assert "DRI EER" in data["explanation"]
