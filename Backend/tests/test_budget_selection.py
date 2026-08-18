import pytest
import jwt
from typing import Dict, List, Optional
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.budget_selection.constants import (
    BudgetPeriod,
    BudgetSource,
    CandidateBudgetStatus,
    BudgetSelectionStatus,
    BudgetSelectionPolicy,
)
from app.budget_selection.models import (
    BudgetContextDTO,
    BudgetCandidateEvaluationDTO,
    DailyCandidateCombinationDTO,
    BudgetAwareSelectionInputDTO,
)
from app.budget_selection.budget_context import derive_daily_budget_envelope
from app.budget_selection.filters import evaluate_candidate_price_and_budget
from app.budget_selection.selector import select_budget_aware_candidates
from app.price_knowledge.constants import PriceConfidence, CostCompleteness, PriceBasis
from app.price_knowledge.models import CandidateCostEstimateDTO, ItemCostEstimateDTO
from app.food_candidates.constants import FoodPlannerRole, CandidateMatchStatus
from app.food_candidates.models import FoodCandidateSetDTO, FoodCandidateItemDTO


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def make_cand(cand_id: str, slot_id: str, energy: float = 500.0, match_status: CandidateMatchStatus = CandidateMatchStatus.STRICT_MATCH) -> FoodCandidateSetDTO:
    item = FoodCandidateItemDTO(
        food_item_id=f"f_{cand_id}",
        canonical_name=f"Food {cand_id}",
        role=FoodPlannerRole.STAPLE,
        serving_id=None,
        serving_name="1 serving",
        grams=100.0,
        energy_kcal=energy,
        protein_g=10.0,
        fat_g=5.0,
        carbohydrate_g=50.0,
    )
    return FoodCandidateSetDTO(
        candidate_id=cand_id,
        slot_id=slot_id,
        items=[item],
        total_energy_kcal=energy,
        total_protein_g=10.0,
        total_fat_g=5.0,
        total_carbohydrate_g=50.0,
        energy_deviation_kcal=0.0,
        absolute_energy_deviation=0.0,
        match_status=match_status,
    )


def make_cost(
    cand_id: str,
    cost_idr: Optional[int],
    completeness: CostCompleteness = CostCompleteness.COMPLETE,
    confidence: PriceConfidence = PriceConfidence.HIGH,
    uses_stale: bool = False,
    subtotal: int = 0,
) -> CandidateCostEstimateDTO:
    return CandidateCostEstimateDTO(
        candidate_id=cand_id,
        estimated_cost_idr=cost_idr,
        known_subtotal_idr=cost_idr if cost_idr is not None else subtotal,
        cost_completeness=completeness,
        priced_item_count=1 if completeness == CostCompleteness.COMPLETE else 0,
        total_item_count=1,
        item_costs=[],
        confidence=confidence,
        uses_stale_prices=uses_stale,
    )


def test_explicit_daily_budget_envelope_priority():
    ctx = BudgetContextDTO(
        budget_period=BudgetPeriod.WEEKLY,
        total_food_budget_idr=350000,
        remaining_food_budget_idr=350000,
        period_days_remaining=7,
        explicit_today_budget_idr=60000,  # Explicit daily override
    )
    env, status, _ = derive_daily_budget_envelope(ctx)
    assert env == 60000
    assert status == BudgetSelectionStatus.SELECTION_FOUND


def test_derived_weekly_budget_envelope_integer_safe():
    # 350.000 / 7 = 50.000
    ctx1 = BudgetContextDTO(
        budget_period=BudgetPeriod.WEEKLY,
        total_food_budget_idr=350000,
        remaining_food_budget_idr=350000,
        period_days_remaining=7,
    )
    env1, status1, _ = derive_daily_budget_envelope(ctx1)
    assert env1 == 50000
    assert status1 == BudgetSelectionStatus.SELECTION_FOUND

    # 100.000 // 3 = 33333 (integer-safe, no float)
    ctx2 = BudgetContextDTO(
        budget_period=BudgetPeriod.WEEKLY,
        total_food_budget_idr=100000,
        remaining_food_budget_idr=100000,
        period_days_remaining=3,
    )
    env2, status2, _ = derive_daily_budget_envelope(ctx2)
    assert env2 == 33333
    assert isinstance(env2, int)


def test_missing_spend_on_weekly_budget_returns_needs_more_budget_data():
    ctx = BudgetContextDTO(
        budget_period=BudgetPeriod.WEEKLY,
        total_food_budget_idr=350000,
        spent_food_budget_idr=None,
        remaining_food_budget_idr=None,
        period_days_remaining=5,
    )
    env, status, _ = derive_daily_budget_envelope(ctx)
    assert env is None
    assert status == BudgetSelectionStatus.NEEDS_MORE_BUDGET_DATA


