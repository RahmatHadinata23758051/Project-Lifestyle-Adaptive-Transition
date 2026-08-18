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
    HalalStatus,
    ServingDivisibility,
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
    FoodCandidateItemDTO,
)
from app.food_candidates.generator import generate_food_candidates
from app.food_candidates.servings import generate_portion_options_for_food
from app.food_candidates.scoring import build_candidate_set


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
    halal_status: HalalStatus = HalalStatus.UNKNOWN,
    allergens: list = None,
    servings: list = None,
    requires_cooking: bool = False,
    required_equipment: list = None,
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
        required_equipment=required_equipment if required_equipment is not None else ([KitchenEquipment.STOVE] if requires_cooking else []),
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
        halal_status=halal_status,
        is_active=True,
    )


def test_nutrition_eligibility_gate_eligible_vs_out_of_scope_and_blocked():
    # 1. Single authoritative source of truth for nutrition eligibility
    rice = make_test_food("f_rice", "Nasi Putih", FoodCategory.GRAIN_STAPLE, 130.0, 2.7, 0.3, 28.0)
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

    # OUT_OF_SCOPE -> STOP immediately, status = NOT_ELIGIBLE
    inp_out = CandidateGenerationInputDTO(
        slot=slot,
        food_pool=[rice],
        nutrition_eligibility_status="OUT_OF_SCOPE",
    )
    res_out = generate_food_candidates(inp_out)
    assert res_out.status == CandidateGenerationStatus.NOT_ELIGIBLE
    assert res_out.candidate_count == 0
    assert CandidateRejectionReason.NUTRITION_NOT_ELIGIBLE.value in res_out.rejected_counts_by_reason

    # BLOCKED -> STOP immediately
    inp_blk = CandidateGenerationInputDTO(
        slot=slot,
        food_pool=[rice],
        nutrition_eligibility_status="BLOCKED",
    )
    res_blk = generate_food_candidates(inp_blk)
    assert res_blk.status == CandidateGenerationStatus.NOT_ELIGIBLE


def test_halal_required_verified_halal_allowed():
    chicken_halal = make_test_food(
        "f_chick_ver", "Daging Ayam Bersertifikat Halal", FoodCategory.POULTRY, 200.0, 22.0, 12.0, 0.0,
        halal_status=HalalStatus.VERIFIED_HALAL,
    )
    rice = make_test_food(
        "f_rice", "Nasi Putih", FoodCategory.GRAIN_STAPLE, 130.0, 2.7, 0.3, 28.0,
        halal_status=HalalStatus.VERIFIED_HALAL,
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
    )

    inp = CandidateGenerationInputDTO(
        slot=slot,
        food_pool=[rice, chicken_halal],
        user_restrictions=["HALAL_REQUIRED"],
        user_equipment=["STOVE"],
    )
    res = generate_food_candidates(inp)
    assert res.status == CandidateGenerationStatus.CANDIDATES_FOUND
    assert res.candidate_count >= 1


def test_halal_required_unknown_halal_rejected_conservatively():
    # Unknown != Safe for Halal
    chicken_unknown = make_test_food(
        "f_chick_unk", "Daging Ayam Pasar", FoodCategory.POULTRY, 200.0, 22.0, 12.0, 0.0,
        halal_status=HalalStatus.UNKNOWN,
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
    )

    inp = CandidateGenerationInputDTO(
        slot=slot,
        food_pool=[chicken_unknown],
        user_restrictions=["HALAL_REQUIRED"],
        user_equipment=["STOVE"],
    )
    res = generate_food_candidates(inp)
    assert CandidateRejectionReason.HALAL_STATUS_UNVERIFIED.value in res.rejected_counts_by_reason


def test_no_pork_does_not_equal_halal_zero_inference():
    # Food is poultry/chicken and contains no pork, but halal_status is UNKNOWN -> NOT Halal
    chicken_no_pork = make_test_food(
        "f_chick_no_pork", "Ayam Potong Segar", FoodCategory.POULTRY, 200.0, 22.0, 12.0, 0.0,
        halal_status=HalalStatus.UNKNOWN,
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
    )

    # User requires HALAL (not just NO_PORK)
    inp = CandidateGenerationInputDTO(
        slot=slot,
        food_pool=[chicken_no_pork],
        user_restrictions=["HALAL"],
        user_equipment=["STOVE"],
    )
    res = generate_food_candidates(inp)
    assert CandidateRejectionReason.HALAL_STATUS_UNVERIFIED.value in res.rejected_counts_by_reason


