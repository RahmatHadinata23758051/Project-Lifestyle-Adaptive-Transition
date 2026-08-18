import pytest
import jwt
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.food_knowledge.constants import (
    FoodCategory,
    PreparationState,
    FoodEntityType,
    BasisType,
    DataQualityStatus,
    NutrientCompleteness,
    AllergenType,
    AllergenRelationshipType,
    KitchenEquipment,
    PrepComplexity,
)
from app.food_knowledge.models import (
    FoodKnowledgeItemDTO,
    NutrientProfileDTO,
    FoodServingDTO,
    FoodAllergenDTO,
    PreparationRequirementsDTO,
    SourceProvenanceDTO,
)
from app.food_knowledge.importer import FoodImportPipeline
from app.repositories.food_repository import FoodRepository
from app.meal_structure.constants import MealSlotType, MealWindowType, ScheduleProvenance, MealScheduleReasonCode
from app.meal_structure.models import MealSlotDTO
from app.food_candidates.constants import (
    FoodPlannerRole,
    CandidateMatchStatus,
    CandidateGenerationStatus,
    CandidateRejectionReason,
    CandidatePolicy,
)
from app.food_candidates.models import (
    CandidateGenerationInputDTO,
)
from app.food_candidates.generator import generate_food_candidates


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def make_test_food(
    food_id: str,
    name: str,
    category: FoodCategory,
    kcal_per_100g: float,
    protein_per_100g: float,
    fat_per_100g: float,
    carb_per_100g: float,
    prep_state: PreparationState = PreparationState.COOKED,
    quality: DataQualityStatus = DataQualityStatus.VERIFIED_OFFICIAL,
    allergens: list = None,
    servings: list = None,
    requires_cooking: bool = False,
) -> FoodKnowledgeItemDTO:
    source_dto = SourceProvenanceDTO(id="s1", code="TKPI_2020", name="TKPI 2020")
    nutrients = NutrientProfileDTO(
        energy_kcal=kcal_per_100g,
        protein_g=protein_per_100g,
        fat_g=fat_per_100g,
        carbohydrate_g=carb_per_100g,
        basis_type=BasisType.PER_100_G_EDIBLE,
        reference_amount=100.0,
        completeness=NutrientCompleteness.CORE_COMPLETE,
        data_quality_status=quality,
    )
    prep_req = PreparationRequirementsDTO(
        requires_cooking=requires_cooking,
        minimum_capability="CAN_COOK" if requires_cooking else "BUY_ONLY",
        prep_complexity=PrepComplexity.VERY_SIMPLE,
        required_equipment=[KitchenEquipment.STOVE] if requires_cooking else [],
    )
    return FoodKnowledgeItemDTO(
        id=food_id,
        canonical_name=name,
        local_name=name,
        scientific_name=None,
        entity_type=FoodEntityType.GENERIC_FOOD,
        food_category=category,
        preparation_state=prep_state,
        is_generic_food=True,
        source=source_dto,
        source_food_code=f"CODE_{food_id}",
        nutrients=nutrients,
        aliases=[],
        servings=servings or [],
        allergens=allergens or [],
        preparation_requirements=prep_req,
        data_quality_status=quality,
        is_active=True,
    )