def test_negative_remaining_budget_returns_budget_already_exceeded():
    ctx = BudgetContextDTO(
        budget_period=BudgetPeriod.MONTHLY,
        total_food_budget_idr=1500000,
        remaining_food_budget_idr=-50000,  # Negative
        period_days_remaining=10,
    )
    env, status, _ = derive_daily_budget_envelope(ctx)
    assert env is None
    assert status == BudgetSelectionStatus.BUDGET_ALREADY_EXCEEDED


def test_partial_cost_candidate_marked_unknown_cost_and_not_treated_as_cheap():
    cand = make_cand("cand_partial", "slot_1")
    cost = make_cost("cand_partial", cost_idr=None, completeness=CostCompleteness.PARTIAL, subtotal=8000)

    eval_dto = evaluate_candidate_price_and_budget(candidate=cand, cost_estimate=cost, budget_envelope_idr=50000)
    assert eval_dto.budget_status == CandidateBudgetStatus.UNKNOWN_COST
    assert eval_dto.estimated_cost_idr is None


def test_feasible_daily_selection_covering_all_slots_within_budget():
    slots = ["slot_breakfast", "slot_lunch", "slot_dinner"]
    cand_b = make_cand("cb", "slot_breakfast")
    cand_l = make_cand("cl", "slot_lunch")
    cand_d = make_cand("cd", "slot_dinner")

    costs = {
        "cb": make_cost("cb", 12000),
        "cl": make_cost("cl", 18000),
        "cd": make_cost("cd", 15000),
    }

    input_dto = BudgetAwareSelectionInputDTO(
        date="2026-08-19",
        logical_day_id="ld_20260819",
        slot_ids=slots,
        candidates_by_slot={
            "slot_breakfast": [cand_b],
            "slot_lunch": [cand_l],
            "slot_dinner": [cand_d],
        },
        candidate_costs_by_candidate_id=costs,
        budget_context=BudgetContextDTO(budget_period=BudgetPeriod.DAILY, total_food_budget_idr=50000),
    )

    res = select_budget_aware_candidates(input_dto)
    assert res.status == BudgetSelectionStatus.SELECTION_FOUND
    assert res.budget_envelope_idr == 50000
    assert res.selected_combination is not None
    assert res.selected_combination.total_estimated_cost_idr == 45000
    assert res.selected_combination.remaining_after_selection_idr == 5000
    assert len(res.selected_combination.selections) == 3


def test_nutrition_priority_strict_match_preferred_over_cheaper_near_match():
    # Slot has Strict (Rp 15k) and Near Match (Rp 10k). Budget is Rp 20k.
    cand_strict = make_cand("c_strict", "slot_1", match_status=CandidateMatchStatus.STRICT_MATCH)
    cand_near = make_cand("c_near", "slot_1", match_status=CandidateMatchStatus.NEAR_MATCH)

    costs = {
        "c_strict": make_cost("c_strict", 15000),
        "c_near": make_cost("c_near", 10000),
    }

    input_dto = BudgetAwareSelectionInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        slot_ids=["slot_1"],
        candidates_by_slot={"slot_1": [cand_near, cand_strict]},
        candidate_costs_by_candidate_id=costs,
        budget_context=BudgetContextDTO(budget_period=BudgetPeriod.DAILY, total_food_budget_idr=20000),
    )

    res = select_budget_aware_candidates(input_dto)
    assert res.status == BudgetSelectionStatus.SELECTION_FOUND
    assert res.selected_combination.selections["slot_1"].candidate_id == "c_strict"


def test_not_cheapest_by_default_preference_honored():
    # Both Strict. cand_pref costs Rp 15k with preference +10, cand_neutral costs Rp 12k with preference 0.
    # Budget is Rp 20k -> cand_pref selected!
    cand_pref = make_cand("c_pref", "slot_1")
    cand_neutral = make_cand("c_neutral", "slot_1")

    costs = {
        "c_pref": make_cost("c_pref", 15000),
        "c_neutral": make_cost("c_neutral", 12000),
    }

    input_dto = BudgetAwareSelectionInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        slot_ids=["slot_1"],
        candidates_by_slot={"slot_1": [cand_neutral, cand_pref]},
        candidate_costs_by_candidate_id=costs,
        budget_context=BudgetContextDTO(budget_period=BudgetPeriod.DAILY, total_food_budget_idr=20000),
        user_preferences_by_food_id={"f_c_pref": 10, "f_c_neutral": 0},
    )

    res = select_budget_aware_candidates(input_dto)
    assert res.status == BudgetSelectionStatus.SELECTION_FOUND
    assert res.selected_combination.selections["slot_1"].candidate_id == "c_pref"


