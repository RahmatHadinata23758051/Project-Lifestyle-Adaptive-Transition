import pytest
import jwt
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.food_knowledge.constants import (
    SourceType,
    FoodCategory,
    PreparationState,
    FoodEntityType,
    BasisType,
    DataQualityStatus,
    NutrientCompleteness,
    AllergenType,
    AllergenRelationshipType,
    FoodPlannerEligibilityStatus,
    ServingSourceType,
    ServingConfidence,
    KitchenEquipment,
    PrepComplexity,
)
from app.food_knowledge.models import (
    NutrientProfileDTO,
    FoodServingDTO,
    FoodAllergenDTO,
    FoodKnowledgeItemDTO,
    SourceProvenanceDTO,
    PreparationRequirementsDTO,
)
from app.food_knowledge.nutrients import (
    scale_nutrients,
    determine_nutrient_completeness,
    calculate_edible_weight,
)
from app.food_knowledge.servings import convert_serving_to_grams
from app.food_knowledge.normalization import normalize_food_search_query
from app.food_knowledge.allergens import check_allergen_conflict
from app.food_knowledge.eligibility import evaluate_food_planner_eligibility
from app.food_knowledge.importer import FoodImportPipeline
from app.repositories.food_repository import FoodRepository


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_nutrient_scaling_and_null_preservation():
    # 100g reference basis with fiber = None
    nutrients = NutrientProfileDTO(
        energy_kcal=200.0,
        protein_g=10.0,
        fat_g=5.0,
        carbohydrate_g=30.0,
        fiber_g=None,
        water_g=50.0,
        optional_micronutrients={"calcium_mg": 120.0},
        basis_type=BasisType.PER_100_G_EDIBLE,
        reference_amount=100.0,
        reference_unit="g",
        data_quality_status=DataQualityStatus.VERIFIED_OFFICIAL,
        completeness=NutrientCompleteness.CORE_COMPLETE,
    )

    # Scale to 150g
    scaled = scale_nutrients(nutrients, consumed_grams=150.0)
    assert scaled.energy_kcal == 300.0
    assert scaled.protein_g == 15.0
    assert scaled.fat_g == 7.5
    assert scaled.carbohydrate_g == 45.0
    assert scaled.water_g == 75.0
    assert scaled.reference_amount == 150.0

    # CRITICAL INVARIANT: Null != 0
    assert scaled.fiber_g is None

    # Micronutrients scaling
    assert scaled.optional_micronutrients is not None
    assert scaled.optional_micronutrients["calcium_mg"] == 180.0


def test_serving_conversion_to_grams():
    serving = FoodServingDTO(
        id="serving-1",
        serving_name="1 butir sedang",
        grams=55.0,
        source_type=ServingSourceType.MEASURED_CURATED,
        confidence=ServingConfidence.HIGH,
    )

    # 2 pieces = 110g
    grams = convert_serving_to_grams(serving, count=2.0)
    assert grams == 110.0

    # Half piece = 27.5g
    grams_half = convert_serving_to_grams(serving, count=0.5)
    assert grams_half == 27.5

    with pytest.raises(ValueError):
        convert_serving_to_grams(serving, count=0)

    with pytest.raises(ValueError):
        convert_serving_to_grams(serving, count=-1)


def test_edible_portion_calculation():
    # 200g banana with 68% edible portion
    edible_g = calculate_edible_weight(purchase_weight_g=200.0, edible_portion_percent=68.0)
    assert edible_g == 136.0

    # No edible portion specified -> 100%
    assert calculate_edible_weight(150.0, None) == 150.0

    with pytest.raises(ValueError):
        calculate_edible_weight(100.0, -5.0)

    with pytest.raises(ValueError):
        calculate_edible_weight(100.0, 105.0)


def test_allergen_safety_block_and_unknown_handling():
    food_allergens = [
        FoodAllergenDTO(allergen_type=AllergenType.PEANUT, relationship_type=AllergenRelationshipType.CONTAINS),
        FoodAllergenDTO(allergen_type=AllergenType.SOY, relationship_type=AllergenRelationshipType.UNKNOWN),
    ]

    # 1. User has PEANUT allergy -> Hard block
    has_conflict, reasons = check_allergen_conflict([AllergenType.PEANUT], food_allergens)
    assert has_conflict is True
    assert any("PEANUT" in r for r in reasons)

    # 2. User has SOY allergy, food has UNKNOWN soy -> Block / Unsafe
    has_conflict_soy, reasons_soy = check_allergen_conflict([AllergenType.SOY], food_allergens)
    assert has_conflict_soy is True
    assert any("UNKNOWN" in r for r in reasons_soy)

    # 3. User has EGG allergy -> No conflict
    has_conflict_egg, reasons_egg = check_allergen_conflict([AllergenType.EGG], food_allergens)
    assert has_conflict_egg is False
    assert len(reasons_egg) == 0