def test_allergen_hard_block_and_unknown_safety():
    # Rice (No allergen), Peanut tempe (Contains Peanut), Soy milk (Unknown Soy)
    rice = make_test_food("f_rice", "Nasi Putih", FoodCategory.GRAIN_STAPLE, 130.0, 2.7, 0.3, 28.0)
    peanut_food = make_test_food(
        "f_peanut",
        "Kacang Goreng",
        FoodCategory.LEGUME,
        500.0,
        25.0,
        40.0,
        20.0,
        allergens=[FoodAllergenDTO(allergen_type=AllergenType.PEANUT, relationship_type=AllergenRelationshipType.CONTAINS)],
    )
    unknown_soy_food = make_test_food(
        "f_soy",
        "Sari Kedelai Olahan",
        FoodCategory.SOY_PRODUCT,
        80.0,
        5.0,
        3.0,
        8.0,
        allergens=[FoodAllergenDTO(allergen_type=AllergenType.SOY, relationship_type=AllergenRelationshipType.UNKNOWN)],
    )

    slot = MealSlotDTO(
        slot_id="slot_1",
        slot_type=MealSlotType.MAIN_MEAL,
        sequence=1,
        preferred_time="12:00",
        earliest_time="11:15",
        latest_time="12:45",
        duration_minutes=30,
        target_kcal=600.0,
        min_kcal=500.0,
        max_kcal=700.0,
        schedule_source=ScheduleProvenance.DERIVED,
        reason_code=MealScheduleReasonCode.NORMAL_BASELINE,
        window_type=MealWindowType.FLEXIBLE,
    )

    # 1. User has PEANUT allergy -> peanut_food hard-blocked
    inp_peanut = CandidateGenerationInputDTO(
        slot=slot,
        food_pool=[rice, peanut_food],
        user_allergies=["PEANUT"],
    )
    res_peanut = generate_food_candidates(inp_peanut)
    assert CandidateRejectionReason.ALLERGEN_CONFLICT.value in res_peanut.rejected_counts_by_reason

    # 2. User has SOY allergy -> unknown soy food excluded (Unknown != Safe)
    inp_soy = CandidateGenerationInputDTO(
        slot=slot,
        food_pool=[rice, unknown_soy_food],
        user_allergies=["SOY"],
    )
    res_soy = generate_food_candidates(inp_soy)
    assert CandidateRejectionReason.ALLERGEN_UNKNOWN.value in res_soy.rejected_counts_by_reason


def test_preparation_capability_filter():
    rice_cooked = make_test_food("f_rice", "Nasi Putih", FoodCategory.GRAIN_STAPLE, 130.0, 2.7, 0.3, 28.0, prep_state=PreparationState.COOKED, requires_cooking=False)
    chicken_raw = make_test_food("f_raw_chick", "Daging Ayam Mentah", FoodCategory.POULTRY, 200.0, 22.0, 12.0, 0.0, prep_state=PreparationState.RAW, requires_cooking=True)

    slot = MealSlotDTO(
        slot_id="slot_1",
        slot_type=MealSlotType.MAIN_MEAL,
        sequence=1,
        preferred_time="12:00",
        earliest_time="11:15",
        latest_time="12:45",
        duration_minutes=30,
        target_kcal=600.0,
        min_kcal=500.0,
        max_kcal=700.0,
        schedule_source=ScheduleProvenance.DERIVED,
        reason_code=MealScheduleReasonCode.NORMAL_BASELINE,
    )

    # BUY_ONLY user cannot use chicken_raw
    inp = CandidateGenerationInputDTO(
        slot=slot,
        food_pool=[rice_cooked, chicken_raw],
        cooking_capability="BUY_ONLY",
    )
    res = generate_food_candidates(inp)
    assert CandidateRejectionReason.PREPARATION_INCOMPATIBLE.value in res.rejected_counts_by_reason


