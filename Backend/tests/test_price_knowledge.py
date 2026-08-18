import pytest
import jwt
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.price_knowledge.constants import (
    PriceUnit,
    PriceBasis,
    PriceSourceType,
    PriceScopeType,
    PriceQuality,
    PriceConfidence,
    LocationMatch,
    PriceFreshness,
    PriceResolutionStatus,
    CostCompleteness,
    PricePolicy,
)
from app.price_knowledge.models import (
    LocationDTO,
    FoodPriceObservationDTO,
    ResolvedFoodPriceDTO,
)
from app.price_knowledge.units import normalize_to_base_unit, convert_quantity_to_base_units
from app.price_knowledge.freshness import determine_price_freshness
from app.price_knowledge.confidence import evaluate_location_match
from app.price_knowledge.aggregation import aggregate_normalized_rates
from app.price_knowledge.resolver import resolve_food_price
from app.price_knowledge.candidate_cost import estimate_candidate_cost
from app.price_knowledge.importer import PriceImportPipeline
from app.repositories.price_knowledge_repository import PriceKnowledgeRepository
from app.food_candidates.constants import FoodPlannerRole, CandidateMatchStatus
from app.food_candidates.models import FoodCandidateSetDTO, FoodCandidateItemDTO
from app.food_knowledge.models import (
    FoodKnowledgeItemDTO,
    NutrientProfileDTO,
    FoodServingDTO,
    SourceProvenanceDTO,
)
from app.food_knowledge.constants import (
    FoodCategory,
    PreparationState,
    FoodEntityType,
    BasisType,
    DataQualityStatus,
    NutrientCompleteness,
)
from app.repositories.food_repository import FoodRepository


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def make_obs(
    obs_id: str,
    food_id: str,
    amount: float,
    unit: PriceUnit,
    price_idr: int,
    city: Optional[str] = None,
    province: Optional[str] = None,
    days_ago: int = 5,
    is_promo: bool = False,
    package_grams: Optional[float] = None,
    price_basis: PriceBasis = PriceBasis.EDIBLE_PORTION,
) -> FoodPriceObservationDTO:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return FoodPriceObservationDTO(
        id=obs_id,
        food_item_id=food_id,
        amount=amount,
        unit=unit,
        price_idr=price_idr,
        price_basis=price_basis,
        location=LocationDTO(country="ID", province=province, city_regency=city),
        observed_at=dt,
        is_promotional=is_promo,
        package_quantity_grams=package_grams,
    )


def test_unit_normalization_mass_and_volume():
    # 1 kg = Rp 20.000 -> 20.0 Rp/g
    rate_kg, unit_kg = normalize_to_base_unit(1.0, PriceUnit.PER_KG, 20000)
    assert rate_kg == pytest.approx(20.0)
    assert unit_kg == "g"

    # 500 g = Rp 10.000 -> 20.0 Rp/g
    rate_g, unit_g = normalize_to_base_unit(500.0, PriceUnit.PER_GRAM, 10000)
    assert rate_g == pytest.approx(20.0)

    # 1 L = Rp 18.000 -> 18.0 Rp/ml
    rate_l, unit_l = normalize_to_base_unit(1.0, PriceUnit.PER_LITER, 18000)
    assert rate_l == pytest.approx(18.0)
    assert unit_l == "ml"


def test_no_ml_to_g_cross_dimensional_conversion_without_density():
    # Milk observation in 1 L, user requests 200 grams
    milk_obs = make_obs("obs_milk", "f_milk", 1.0, PriceUnit.PER_LITER, 18000)
    res = resolve_food_price(
        food_item_id="f_milk",
        requested_quantity=200.0,
        requested_unit=PriceUnit.PER_GRAM,  # Requested mass, but observation is volume!
        observations=[milk_obs],
    )
    assert res.resolution_status == PriceResolutionStatus.INCOMPATIBLE_UNIT
    assert res.estimated_cost_idr is None


def test_package_normalization_with_and_without_quantity():
    # 250 g package = Rp 10.000 -> Rp 40 / g
    rate_pkg, unit_pkg = normalize_to_base_unit(1.0, PriceUnit.PER_PACKAGE, 10000, package_quantity_grams=250.0)
    assert rate_pkg == pytest.approx(40.0)
    assert unit_pkg == "g"

    # Package without known grams fails safely
    rate_unknown, _ = normalize_to_base_unit(1.0, PriceUnit.PER_PACKAGE, 10000, package_quantity_grams=None)
    assert rate_unknown is None