def test_search_query_normalization():
    assert normalize_food_search_query("  TeMpE    kEdeLai !? ") == "tempe kedelai"
    assert normalize_food_search_query("Nasi-Goreng (Spesial)") == "nasi-goreng spesial"
    assert normalize_food_search_query("") == ""


def test_planner_eligibility_evaluation():
    source_dto = SourceProvenanceDTO(id="s1", code="TKPI_2020", name="TKPI 2020")

    # Complete & Verified Food
    food_valid = FoodKnowledgeItemDTO(
        id="f1",
        canonical_name="Tempe Goreng",
        local_name="Tempe",
        scientific_name=None,
        entity_type=FoodEntityType.GENERIC_FOOD,
        food_category=FoodCategory.SOY_PRODUCT,
        preparation_state=PreparationState.FRIED,
        is_generic_food=True,
        source=source_dto,
        source_food_code="TKPI_TEMPE_1",
        nutrients=NutrientProfileDTO(
            energy_kcal=200.0,
            protein_g=14.0,
            fat_g=8.0,
            carbohydrate_g=12.0,
            completeness=NutrientCompleteness.CORE_COMPLETE,
        ),
        aliases=[],
        servings=[],
        allergens=[FoodAllergenDTO(allergen_type=AllergenType.SOY, relationship_type=AllergenRelationshipType.CONTAINS)],
        preparation_requirements=None,
        data_quality_status=DataQualityStatus.VERIFIED_OFFICIAL,
        is_active=True,
    )
    status_valid, reasons_valid = evaluate_food_planner_eligibility(food_valid)
    assert status_valid == FoodPlannerEligibilityStatus.ELIGIBLE
    assert len(reasons_valid) == 0

    # Incomplete nutrients
    food_incomplete = FoodKnowledgeItemDTO(
        id="f2",
        canonical_name="Unknown Herb",
        local_name=None,
        scientific_name=None,
        entity_type=FoodEntityType.GENERIC_FOOD,
        food_category=FoodCategory.OTHER,
        preparation_state=PreparationState.RAW,
        is_generic_food=True,
        source=source_dto,
        source_food_code="HERB_1",
        nutrients=NutrientProfileDTO(
            energy_kcal=None,
            protein_g=None,
            fat_g=None,
            carbohydrate_g=None,
            completeness=NutrientCompleteness.INSUFFICIENT,
        ),
        aliases=[],
        servings=[],
        allergens=[],
        preparation_requirements=None,
        data_quality_status=DataQualityStatus.VERIFIED_OFFICIAL,
        is_active=True,
    )
    status_inc, reasons_inc = evaluate_food_planner_eligibility(food_incomplete)
    assert status_inc == FoodPlannerEligibilityStatus.NUTRIENT_DATA_INSUFFICIENT


def test_importer_dry_run_and_idempotency(db_session):
    source = FoodRepository.get_or_create_source(
        db=db_session,
        code="FIXTURE_TEST_SRC",
        name="Fixture Test Source",
        source_type="CURATED_INTERNAL",
    )

    fixture_items = [
        {
            "canonical_name": "Tahu Putih Kukus",
            "source_food_code": "TAHU_01",
            "food_category": "SOY_PRODUCT",
            "preparation_state": "STEAMED",
            "nutrients": {
                "energy_kcal": 78.0,
                "protein_g": 7.8,
                "fat_g": 4.6,
                "carbohydrate_g": 1.6,
                "fiber_g": 0.1,
                "basis_type": "PER_100_G_EDIBLE",
                "reference_amount": 100.0,
            },
            "servings": [{"serving_name": "1 potong sedang", "grams": 50.0}],
            "allergens": [{"allergen_type": "SOY", "relationship_type": "CONTAINS"}],
        },
        {
            "canonical_name": "Invalid Item Missing Code",
            "source_food_code": "",  # Missing code -> rejected
            "nutrients": {"energy_kcal": 100.0},
        },
    ]

    # 1. Dry Run Test
    dry_result = FoodImportPipeline.import_dataset(
        db=db_session,
        source_record=source,
        raw_items=fixture_items,
        dry_run=True,
    )
    assert dry_result.total_parsed == 2
    assert dry_result.valid_count == 1
    assert dry_result.rejected_count == 1
    assert dry_result.persisted_count == 0

    # 2. Persist Test
    persist_result = FoodImportPipeline.import_dataset(
        db=db_session,
        source_record=source,
        raw_items=fixture_items,
        dry_run=False,
    )
    assert persist_result.valid_count == 1
    assert persist_result.persisted_count == 1

    # 3. Idempotency Test (Importing again should not duplicate)
    repeat_result = FoodImportPipeline.import_dataset(
        db=db_session,
        source_record=source,
        raw_items=fixture_items,
        dry_run=False,
    )
    assert repeat_result.duplicate_count == 1
    assert repeat_result.persisted_count == 0