def test_equipment_unknown_candidate_rejected_and_all_unknown_yields_needs_more_data():
    # H2: Unknown equipment != Available. If all rejected due to unknown equipment -> NEEDS_MORE_DATA
    raw_food = make_test_food(
        "f_raw", "Bahan Masak Mentah", FoodCategory.GRAIN_STAPLE, 150.0, 3.0, 0.5, 30.0,
        requires_cooking=True,
        required_equipment=[KitchenEquipment.STOVE],
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
    )

    inp = CandidateGenerationInputDTO(
        slot=slot,
        food_pool=[raw_food],
        user_equipment=None,  # Unknown equipment
    )
    res = generate_food_candidates(inp)
    assert CandidateRejectionReason.EQUIPMENT_UNKNOWN.value in res.rejected_counts_by_reason
    assert res.status == CandidateGenerationStatus.NEEDS_MORE_DATA


def test_discrete_serving_egg_integer_multipliers_only_no_fractions():
    # H3: Discrete food (egg) allows only 1, 2, 3 units, never 1.5 eggs
    egg_serving = FoodServingDTO(
        id="srv_egg",
        serving_name="1 butir telur",
        grams=50.0,
        divisibility=ServingDivisibility.DISCRETE,
        is_discrete=True,
    )
    egg = make_test_food("f_egg", "Telur Ayam", FoodCategory.EGG, 155.0, 13.0, 11.0, 1.1, servings=[egg_serving])

    portions_egg = generate_portion_options_for_food(egg, role=FoodPlannerRole.PROTEIN_SOURCE)
    gram_values = [p.grams for p in portions_egg]
    assert gram_values == [50.0, 100.0, 150.0]
    assert all("1.5" not in p.serving_name for p in portions_egg)


def test_continuous_serving_fractional_multipliers_allowed():
    # Continuous food (rice) allows 0.5, 1.0, 1.5, 2.0
    rice_serving = FoodServingDTO(
        id="srv_rice",
        serving_name="1 piring",
        grams=100.0,
        divisibility=ServingDivisibility.CONTINUOUS,
        is_discrete=False,
    )
    rice = make_test_food("f_rice", "Nasi Putih", FoodCategory.GRAIN_STAPLE, 130.0, 2.7, 0.3, 28.0, servings=[rice_serving])

    portions_rice = generate_portion_options_for_food(rice, role=FoodPlannerRole.STAPLE)
    gram_values = [p.grams for p in portions_rice]
    assert 50.0 in gram_values   # 0.5 piring
    assert 150.0 in gram_values  # 1.5 piring


def test_near_match_exact_boundaries_strict_near_and_ineligible():
    # Target = 700, Strict = 600–800
    # Extension = 700 * 0.10 = 70 kcal
    # Near Match range = 530–870 kcal
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

    item_strict = FoodCandidateItemDTO("f1", "Strict Item", FoodPlannerRole.STAPLE, None, "100g", 100.0, 700.0, 20.0, 10.0, 50.0)
    cand_strict = build_candidate_set(slot, [item_strict])
    assert cand_strict.match_status == CandidateMatchStatus.STRICT_MATCH

    item_near_low = FoodCandidateItemDTO("f2", "Near Low Item", FoodPlannerRole.STAPLE, None, "100g", 100.0, 550.0, 15.0, 8.0, 40.0)
    cand_near_low = build_candidate_set(slot, [item_near_low])
    assert cand_near_low.match_status == CandidateMatchStatus.NEAR_MATCH

    item_near_high = FoodCandidateItemDTO("f3", "Near High Item", FoodPlannerRole.STAPLE, None, "100g", 100.0, 850.0, 25.0, 12.0, 60.0)
    cand_near_high = build_candidate_set(slot, [item_near_high])
    assert cand_near_high.match_status == CandidateMatchStatus.NEAR_MATCH

    item_ineligible = FoodCandidateItemDTO("f4", "Ineligible Item", FoodPlannerRole.STAPLE, None, "100g", 100.0, 500.0, 10.0, 5.0, 30.0)
    cand_ineligible = build_candidate_set(slot, [item_ineligible])
    assert cand_ineligible.match_status == CandidateMatchStatus.INELIGIBLE