def test_discrete_unit_pricing():
    # 1 egg = Rp 2.500 / unit, requested 2 units -> Rp 5.000
    egg_obs = make_obs("obs_egg", "f_egg", 1.0, PriceUnit.PER_UNIT, 2500)
    res = resolve_food_price(
        food_item_id="f_egg",
        requested_quantity=2.0,
        requested_unit=PriceUnit.PER_UNIT,
        observations=[egg_obs],
    )
    assert res.resolution_status == PriceResolutionStatus.RESOLVED_WITH_FALLBACK
    assert res.estimated_cost_idr == 5000


def test_missing_price_data_never_becomes_zero():
    # Food with no price records
    res = resolve_food_price(
        food_item_id="f_unknown_food",
        requested_quantity=100.0,
        requested_unit=PriceUnit.PER_GRAM,
        observations=[],
    )
    assert res.resolution_status == PriceResolutionStatus.NO_PRICE_DATA
    assert res.estimated_cost_idr is None  # Never Rp 0!


def test_candidate_cost_estimation_complete_partial_and_unavailable():
    # Rice = Rp 15 / g, Egg = Rp 50 / g
    obs_rice = make_obs("o1", "f_rice", 1000.0, PriceUnit.PER_GRAM, 15000)
    obs_egg = make_obs("o2", "f_egg", 100.0, PriceUnit.PER_GRAM, 5000)

    item_rice = FoodCandidateItemDTO("f_rice", "Nasi Putih", FoodPlannerRole.STAPLE, None, "100g", 100.0, 130.0, 2.7, 0.3, 28.0)
    item_egg = FoodCandidateItemDTO("f_egg", "Telur Ayam", FoodPlannerRole.PROTEIN_SOURCE, None, "50g", 50.0, 75.0, 6.0, 5.0, 0.5)
    item_veg = FoodCandidateItemDTO("f_veg", "Sayur Bayam", FoodPlannerRole.VEGETABLE, None, "50g", 50.0, 20.0, 1.0, 0.1, 3.0)

    # 1. Complete candidate (both items priced)
    cand_complete = FoodCandidateSetDTO(
        candidate_id="c_complete",
        slot_id="slot_1",
        items=[item_rice, item_egg],
        total_energy_kcal=205.0,
        total_protein_g=8.7,
        total_fat_g=5.3,
        total_carbohydrate_g=28.5,
        energy_deviation_kcal=0.0,
        absolute_energy_deviation=0.0,
        match_status=CandidateMatchStatus.STRICT_MATCH,
    )
    est_complete = estimate_candidate_cost(cand_complete, observations=[obs_rice, obs_egg])
    assert est_complete.cost_completeness == CostCompleteness.COMPLETE
    assert est_complete.estimated_cost_idr == (100 * 15) + (50 * 50)  # 1500 + 2500 = 4000
    assert est_complete.known_subtotal_idr == 4000

    # 2. Partial candidate (rice & egg priced, veg unpriced)
    cand_partial = FoodCandidateSetDTO(
        candidate_id="c_partial",
        slot_id="slot_1",
        items=[item_rice, item_egg, item_veg],
        total_energy_kcal=225.0,
        total_protein_g=9.7,
        total_fat_g=5.4,
        total_carbohydrate_g=31.5,
        energy_deviation_kcal=0.0,
        absolute_energy_deviation=0.0,
        match_status=CandidateMatchStatus.STRICT_MATCH,
    )
    est_partial = estimate_candidate_cost(cand_partial, observations=[obs_rice, obs_egg])
    assert est_partial.cost_completeness == CostCompleteness.PARTIAL
    assert est_partial.estimated_cost_idr is None  # Never present partial subtotal as complete total!
    assert est_partial.known_subtotal_idr == 4000
    assert est_partial.priced_item_count == 2
    assert est_partial.total_item_count == 3