@pytest.mark.asyncio
async def test_api_food_search_detail_and_serving_calculation(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-food-test", "foods@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        # Setup seeded item in database
        source = FoodRepository.get_or_create_source(
            db=db_session,
            code="TKPI_SEEDED",
            name="Tabel Komposisi Pangan Indonesia",
            publisher="Kemenkes RI",
            publication_year=2020,
        )
        raw_foods = [
            {
                "canonical_name": "Telur Ayam Ras Rebus",
                "local_name": "Telur Rebus",
                "source_food_code": "TELUR_REBUS_01",
                "food_category": "EGG",
                "preparation_state": "BOILED",
                "nutrients": {
                    "energy_kcal": 155.0,
                    "protein_g": 13.0,
                    "fat_g": 11.0,
                    "carbohydrate_g": 1.1,
                    "fiber_g": None,
                    "basis_type": "PER_100_G_EDIBLE",
                    "reference_amount": 100.0,
                },
                "aliases": [{"alias": "Telur Rebus", "alias_type": "COMMON_NAME"}],
                "servings": [{"serving_name": "1 butir", "grams": 55.0}],
                "allergens": [{"allergen_type": "EGG", "relationship_type": "CONTAINS"}],
                "preparation_requirements": {
                    "requires_cooking": True,
                    "minimum_capability": "LIMITED",
                    "prep_complexity": "VERY_SIMPLE",
                    "required_equipment": ["STOVE"],
                },
            }
        ]
        FoodImportPipeline.import_dataset(db=db_session, source_record=source, raw_items=raw_foods, dry_run=False)

        # 1. Search by canonical name
        res_search = await client.get("/api/v1/foods/search?q=telur", headers=headers)
        assert res_search.status_code == 200
        search_data = res_search.json()
        assert search_data["total_matches"] >= 1
        found_food = search_data["results"][0]
        assert "Telur" in found_food["canonical_name"]
        food_id = found_food["id"]

        # 2. Get Food Detail
        res_detail = await client.get(f"/api/v1/foods/{food_id}", headers=headers)
        assert res_detail.status_code == 200
        detail_data = res_detail.json()
        assert detail_data["canonical_name"] == "Telur Ayam Ras Rebus"
        assert detail_data["source"]["code"] == "TKPI_SEEDED"
        assert detail_data["nutrients"]["energy_kcal"] == 155.0
        assert len(detail_data["servings"]) >= 1
        serving_id = detail_data["servings"][0]["id"]

        # 3. Calculate Serving by Grams (100g -> 155 kcal)
        res_calc_grams = await client.post(
            f"/api/v1/foods/{food_id}/calculate-serving",
            json={"grams": 100.0},
            headers=headers,
        )
        assert res_calc_grams.status_code == 200
        calc_grams_data = res_calc_grams.json()
        assert calc_grams_data["consumed_grams"] == 100.0
        assert calc_grams_data["scaled_nutrients"]["energy_kcal"] == 155.0
        assert calc_grams_data["scaled_nutrients"]["protein_g"] == 13.0

        # 4. Calculate Serving by Serving ID (1 butir = 55g -> (55/100)*155 = 85.25 kcal)
        res_calc_srv = await client.post(
            f"/api/v1/foods/{food_id}/calculate-serving",
            json={"serving_id": serving_id, "serving_count": 1.0},
            headers=headers,
        )
        assert res_calc_srv.status_code == 200
        calc_srv_data = res_calc_srv.json()
        assert calc_srv_data["consumed_grams"] == 55.0
        assert calc_srv_data["scaled_nutrients"]["energy_kcal"] == 85.25
        assert calc_srv_data["scaled_nutrients"]["protein_g"] == 7.15
        assert calc_srv_data["scaled_nutrients"]["fiber_g"] is None  # Preserves Null != 0
        assert calc_srv_data["source_provenance"]["code"] == "TKPI_SEEDED"

        # 5. Food Not Found
        res_not_found = await client.get("/api/v1/foods/non-existent-uuid-12345", headers=headers)
        assert res_not_found.status_code == 404