def test_energy_match_strict_and_nutrient_aggregation():
    # Rice: 100g = 130 kcal, 2.7g P, 0.3g F, 28g C
    # Chicken: 100g = 250 kcal, 25g P, 15g F, 0g C
    # Egg: 100g = 155 kcal, 13g P, 11g F, 1.1g C
    rice = make_test_food("f_rice", "Nasi Putih", FoodCategory.GRAIN_STAPLE, 130.0, 2.7, 0.3, 28.0)
    chicken = make_test_food("f_chicken", "Ayam Panggang", FoodCategory.POULTRY, 250.0, 25.0, 15.0, 0.0)
    egg = make_test_food("f_egg", "Telur Rebus", FoodCategory.EGG, 155.0, 13.0, 11.0, 1.1)

    slot = MealSlotDTO(
        slot_id="slot_1",
        slot_type=MealSlotType.MAIN_MEAL,
        sequence=1,
        preferred_time="12:00",
        earliest_time="11:15",
        latest_time="12:45",
        duration_minutes=30,
        target_kcal=650.0,
        min_kcal=550.0,
        max_kcal=750.0,
        schedule_source=ScheduleProvenance.DERIVED,
        reason_code=MealScheduleReasonCode.NORMAL_BASELINE,
    )

    inp = CandidateGenerationInputDTO(
        slot=slot,
        food_pool=[rice, chicken, egg],
    )
    res = generate_food_candidates(inp)

    assert res.status == CandidateGenerationStatus.CANDIDATES_FOUND
    assert res.candidate_count >= 1

    # Check top candidate
    top_cand = res.candidates[0]
    assert top_cand.match_status == CandidateMatchStatus.STRICT_MATCH
    assert 550.0 <= top_cand.total_energy_kcal <= 750.0
    assert top_cand.total_protein_g is not None
    assert top_cand.total_protein_g > 0.0
    assert top_cand.energy_deviation_kcal == pytest.approx(top_cand.total_energy_kcal - 650.0, abs=0.1)


def test_determinism_same_input_same_output():
    rice = make_test_food("f_rice", "Nasi Putih", FoodCategory.GRAIN_STAPLE, 130.0, 2.7, 0.3, 28.0)
    egg = make_test_food("f_egg", "Telur Rebus", FoodCategory.EGG, 155.0, 13.0, 11.0, 1.1)

    slot = MealSlotDTO(
        slot_id="slot_1",
        slot_type=MealSlotType.MAIN_MEAL,
        sequence=1,
        preferred_time="12:00",
        earliest_time="11:15",
        latest_time="12:45",
        duration_minutes=30,
        target_kcal=500.0,
        min_kcal=400.0,
        max_kcal=600.0,
        schedule_source=ScheduleProvenance.DERIVED,
        reason_code=MealScheduleReasonCode.NORMAL_BASELINE,
    )

    inp = CandidateGenerationInputDTO(slot=slot, food_pool=[rice, egg])
    res_1 = generate_food_candidates(inp)
    res_2 = generate_food_candidates(inp)

    assert res_1.candidate_count == res_2.candidate_count
    for c1, c2 in zip(res_1.candidates, res_2.candidates):
        assert c1.candidate_id == c2.candidate_id
        assert c1.total_energy_kcal == c2.total_energy_kcal
        assert c1.total_protein_g == c2.total_protein_g


def test_unverified_source_quality_rejected():
    unverified_food = make_test_food(
        "f_unverified",
        "Unknown Berry",
        FoodCategory.FRUIT,
        100.0,
        1.0,
        0.5,
        20.0,
        quality=DataQualityStatus.UNVERIFIED,
    )

    slot = MealSlotDTO(
        slot_id="slot_snack",
        slot_type=MealSlotType.SNACK,
        sequence=1,
        preferred_time="16:00",
        earliest_time="15:30",
        latest_time="16:30",
        duration_minutes=15,
        target_kcal=200.0,
        min_kcal=150.0,
        max_kcal=250.0,
        schedule_source=ScheduleProvenance.DERIVED,
        reason_code=MealScheduleReasonCode.NORMAL_BASELINE,
    )

    inp = CandidateGenerationInputDTO(slot=slot, food_pool=[unverified_food])
    res = generate_food_candidates(inp)

    assert res.status == CandidateGenerationStatus.NO_ELIGIBLE_FOODS
    assert CandidateRejectionReason.QUALITY_NOT_ELIGIBLE.value in res.rejected_counts_by_reason