def test_insufficient_budget_returns_no_budget_feasible_selection_with_shortfall():
    cand = make_cand("c_expensive", "slot_1")
    costs = {"c_expensive": make_cost("c_expensive", 36500)}

    input_dto = BudgetAwareSelectionInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        slot_ids=["slot_1"],
        candidates_by_slot={"slot_1": [cand]},
        candidate_costs_by_candidate_id=costs,
        budget_context=BudgetContextDTO(budget_period=BudgetPeriod.DAILY, total_food_budget_idr=30000),
    )

    res = select_budget_aware_candidates(input_dto)
    assert res.status == BudgetSelectionStatus.NO_BUDGET_FEASIBLE_SELECTION
    assert res.selected_combination is None
    assert res.shortfall_idr == 6500


def test_missing_price_data_distinguished_from_insufficient_budget():
    cand = make_cand("c_unpriced", "slot_1")
    costs = {"c_unpriced": make_cost("c_unpriced", None, completeness=CostCompleteness.UNAVAILABLE)}

    input_dto = BudgetAwareSelectionInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        slot_ids=["slot_1"],
        candidates_by_slot={"slot_1": [cand]},
        candidate_costs_by_candidate_id=costs,
        budget_context=BudgetContextDTO(budget_period=BudgetPeriod.DAILY, total_food_budget_idr=30000),
    )

    res = select_budget_aware_candidates(input_dto)
    assert res.status == BudgetSelectionStatus.NEEDS_MORE_PRICE_DATA
    assert res.selected_combination is None


def test_stale_prices_fallback_yields_selection_found_with_low_confidence_price():
    cand = make_cand("c_stale", "slot_1")
    costs = {"c_stale": make_cost("c_stale", 20000, uses_stale=True, confidence=PriceConfidence.LOW)}

    input_dto = BudgetAwareSelectionInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        slot_ids=["slot_1"],
        candidates_by_slot={"slot_1": [cand]},
        candidate_costs_by_candidate_id=costs,
        budget_context=BudgetContextDTO(budget_period=BudgetPeriod.DAILY, total_food_budget_idr=25000),
    )

    res = select_budget_aware_candidates(input_dto)
    assert res.status == BudgetSelectionStatus.SELECTION_FOUND_WITH_LOW_CONFIDENCE_PRICE
    assert res.selected_combination is not None
    assert res.selected_combination.uses_stale_prices is True


def test_per_slot_candidate_truncation_yields_search_incomplete_when_no_feasible_found():
    # Slot 1 has 20 candidates (> 15 per slot limit), but single slot combination search is only 15 iterations (< 5000)
    cands_s1 = [make_cand(f"c1_{i}", "slot_1") for i in range(20)]
    costs = {c.candidate_id: make_cost(c.candidate_id, 30000) for c in cands_s1}

    # Budget is Rp 25.000 (none fit)
    input_dto = BudgetAwareSelectionInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        slot_ids=["slot_1"],
        candidates_by_slot={"slot_1": cands_s1},
        candidate_costs_by_candidate_id=costs,
        budget_context=BudgetContextDTO(budget_period=BudgetPeriod.DAILY, total_food_budget_idr=25000),
    )

    res = select_budget_aware_candidates(input_dto)
    # Because slot 1 had 20 candidates and only 15 were searched, search_truncated must be True, and status SEARCH_INCOMPLETE!
    assert res.status == BudgetSelectionStatus.SEARCH_INCOMPLETE
    assert res.search_truncated is True
    assert res.shortfall_idr is None


def test_search_truncation_without_feasible_candidate_yields_search_incomplete():
    # Force search truncation by creating lots of combinations exceeding budget
    cands_s1 = [make_cand(f"c1_{i}", "slot_1") for i in range(15)]
    cands_s2 = [make_cand(f"c2_{i}", "slot_2") for i in range(15)]
    cands_s3 = [make_cand(f"c3_{i}", "slot_3") for i in range(15)]
    cands_s4 = [make_cand(f"c4_{i}", "slot_4") for i in range(15)]

    # All cost Rp 20.000 (total combo cost = 80.000)
    costs = {}
    for c in cands_s1 + cands_s2 + cands_s3 + cands_s4:
        costs[c.candidate_id] = make_cost(c.candidate_id, 20000)

    # Budget is Rp 50.000 (none will fit in 5000 evaluated combinations of 50625 total)
    input_dto = BudgetAwareSelectionInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        slot_ids=["slot_1", "slot_2", "slot_3", "slot_4"],
        candidates_by_slot={"slot_1": cands_s1, "slot_2": cands_s2, "slot_3": cands_s3, "slot_4": cands_s4},
        candidate_costs_by_candidate_id=costs,
        budget_context=BudgetContextDTO(budget_period=BudgetPeriod.DAILY, total_food_budget_idr=50000),
    )

    res = select_budget_aware_candidates(input_dto)
    assert res.status == BudgetSelectionStatus.SEARCH_INCOMPLETE
    assert res.search_truncated is True
    assert res.shortfall_idr is None  # Cannot claim exact shortfall under incomplete search!