def test_search_truncation_flag_and_deterministic_order_reproducibility():
    # 25 staples and 25 proteins exceeding MAX_POOL_PER_ROLE (20)
    staples = [
        make_test_food(f"staple_{i:02d}", f"Staple {i:02d}", FoodCategory.GRAIN_STAPLE, 120.0 + i, 2.5, 0.5, 25.0)
        for i in range(25)
    ]
    proteins = [
        make_test_food(f"protein_{i:02d}", f"Protein {i:02d}", FoodCategory.POULTRY, 200.0 + i, 20.0, 10.0, 1.0)
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

    inp = CandidateGenerationInputDTO(slot=slot, food_pool=staples + proteins, user_equipment=["STOVE"])
    res_1 = generate_food_candidates(inp)
    res_2 = generate_food_candidates(inp)

    assert res_1.search_truncated is True
    assert res_1.candidate_count == CandidatePolicy.MAX_CANDIDATES_RETURNED
    assert res_1.candidate_count == res_2.candidate_count
    for c1, c2 in zip(res_1.candidates, res_2.candidates):
        assert c1.candidate_id == c2.candidate_id
        assert c1.total_energy_kcal == c2.total_energy_kcal


def test_deterministic_candidate_ranking_same_input_same_ranking():
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

    inp = CandidateGenerationInputDTO(slot=slot, food_pool=[rice, egg], user_equipment=["STOVE"])
    res_1 = generate_food_candidates(inp)
    res_2 = generate_food_candidates(inp)

    assert res_1.ranking_policy_version == CandidatePolicy.RANKING_POLICY_VERSION
    assert res_1.candidate_count == res_2.candidate_count
    for c1, c2 in zip(res_1.candidates, res_2.candidates):
        assert c1.candidate_id == c2.candidate_id
        assert c1.total_energy_kcal == c2.total_energy_kcal
        assert c1.total_protein_g == c2.total_protein_g


def test_allergen_hard_block_contains_and_unknown_safety():
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
    )

    # 1. PEANUT allergy -> hard blocked
    inp_peanut = CandidateGenerationInputDTO(
        slot=slot,
        food_pool=[rice, peanut_food],
        user_allergies=["PEANUT"],
        user_equipment=["STOVE"],
    )
    res_peanut = generate_food_candidates(inp_peanut)
    assert CandidateRejectionReason.ALLERGEN_CONFLICT.value in res_peanut.rejected_counts_by_reason

    # 2. SOY allergy -> unknown soy state rejected conservatively
    inp_soy = CandidateGenerationInputDTO(
        slot=slot,
        food_pool=[rice, unknown_soy_food],
        user_allergies=["SOY"],
        user_equipment=["STOVE"],
    )
    res_soy = generate_food_candidates(inp_soy)
    assert CandidateRejectionReason.ALLERGEN_UNKNOWN.value in res_soy.rejected_counts_by_reason


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
            "nutrition_eligibility_status": "ELIGIBLE",
            "user_allergies": ["PEANUT"],
            "cooking_capability": "CAN_COOK",
            "user_equipment": ["STOVE"],
        }

        res = await client.post("/api/v1/food-candidates/preview", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["slot_id"] == "slot_lunch"
        assert data["status"] in ("CANDIDATES_FOUND", "NO_STRICT_MATCH")
        assert data["policy_version"] == CandidatePolicy.VERSION
        assert data["ranking_policy_version"] == CandidatePolicy.RANKING_POLICY_VERSION

        if data["candidate_count"] > 0:
            top_cand = data["candidates"][0]
            for item in top_cand["items"]:
                assert "Kacang" not in item["canonical_name"]
            assert top_cand["total_energy_kcal"] > 0