def test_bounded_search_space_control():
    # 25 staples and 25 proteins
    staples = [
        make_test_food(f"staple_{i}", f"Staple {i}", FoodCategory.GRAIN_STAPLE, 120.0 + i, 2.5, 0.5, 25.0)
        for i in range(25)
    ]
    proteins = [
        make_test_food(f"protein_{i}", f"Protein {i}", FoodCategory.POULTRY, 200.0 + i, 20.0, 10.0, 1.0)
        for i in range(25)
    ]

    slot = MealSlotDTO(
        slot_id="slot_1",
        slot_type=MealSlotType.MAIN_MEAL,
        sequence=1,
        preferred_time="12:00",
        earliest_time="11:15",
        latest_time="12:45",
        duration_minutes=30,
        target_kcal=700.0,
        min_kcal=600.0,
        max_kcal=800.0,
        schedule_source=ScheduleProvenance.DERIVED,
        reason_code=MealScheduleReasonCode.NORMAL_BASELINE,
    )

    inp = CandidateGenerationInputDTO(slot=slot, food_pool=staples + proteins)
    res = generate_food_candidates(inp)

    # Returned candidates strictly capped at MAX_CANDIDATES_RETURNED (20)
    assert res.candidate_count <= CandidatePolicy.MAX_CANDIDATES_RETURNED


@pytest.mark.asyncio
async def test_api_food_candidates_preview_authenticated(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-candidate-test", "candidate@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        # Seed food knowledge in DB
        source = FoodRepository.get_or_create_source(
            db=db_session,
            code="TKPI_CANDIDATE_SEED",
            name="Tabel Komposisi Pangan Indonesia",
            publisher="Kemenkes RI",
            publication_year=2020,
        )
        raw_items = [
            {
                "canonical_name": "Nasi Putih Pulen",
                "source_food_code": "NASI_01",
                "food_category": "GRAIN_STAPLE",
                "preparation_state": "COOKED",
                "nutrients": {
                    "energy_kcal": 130.0,
                    "protein_g": 2.7,
                    "fat_g": 0.3,
                    "carbohydrate_g": 28.0,
                    "basis_type": "PER_100_G_EDIBLE",
                    "reference_amount": 100.0,
                },
                "servings": [{"serving_name": "1 centong", "grams": 100.0}],
            },
            {
                "canonical_name": "Dada Ayam Panggang",
                "source_food_code": "AYAM_01",
                "food_category": "POULTRY",
                "preparation_state": "ROASTED",
                "nutrients": {
                    "energy_kcal": 165.0,
                    "protein_g": 31.0,
                    "fat_g": 3.6,
                    "carbohydrate_g": 0.0,
                    "basis_type": "PER_100_G_EDIBLE",
                    "reference_amount": 100.0,
                },
                "servings": [{"serving_name": "1 potong sedang", "grams": 100.0}],
            },
            {
                "canonical_name": "Kacang Tanah Sangrai (Alergen)",
                "source_food_code": "KACANG_01",
                "food_category": "LEGUME",
                "preparation_state": "ROASTED",
                "nutrients": {
                    "energy_kcal": 560.0,
                    "protein_g": 26.0,
                    "fat_g": 49.0,
                    "carbohydrate_g": 16.0,
                    "basis_type": "PER_100_G_EDIBLE",
                    "reference_amount": 100.0,
                },
                "allergens": [{"allergen_type": "PEANUT", "relationship_type": "CONTAINS"}],
            },
        ]
        FoodImportPipeline.import_dataset(db=db_session, source_record=source, raw_items=raw_items, dry_run=False)

        # Call Preview Endpoint
        payload = {
            "slot_id": "slot_lunch",
            "slot_type": "MAIN_MEAL",
            "target_kcal": 450.0,
            "min_kcal": 350.0,
            "max_kcal": 550.0,
            "user_allergies": ["PEANUT"],
            "cooking_capability": "CAN_COOK",
        }

        res = await client.post("/api/v1/food-candidates/preview", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["slot_id"] == "slot_lunch"
        assert data["status"] in ("CANDIDATES_FOUND", "NO_STRICT_MATCH")
        assert data["policy_version"] == CandidatePolicy.VERSION

        if data["candidate_count"] > 0:
            top_cand = data["candidates"][0]
            # No peanut in items
            for item in top_cand["items"]:
                assert "Kacang" not in item["canonical_name"]
            assert top_cand["total_energy_kcal"] > 0