def test_as_sold_vs_edible_portion_conversion_and_incompatible_basis_safety():
    # Banana price: Rp 20.000 / kg AS_SOLD (with peel)
    obs_banana = FoodPriceObservationDTO(
        id="o_banana",
        food_item_id="f_banana",
        amount=1.0,
        unit=PriceUnit.PER_KG,
        price_idr=20000,
        price_basis=PriceBasis.AS_SOLD,
        location=LocationDTO(country="ID", city_regency="Jakarta"),
    )

    # 1. Candidate requests 150g EDIBLE_PORTION with edible portion factor = 0.60 (60% flesh, 40% peel)
    # Effective as-sold weight = 150g / 0.60 = 250g as-sold.
    # Cost = 250g * (Rp 20.000 / 1000g) = Rp 5.000
    res_with_factor = resolve_food_price(
        food_item_id="f_banana",
        requested_quantity=150.0,
        requested_unit=PriceUnit.PER_GRAM,
        requested_basis=PriceBasis.EDIBLE_PORTION,
        edible_portion_factor=0.60,
        user_location=LocationDTO(country="ID", city_regency="Jakarta"),
        observations=[obs_banana],
    )
    assert res_with_factor.resolution_status in (PriceResolutionStatus.RESOLVED, PriceResolutionStatus.RESOLVED_WITH_FALLBACK)
    assert res_with_factor.estimated_cost_idr == 5000
    assert res_with_factor.edible_portion_factor_applied == 0.60

    # 2. Candidate requests 150g EDIBLE_PORTION without edible portion factor
    # Invariant: Must NOT silently compute 150g * 20 Rp/g = Rp 3.000!
    res_no_factor = resolve_food_price(
        food_item_id="f_banana",
        requested_quantity=150.0,
        requested_unit=PriceUnit.PER_GRAM,
        requested_basis=PriceBasis.EDIBLE_PORTION,
        edible_portion_factor=None,  # Missing factor!
        user_location=LocationDTO(country="ID", city_regency="Jakarta"),
        observations=[obs_banana],
    )
    assert res_no_factor.resolution_status == PriceResolutionStatus.INCOMPATIBLE_BASIS
    assert res_no_factor.estimated_cost_idr is None


def test_source_quality_impact_on_confidence():
    loc = LocationDTO(country="ID", city_regency="Surabaya")

    # 1. Verified Government source -> HIGH confidence
    obs_gov = FoodPriceObservationDTO(
        id="o_gov",
        food_item_id="f_rice",
        amount=1.0,
        unit=PriceUnit.PER_KG,
        price_idr=15000,
        price_basis=PriceBasis.EDIBLE_PORTION,
        source_type=PriceSourceType.GOVERNMENT_DATA,
        quality_status=PriceQuality.VERIFIED,
        location=loc,
    )
    res_gov = resolve_food_price("f_rice", 1000.0, PriceUnit.PER_GRAM, user_location=loc, observations=[obs_gov])
    assert res_gov.confidence == PriceConfidence.HIGH

    # 2. User Reported source -> MEDIUM confidence (even if local & fresh)
    obs_user = FoodPriceObservationDTO(
        id="o_user",
        food_item_id="f_rice",
        amount=1.0,
        unit=PriceUnit.PER_KG,
        price_idr=15000,
        price_basis=PriceBasis.EDIBLE_PORTION,
        source_type=PriceSourceType.USER_REPORTED,
        quality_status=PriceQuality.USER_REPORTED,
        location=loc,
    )
    res_user = resolve_food_price("f_rice", 1000.0, PriceUnit.PER_GRAM, user_location=loc, observations=[obs_user])
    assert res_user.confidence == PriceConfidence.MEDIUM


def test_stale_only_candidate_cost_preserves_completeness_with_stale_flag():
    # 120 days old observations (STALE)
    dt_stale = datetime.now(timezone.utc) - timedelta(days=120)
    obs_stale_rice = FoodPriceObservationDTO("o_sr", "f_rice", 1000.0, PriceUnit.PER_GRAM, 15000, price_basis=PriceBasis.EDIBLE_PORTION, observed_at=dt_stale)
    obs_stale_egg = FoodPriceObservationDTO("o_se", "f_egg", 100.0, PriceUnit.PER_GRAM, 5000, price_basis=PriceBasis.EDIBLE_PORTION, observed_at=dt_stale)

    item_rice = FoodCandidateItemDTO("f_rice", "Nasi Putih", FoodPlannerRole.STAPLE, None, "100g", 100.0, 130.0, 2.7, 0.3, 28.0)
    item_egg = FoodCandidateItemDTO("f_egg", "Telur Ayam", FoodPlannerRole.PROTEIN_SOURCE, None, "50g", 50.0, 75.0, 6.0, 5.0, 0.5)

    cand = FoodCandidateSetDTO(
        candidate_id="c_stale_cand",
        slot_id="slot_1",
        items=[item_rice, item_egg],
        total_energy_kcal=205.0,
        total_protein_g=8.7,
        total_fat_g=5.3,
        total_carbohydrate_g=28.5,
        energy_deviation_kcal=0.0,
        absolute_energy_deviation=0.0,
        match_status=CandidateMatchStatus.STRICT_MATCH,
    )

    est = estimate_candidate_cost(cand, observations=[obs_stale_rice, obs_stale_egg])
    assert est.cost_completeness == CostCompleteness.COMPLETE
    assert est.estimated_cost_idr == 4000
    assert est.uses_stale_prices is True
    assert est.confidence == PriceConfidence.LOW  # Weakest link is LOW due to stale data!


