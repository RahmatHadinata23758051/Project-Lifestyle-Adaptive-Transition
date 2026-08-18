import pytest
import jwt
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.nutrition.constants import PhysicalActivityCategory, NutritionEligibilityStatus, NutritionPolicy
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


def test_weight_gain_surplus_addition_and_bounds():
    result = EnergyCalculator.calculate_weight_gain_target(
        sex="MALE",
        age=20,
        height_cm=170.0,
        weight_kg=55.0,
        pal=PhysicalActivityCategory.LOW_ACTIVE,
        starting_surplus_kcal=300,
    )
    assert result.starting_surplus_kcal == 300
    assert result.target_kcal == round(result.maintenance_estimate_kcal + 300, 2)
    assert result.rounded_display_kcal % 50 == 0

    # Surplus capped at MAX_STARTING_SURPLUS_KCAL (500)
    capped_res = EnergyCalculator.calculate_weight_gain_target(
        sex="MALE",
        age=20,
        height_cm=170.0,
        weight_kg=55.0,
        pal=PhysicalActivityCategory.LOW_ACTIVE,
        starting_surplus_kcal=800,
    )
    assert capped_res.starting_surplus_kcal == 500


def test_protein_floor_and_amdr_macro_calculations():
    protein_floor = MacroCalculator.calculate_protein_rda_floor(weight_kg=50.0)
    assert protein_floor == 40.0  # 0.8 * 50

    macros = MacroCalculator.calculate_macro_reference(weight_kg=50.0, target_kcal=2400.0)
    assert macros.protein_rda_floor_g == 40.0
    assert macros.training_target_g is None  # TBD in v0.1

    # Check AMDR percentage boundaries
    assert macros.amdr_percentages["carbohydrate_percent"] == [45, 65]
    assert macros.amdr_percentages["fat_percent"] == [20, 35]
    assert macros.amdr_percentages["protein_percent"] == [10, 35]

    # Check Gram ranges computed from 2400 kcal
    # Carb: (2400 * 0.45)/4 = 270g, (2400 * 0.65)/4 = 390g
    assert macros.amdr_gram_ranges["carbohydrate_g"] == [270, 390]


def test_eligibility_safety_screening():
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

    # 5. Unexplained weight loss
    res_unexplained = NutritionEligibilityEvaluator.evaluate(age=23, has_unexplained_weight_loss=True)
    assert res_unexplained.status == NutritionEligibilityStatus.PROFESSIONAL_GUIDANCE_RECOMMENDED
    assert not res_unexplained.is_eligible


def test_pal_classification_rules():
    # Inactive
    pal_in = PALClassifier.classify(occupation_type="STUDENT", available_days_per_week=0, minutes_per_session=0)
    assert pal_in.category == PhysicalActivityCategory.INACTIVE

    # Low Active (3 days x 30 min = 90 min)
    pal_low = PALClassifier.classify(occupation_type="STUDENT", available_days_per_week=3, minutes_per_session=30)
    assert pal_low.category == PhysicalActivityCategory.LOW_ACTIVE

    # Active (4 days x 45 min = 180 min)
    pal_act = PALClassifier.classify(occupation_type="STUDENT", available_days_per_week=4, minutes_per_session=45)
    assert pal_act.category == PhysicalActivityCategory.ACTIVE

    # Very Active (5 days x 60 min = 300 min)
    pal_very = PALClassifier.classify(occupation_type="STUDENT", available_days_per_week=5, minutes_per_session=60)
    assert pal_very.category == PhysicalActivityCategory.VERY_ACTIVE


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

        # 2. Update Financial Profile
        await client.put(
            "/api/v1/user-state/financial-profile",
            json={"weekly_food_budget": 450000.0, "currency": "IDR"},
            headers=headers,
        )

        # 3. Call Calculation Endpoint
        calc_payload = {
            "available_days_per_week": 3,
            "minutes_per_session": 40,
            "starting_surplus_kcal": 300,
        }
        res_calc = await client.post("/api/v1/nutrition/calculate", json=calc_payload, headers=headers)
        assert res_calc.status_code == 200
        data = res_calc.json()

        assert data["policy_version"] == NutritionPolicy.VERSION
        assert data["eligibility"]["is_eligible"] is True
        assert data["energy"]["method"] == "DRI_EER_2023"
        assert data["energy"]["pal_category"] == "ACTIVE"
        assert data["energy"]["starting_surplus_kcal"] == 300
        assert data["energy"]["target_kcal"] > 2000.0
        assert data["macros"]["protein_rda_floor_g"] == round(56.0 * 0.8, 1)
        assert data["weekly_food_budget"] == 450000.0
        assert data["bmi_context"] == round(56.0 / (1.74 * 1.74), 1)
        assert "DRI EER" in data["explanation"]