def test_explicit_today_budget_exceeding_remaining_period_budget_yields_conflict():
    # User declares today budget 70k, but remaining weekly budget is only 40k
    ctx = BudgetContextDTO(
        budget_period=BudgetPeriod.WEEKLY,
        total_food_budget_idr=280000,
        remaining_food_budget_idr=40000,
        period_days_remaining=2,
        explicit_today_budget_idr=70000,
    )
    env, status, msg = derive_daily_budget_envelope(ctx)
    assert env is None
    assert status == BudgetSelectionStatus.BUDGET_CONTEXT_CONFLICT
    assert "exceeds remaining period budget" in msg


def test_invalid_period_days_remaining_zero_or_negative():
    # period_days_remaining <= 0 on multi-day period
    ctx = BudgetContextDTO(
        budget_period=BudgetPeriod.WEEKLY,
        total_food_budget_idr=350000,
        remaining_food_budget_idr=100000,
        period_days_remaining=0,  # Invalid
    )
    env, status, _ = derive_daily_budget_envelope(ctx)
    assert env is None
    assert status == BudgetSelectionStatus.NEEDS_MORE_BUDGET_DATA


def test_fresh_feasible_combination_strictly_preferred_over_cheaper_stale_fallback():
    # Fresh candidate (Rp 18.000) vs Stale candidate (Rp 10.000). Budget is Rp 20.000.
    cand_fresh = make_cand("c_fresh", "slot_1")
    cand_stale = make_cand("c_stale_opt", "slot_1")

    costs = {
        "c_fresh": make_cost("c_fresh", 18000, confidence=PriceConfidence.HIGH, uses_stale=False),
        "c_stale_opt": make_cost("c_stale_opt", 10000, confidence=PriceConfidence.LOW, uses_stale=True),
    }

    input_dto = BudgetAwareSelectionInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        slot_ids=["slot_1"],
        candidates_by_slot={"slot_1": [cand_stale, cand_fresh]},
        candidate_costs_by_candidate_id=costs,
        budget_context=BudgetContextDTO(budget_period=BudgetPeriod.DAILY, total_food_budget_idr=20000),
    )

    res = select_budget_aware_candidates(input_dto)
    # Must select fresh combination, NOT stale combination merely because it's cheaper!
    assert res.status == BudgetSelectionStatus.SELECTION_FOUND
    assert res.selected_combination.selections["slot_1"].candidate_id == "c_fresh"
    assert res.selected_combination.uses_stale_prices is False



@pytest.mark.asyncio
async def test_api_budget_selection_preview_authenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-budget-test", "budget@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "date": "2026-08-19",
            "logical_day_id": "ld_api_1",
            "slot_ids": ["slot_main"],
            "candidates_by_slot": {
                "slot_main": [
                    {
                        "candidate_id": "cand_api_main",
                        "slot_id": "slot_main",
                        "items": [
                            {
                                "food_item_id": "f_api_rice",
                                "canonical_name": "Nasi Putih",
                                "role": "STAPLE",
                                "serving_name": "100g",
                                "grams": 100.0,
                                "energy_kcal": 130.0,
                                "protein_g": 2.7,
                                "fat_g": 0.3,
                                "carbohydrate_g": 28.0,
                            }
                        ],
                        "total_energy_kcal": 130.0,
                        "total_protein_g": 2.7,
                        "total_fat_g": 0.3,
                        "total_carbohydrate_g": 28.0,
                        "energy_deviation_kcal": 0.0,
                        "absolute_energy_deviation": 0.0,
                        "match_status": "STRICT_MATCH",
                    }
                ]
            },
            "candidate_costs_by_candidate_id": {
                "cand_api_main": {
                    "candidate_id": "cand_api_main",
                    "estimated_cost_idr": 15000,
                    "known_subtotal_idr": 15000,
                    "cost_completeness": "COMPLETE",
                    "priced_item_count": 1,
                    "total_item_count": 1,
                    "item_costs": [],
                    "confidence": "HIGH",
                    "uses_stale_prices": False,
                }
            },
            "budget_context": {
                "budget_period": "DAILY",
                "total_food_budget_idr": 25000,
            },
        }

        res = await client.post("/api/v1/budget-selection/preview", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SELECTION_FOUND"
        assert data["budget_envelope_idr"] == 25000
        assert data["selected_combination"]["total_estimated_cost_idr"] == 15000
        assert data["selected_combination"]["remaining_after_selection_idr"] == 10000