def test_location_fallback_hierarchy():
    # Bandung vs West Java vs National
    obs_bandung = make_obs("o_bdg", "f_rice", 1000.0, PriceUnit.PER_GRAM, 14000, city="Bandung", province="Jawa Barat")
    obs_jabar = make_obs("o_jbr", "f_rice", 1000.0, PriceUnit.PER_GRAM, 15000, city="Bogor", province="Jawa Barat")
    obs_national = make_obs("o_nat", "f_rice", 1000.0, PriceUnit.PER_GRAM, 16000)

    user_loc = LocationDTO(country="ID", province="Jawa Barat", city_regency="Bandung")

    # 1. Exact city match available -> chooses Bandung (Rp 14/g)
    res_bdg = resolve_food_price(
        food_item_id="f_rice",
        requested_quantity=100.0,
        requested_unit=PriceUnit.PER_GRAM,
        user_location=user_loc,
        observations=[obs_bandung, obs_jabar, obs_national],
    )
    assert res_bdg.location_match == LocationMatch.SAME_CITY
    assert res_bdg.estimated_cost_idr == 1400

    # 2. No city match, but same province available -> chooses Jawa Barat (Rp 15/g)
    res_jbr = resolve_food_price(
        food_item_id="f_rice",
        requested_quantity=100.0,
        requested_unit=PriceUnit.PER_GRAM,
        user_location=user_loc,
        observations=[obs_jabar, obs_national],
    )
    assert res_jbr.location_match == LocationMatch.SAME_PROVINCE
    assert res_jbr.estimated_cost_idr == 1500


def test_median_aggregation_robust_to_outliers():
    # Observations: [10000, 11000, 12000, 50000] for 1 kg -> rates: [10, 11, 12, 50]
    # Median is (11 + 12)/2 = 11.5
    obs1 = make_obs("o1", "f_rice", 1.0, PriceUnit.PER_KG, 10000, city="Jakarta")
    obs2 = make_obs("o2", "f_rice", 1.0, PriceUnit.PER_KG, 11000, city="Jakarta")
    obs3 = make_obs("o3", "f_rice", 1.0, PriceUnit.PER_KG, 12000, city="Jakarta")
    obs4 = make_obs("o4", "f_rice", 1.0, PriceUnit.PER_KG, 50000, city="Jakarta")  # Outlier

    user_loc = LocationDTO(country="ID", city_regency="Jakarta")
    res = resolve_food_price(
        food_item_id="f_rice",
        requested_quantity=1000.0,
        requested_unit=PriceUnit.PER_GRAM,
        user_location=user_loc,
        observations=[obs1, obs2, obs3, obs4],
    )
    assert res.normalized_unit_price_idr == pytest.approx(11.5)
    assert res.estimated_cost_idr == 11500


def test_promotional_isolation():
    obs_normal = make_obs("o_norm", "f_egg", 1.0, PriceUnit.PER_UNIT, 2500, is_promo=False)
    obs_promo = make_obs("o_promo", "f_egg", 1.0, PriceUnit.PER_UNIT, 1000, is_promo=True)

    # By default, promo is excluded
    res_default = resolve_food_price(
        food_item_id="f_egg",
        requested_quantity=1.0,
        requested_unit=PriceUnit.PER_UNIT,
        observations=[obs_normal, obs_promo],
        include_promotions=False,
    )
    assert res_default.estimated_cost_idr == 2500

    # Explicitly include promo
    res_promo = resolve_food_price(
        food_item_id="f_egg",
        requested_quantity=1.0,
        requested_unit=PriceUnit.PER_UNIT,
        observations=[obs_promo],
        include_promotions=True,
    )
    assert res_promo.estimated_cost_idr == 1000


def test_importer_idempotency_and_validation(db_session):
    source = PriceKnowledgeRepository.get_or_create_source(
        db=db_session,
        name="PIHPS Pasar Tradisional",
        source_type=PriceSourceType.GOVERNMENT_DATA,
        publisher="Bank Indonesia",
    )

    raw_data = [
        {
            "food_item_id": "f_rice_db",
            "amount": 1.0,
            "unit": "PER_KG",
            "price_idr": 15000,
            "city_regency": "Surabaya",
        },
        {
            "food_item_id": "f_invalid_price",
            "amount": 1.0,
            "unit": "PER_KG",
            "price_idr": -500,  # Invalid price <= 0
        },
    ]

    # First import
    res1 = PriceImportPipeline.import_price_dataset(db=db_session, source_record=source, raw_items=raw_data, dry_run=False)
    assert res1["inserted_records"] == 1
    assert res1["rejected_records"] == 1

    # Second import (idempotent skip)
    res2 = PriceImportPipeline.import_price_dataset(db=db_session, source_record=source, raw_items=raw_data, dry_run=False)
    assert res2["inserted_records"] == 0


def test_user_ownership_isolation_rls(db_session):
    source = PriceKnowledgeRepository.get_or_create_source(db=db_session, name="User Uploads")

    # Global price
    PriceKnowledgeRepository.add_observation(
        db=db_session,
        food_item_id="f_rice_rls",
        amount=1.0,
        unit=PriceUnit.PER_KG,
        price_idr=14000,
        scope_type=PriceScopeType.GLOBAL_REFERENCE,
        source_id=source.id,
    )

    # User A private price
    PriceKnowledgeRepository.add_observation(
        db=db_session,
        food_item_id="f_rice_rls",
        amount=1.0,
        unit=PriceUnit.PER_KG,
        price_idr=12000,
        scope_type=PriceScopeType.USER_PRIVATE,
        owner_user_id="user_a",
        source_id=source.id,
    )

    # User B private price
    PriceKnowledgeRepository.add_observation(
        db=db_session,
        food_item_id="f_rice_rls",
        amount=1.0,
        unit=PriceUnit.PER_KG,
        price_idr=18000,
        scope_type=PriceScopeType.USER_PRIVATE,
        owner_user_id="user_b",
        source_id=source.id,
    )

    # User A sees global + User A private (2 records), cannot see User B private
    obs_a = PriceKnowledgeRepository.get_observations_for_food(db=db_session, food_item_id="f_rice_rls", user_id="user_a")
    assert len(obs_a) == 2
    prices_a = [o.price_idr for o in obs_a]
    assert 14000 in prices_a
    assert 12000 in prices_a
    assert 18000 not in prices_a


@pytest.mark.asyncio
async def test_api_price_endpoints_authenticated(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-price-test", "price@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        source = PriceKnowledgeRepository.get_or_create_source(
            db=db_session,
            name="Test Market Feed",
            source_type=PriceSourceType.MANUAL_CURATED,
        )

        PriceKnowledgeRepository.add_observation(
            db=db_session,
            food_item_id="f_api_egg",
            amount=1.0,
            unit=PriceUnit.PER_UNIT,
            price_idr=2500,
            source_id=source.id,
            location=LocationDTO(country="ID", city_regency="Semarang"),
        )

        # 1. GET /api/v1/prices/foods/{food_id}
        res_get = await client.get("/api/v1/prices/foods/f_api_egg", headers=headers)
        assert res_get.status_code == 200
        data_get = res_get.json()
        assert len(data_get) >= 1
        assert data_get[0]["price_idr"] == 2500

        # 2. POST /api/v1/prices/resolve
        resolve_payload = {
            "food_item_id": "f_api_egg",
            "requested_quantity": 4.0,
            "requested_unit": "PER_UNIT",
            "user_location": {"country": "ID", "city_regency": "Semarang"},
        }
        res_resolve = await client.post("/api/v1/prices/resolve", json=resolve_payload, headers=headers)
        assert res_resolve.status_code == 200
        data_res = res_resolve.json()
        assert data_res["estimated_cost_idr"] == 10000
        assert data_res["resolution_status"] in ("RESOLVED", "RESOLVED_WITH_FALLBACK")
