import pytest
import jwt
from typing import Dict, List, Optional
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.daily_nutrition_plan.constants import (
    DailyPlanStatus,
    DailyPlanWarningSeverity,
    DailyPlanWarningCode,
    MacroCompleteness,
    DailyPlanPolicy,
)
from app.daily_nutrition_plan.models import (
    DailyNutritionPlanAssemblyInputDTO,
    DailyNutritionPlanDTO,
)
from app.daily_nutrition_plan.assembler import assemble_daily_nutrition_plan
from app.daily_nutrition_plan.ordering import order_meal_entries_by_waking_day
from app.daily_nutrition_plan.aggregation import aggregate_daily_nutrition, aggregate_daily_budget
from app.food_candidates.constants import FoodPlannerRole, CandidateMatchStatus
from app.food_candidates.models import FoodCandidateSetDTO, FoodCandidateItemDTO
from app.price_knowledge.constants import PriceConfidence, CostCompleteness
from app.price_knowledge.models import CandidateCostEstimateDTO
from app.budget_selection.constants import BudgetSelectionStatus, BudgetSource, CandidateBudgetStatus
from app.budget_selection.models import (
    BudgetAwareSelectionResultDTO,
    DailyCandidateCombinationDTO,
    BudgetCandidateEvaluationDTO,
)


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def make_candidate(
    cand_id: str,
    slot_id: str,
    energy: float = 600.0,
    protein: Optional[float] = 30.0,
    fat: Optional[float] = 15.0,
    carbs: Optional[float] = 80.0,
    match_status: CandidateMatchStatus = CandidateMatchStatus.STRICT_MATCH,
) -> FoodCandidateSetDTO:
    item = FoodCandidateItemDTO(
        food_item_id=f"f_{cand_id}",
        canonical_name=f"Food {cand_id}",
        role=FoodPlannerRole.STAPLE,
        serving_id=None,
        serving_name="1 porsi",
        grams=150.0,
        energy_kcal=energy,
        protein_g=protein,
        fat_g=fat,
        carbohydrate_g=carbs,
    )
    return FoodCandidateSetDTO(
        candidate_id=cand_id,
        slot_id=slot_id,
        items=[item],
        total_energy_kcal=energy,
        total_protein_g=protein,
        total_fat_g=fat,
        total_carbohydrate_g=carbs,
        energy_deviation_kcal=0.0,
        absolute_energy_deviation=0.0,
        match_status=match_status,
        explanations=["Strict energy match"],
    )


def make_cost(
    cand_id: str,
    cost_idr: int = 15000,
    confidence: PriceConfidence = PriceConfidence.HIGH,
    uses_stale: bool = False,
    completeness: CostCompleteness = CostCompleteness.COMPLETE,
) -> CandidateCostEstimateDTO:
    return CandidateCostEstimateDTO(
        candidate_id=cand_id,
        estimated_cost_idr=cost_idr,
        known_subtotal_idr=cost_idr,
        cost_completeness=completeness,
        priced_item_count=1,
        total_item_count=1,
        item_costs=[],
        confidence=confidence,
        uses_stale_prices=uses_stale,
    )


def make_bs_result(
    slot_ids: List[str],
    cand_map: Dict[str, FoodCandidateSetDTO],
    cost_map: Dict[str, CandidateCostEstimateDTO],
    envelope_idr: int = 50000,
    status: BudgetSelectionStatus = BudgetSelectionStatus.SELECTION_FOUND,
    search_truncated: bool = False,
) -> BudgetAwareSelectionResultDTO:
    total_cost = sum(cost_map[c.candidate_id].estimated_cost_idr or 0 for c in cand_map.values())
    selections = {
        slot: BudgetCandidateEvaluationDTO(
            candidate_id=cand.candidate_id,
            slot_id=slot,
            estimated_cost_idr=cost_map[cand.candidate_id].estimated_cost_idr,
            budget_status=CandidateBudgetStatus.WITHIN_BUDGET,
            price_confidence=cost_map[cand.candidate_id].confidence,
            uses_stale_prices=cost_map[cand.candidate_id].uses_stale_prices,
            nutrition_fit_status=cand.match_status,
        )
        for slot, cand in cand_map.items()
    }
    comb = DailyCandidateCombinationDTO(
        combination_id="comb_test_1",
        selections=selections,
        total_estimated_cost_idr=total_cost,
        budget_envelope_idr=envelope_idr,
        remaining_after_selection_idr=envelope_idr - total_cost,
        price_confidence=PriceConfidence.HIGH,
        uses_stale_prices=any(c.uses_stale_prices for c in cost_map.values()),
        nutrition_deviation_score=0.0,
        preference_score=0,
        all_strict_nutrition=all(c.match_status == CandidateMatchStatus.STRICT_MATCH for c in cand_map.values()),
    )
    return BudgetAwareSelectionResultDTO(
        date="2026-08-19",
        logical_day_id="ld_20260819",
        status=status,
        budget_envelope_idr=envelope_idr,
        selected_combination=comb if status == BudgetSelectionStatus.SELECTION_FOUND else None,
        alternatives=[],
        search_truncated=search_truncated,
    )


def test_readiness_gate_nutrition_eligibility_out_of_scope():
    cand = make_candidate("c1", "slot_1")
    cost = make_cost("c1", 15000)
    sched = {"logical_day_id": "ld_1", "status": "FEASIBLE", "slots": [{"slot_id": "slot_1", "target_time": "12:00"}]}
    bs = make_bs_result(["slot_1"], {"slot_1": cand}, {"c1": cost})
    bs.logical_day_id = "ld_1"

    inp = DailyNutritionPlanAssemblyInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        target_energy_kcal=2000.0,
        nutrition_eligibility_status="OUT_OF_SCOPE",
        meal_schedule=sched,
        budget_selection_result=bs,
        selected_candidates_by_slot={"slot_1": cand},
        candidate_costs_by_candidate_id={"c1": cost},
    )
    plan = assemble_daily_nutrition_plan(inp)
    assert plan.status == DailyPlanStatus.NOT_ELIGIBLE
    assert len(plan.meal_entries) == 0


def test_readiness_gate_meal_schedule_infeasible():
    cand = make_candidate("c1", "slot_1")
    cost = make_cost("c1", 15000)
    sched = {"logical_day_id": "ld_1", "status": "INFEASIBLE", "slots": [{"slot_id": "slot_1", "target_time": "12:00"}]}
    bs = make_bs_result(["slot_1"], {"slot_1": cand}, {"c1": cost})
    bs.logical_day_id = "ld_1"

    inp = DailyNutritionPlanAssemblyInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        target_energy_kcal=2000.0,
        nutrition_eligibility_status="ELIGIBLE",
        meal_schedule=sched,
        budget_selection_result=bs,
        selected_candidates_by_slot={"slot_1": cand},
        candidate_costs_by_candidate_id={"c1": cost},
    )
    plan = assemble_daily_nutrition_plan(inp)
    assert plan.status == DailyPlanStatus.INFEASIBLE


def test_readiness_gate_budget_selection_search_incomplete():
    cand = make_candidate("c1", "slot_1")
    cost = make_cost("c1", 15000)
    sched = {"logical_day_id": "ld_1", "status": "FEASIBLE", "slots": [{"slot_id": "slot_1", "target_time": "12:00"}]}
    bs = make_bs_result(["slot_1"], {"slot_1": cand}, {"c1": cost}, status=BudgetSelectionStatus.SEARCH_INCOMPLETE)
    bs.logical_day_id = "ld_1"

    inp = DailyNutritionPlanAssemblyInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        target_energy_kcal=2000.0,
        nutrition_eligibility_status="ELIGIBLE",
        meal_schedule=sched,
        budget_selection_result=bs,
        selected_candidates_by_slot={"slot_1": cand},
        candidate_costs_by_candidate_id={"c1": cost},
    )
    plan = assemble_daily_nutrition_plan(inp)
    assert plan.status == DailyPlanStatus.SEARCH_INCOMPLETE


def test_slot_integrity_missing_slot_fails_assembly():
    cand1 = make_candidate("c1", "slot_1")
    cost1 = make_cost("c1", 15000)
    sched = {
        "logical_day_id": "ld_1",
        "status": "FEASIBLE",
        "slots": [{"slot_id": "slot_1", "target_time": "08:00"}, {"slot_id": "slot_2", "target_time": "13:00"}],
    }
    # Only slot_1 provided in selected candidates (slot_2 missing!)
    bs = make_bs_result(["slot_1"], {"slot_1": cand1}, {"c1": cost1})
    bs.logical_day_id = "ld_1"

    inp = DailyNutritionPlanAssemblyInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        target_energy_kcal=2000.0,
        nutrition_eligibility_status="ELIGIBLE",
        meal_schedule=sched,
        budget_selection_result=bs,
        selected_candidates_by_slot={"slot_1": cand1},
        candidate_costs_by_candidate_id={"c1": cost1},
    )
    plan = assemble_daily_nutrition_plan(inp)
    assert plan.status == DailyPlanStatus.INFEASIBLE


def test_cost_consistency_mismatch_fails_assembly():
    cand1 = make_candidate("c1", "slot_1")
    cost1 = make_cost("c1", 15000)
    sched = {"logical_day_id": "ld_1", "status": "FEASIBLE", "slots": [{"slot_id": "slot_1", "target_time": "12:00"}]}
    bs = make_bs_result(["slot_1"], {"slot_1": cand1}, {"c1": cost1})
    bs.logical_day_id = "ld_1"
    # Artificially alter budget selection total to 16.000 (mismatch with 15.000)
    bs.selected_combination.total_estimated_cost_idr = 16000

    inp = DailyNutritionPlanAssemblyInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        target_energy_kcal=2000.0,
        nutrition_eligibility_status="ELIGIBLE",
        meal_schedule=sched,
        budget_selection_result=bs,
        selected_candidates_by_slot={"slot_1": cand1},
        candidate_costs_by_candidate_id={"c1": cost1},
    )
    plan = assemble_daily_nutrition_plan(inp)
    assert plan.status == DailyPlanStatus.INFEASIBLE


def test_cross_midnight_waking_day_chronological_ordering():
    cand1 = make_candidate("c1", "s_night", energy=600)
    cand2 = make_candidate("c2", "s_wake", energy=700)
    cand3 = make_candidate("c3", "s_mid", energy=800)

    costs = {"c1": make_cost("c1", 15000), "c2": make_cost("c2", 15000), "c3": make_cost("c3", 15000)}

    # Wake time is 15:00. Meals: 16:00 (s_wake), 21:00 (s_mid), 01:00 (s_night)
    sched = {
        "logical_day_id": "ld_cross",
        "wake_time": "15:00",
        "status": "FEASIBLE",
        "slots": [
            {"slot_id": "s_night", "target_time": "01:00"},
            {"slot_id": "s_wake", "target_time": "16:00"},
            {"slot_id": "s_mid", "target_time": "21:00"},
        ],
    }

    c_map = {"s_night": cand1, "s_wake": cand2, "s_mid": cand3}
    bs = make_bs_result(["s_night", "s_wake", "s_mid"], c_map, costs)
    bs.logical_day_id = "ld_cross"

    inp = DailyNutritionPlanAssemblyInputDTO(
        date="2026-08-19",
        logical_day_id="ld_cross",
        target_energy_kcal=2100.0,
        nutrition_eligibility_status="ELIGIBLE",
        meal_schedule=sched,
        budget_selection_result=bs,
        selected_candidates_by_slot=c_map,
        candidate_costs_by_candidate_id=costs,
    )
    plan = assemble_daily_nutrition_plan(inp)
    assert plan.status == DailyPlanStatus.READY
    # Chronological waking day order: 16:00 -> 21:00 -> 01:00
    assert plan.meal_entries[0].scheduled_time == "16:00"
    assert plan.meal_entries[1].scheduled_time == "21:00"
    assert plan.meal_entries[2].scheduled_time == "01:00"


def test_macro_aggregation_with_missing_macro_partial_not_zero():
    # cand1 has complete macros, cand2 has missing protein & fat
    cand1 = make_candidate("c1", "s1", energy=500, protein=25.0, fat=10.0, carbs=70.0)
    cand2 = make_candidate("c2", "s2", energy=500, protein=None, fat=None, carbs=80.0)

    costs = {"c1": make_cost("c1", 10000), "c2": make_cost("c2", 10000)}
    sched = {
        "logical_day_id": "ld_1",
        "status": "FEASIBLE",
        "slots": [{"slot_id": "s1", "target_time": "08:00"}, {"slot_id": "s2", "target_time": "13:00"}],
    }
    c_map = {"s1": cand1, "s2": cand2}
    bs = make_bs_result(["s1", "s2"], c_map, costs)
    bs.logical_day_id = "ld_1"

    inp = DailyNutritionPlanAssemblyInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        target_energy_kcal=1000.0,
        nutrition_eligibility_status="ELIGIBLE",
        meal_schedule=sched,
        budget_selection_result=bs,
        selected_candidates_by_slot=c_map,
        candidate_costs_by_candidate_id=costs,
    )
    plan = assemble_daily_nutrition_plan(inp)
    assert plan.status == DailyPlanStatus.READY_WITH_WARNINGS
    assert plan.nutrition_summary.macro_completeness == MacroCompleteness.PARTIAL
    # Invariant: unknown != 0. Since cand2 lacks protein and fat, aggregate planned_protein_g is None!
    assert plan.nutrition_summary.planned_protein_g is None
    assert plan.nutrition_summary.planned_fat_g is None
    assert any(w.code == DailyPlanWarningCode.PARTIAL_MACRO_DATA for w in plan.warnings)


def test_stale_and_low_confidence_price_warnings():
    cand1 = make_candidate("c1", "s1")
    cost1 = make_cost("c1", 15000, confidence=PriceConfidence.LOW, uses_stale=True)
    sched = {"logical_day_id": "ld_1", "status": "FEASIBLE", "slots": [{"slot_id": "s1", "target_time": "12:00"}]}
    c_map = {"s1": cand1}
    bs = make_bs_result(["s1"], c_map, {"c1": cost1})
    bs.logical_day_id = "ld_1"

    inp = DailyNutritionPlanAssemblyInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        target_energy_kcal=600.0,
        nutrition_eligibility_status="ELIGIBLE",
        meal_schedule=sched,
        budget_selection_result=bs,
        selected_candidates_by_slot=c_map,
        candidate_costs_by_candidate_id={"c1": cost1},
    )
    plan = assemble_daily_nutrition_plan(inp)
    assert plan.status == DailyPlanStatus.READY_WITH_WARNINGS
    codes = [w.code for w in plan.warnings]
    assert DailyPlanWarningCode.STALE_PRICE_USED in codes
    assert DailyPlanWarningCode.LOW_CONFIDENCE_PRICE in codes


def test_deterministic_plan_id_reproducibility():
    cand1 = make_candidate("c1", "s1")
    cost1 = make_cost("c1", 15000)
    sched = {"logical_day_id": "ld_1", "status": "FEASIBLE", "slots": [{"slot_id": "s1", "target_time": "12:00"}]}
    c_map = {"s1": cand1}
    bs = make_bs_result(["s1"], c_map, {"c1": cost1})
    bs.logical_day_id = "ld_1"

    inp1 = DailyNutritionPlanAssemblyInputDTO(
        date="2026-08-19",
        logical_day_id="ld_1",
        target_energy_kcal=600.0,
        nutrition_eligibility_status="ELIGIBLE",
        meal_schedule=sched,
        budget_selection_result=bs,
        selected_candidates_by_slot=c_map,
        candidate_costs_by_candidate_id={"c1": cost1},
    )
    plan1 = assemble_daily_nutrition_plan(inp1)
    plan2 = assemble_daily_nutrition_plan(inp1)

    assert plan1.plan_id == plan2.plan_id
    assert plan1.status == DailyPlanStatus.READY


@pytest.mark.asyncio
async def test_api_daily_nutrition_plan_preview_authenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-plan-test", "plan@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "date": "2026-08-19",
            "logical_day_id": "ld_api_plan",
            "target_energy_kcal": 2000.0,
            "nutrition_eligibility_status": "ELIGIBLE",
            "meal_schedule": {
                "date": "2026-08-19",
                "logical_day_id": "ld_api_plan",
                "structure_state": "BASELINE",
                "step_index": 0,
                "energy_target_kcal": 2000.0,
                "feasibility": "FEASIBLE",
                "slots": [
                    {
                        "slot_id": "slot_m1",
                        "slot_type": "MAIN_MEAL",
                        "sequence": 1,
                        "preferred_time": "08:00",
                        "earliest_time": "07:30",
                        "latest_time": "08:30",
                        "duration_minutes": 30,
                        "target_kcal": 650.0,
                        "min_kcal": 550.0,
                        "max_kcal": 750.0,
                        "schedule_source": "BASELINE_OBSERVED",
                        "reason_code": "BASELINE_TIME_PRESERVED",
                        "window_type": "FLEXIBLE",
                        "is_user_fixed": False,
                    }
                ],
                "explanation": "Feasible meal schedule",
                "meal_structure_ready": True,
            },
            "budget_selection_result": {
                "date": "2026-08-19",
                "logical_day_id": "ld_api_plan",
                "status": "SELECTION_FOUND",
                "budget_envelope_idr": 40000,
                "selected_combination": {
                    "combination_id": "comb_api_1",
                    "selections": {
                        "slot_m1": {
                            "candidate_id": "cand_m1",
                            "slot_id": "slot_m1",
                            "estimated_cost_idr": 18000,
                            "budget_status": "WITHIN_BUDGET",
                            "price_confidence": "HIGH",
                            "uses_stale_prices": False,
                            "nutrition_fit_status": "STRICT_MATCH",
                        }
                    },
                    "total_estimated_cost_idr": 18000,
                    "budget_envelope_idr": 40000,
                    "remaining_after_selection_idr": 22000,
                    "price_confidence": "HIGH",
                    "uses_stale_prices": False,
                    "nutrition_deviation_score": 0.0,
                    "preference_score": 0,
                    "all_strict_nutrition": True,
                },
                "alternatives": [],
                "search_truncated": False,
            },
            "selected_candidates_by_slot": {
                "slot_m1": {
                    "candidate_id": "cand_m1",
                    "slot_id": "slot_m1",
                    "items": [
                        {
                            "food_item_id": "f_rice",
                            "canonical_name": "Nasi Putih",
                            "role": "STAPLE",
                            "serving_name": "150g",
                            "grams": 150.0,
                            "energy_kcal": 195.0,
                            "protein_g": 4.0,
                            "fat_g": 0.5,
                            "carbohydrate_g": 42.0,
                        }
                    ],
                    "total_energy_kcal": 195.0,
                    "total_protein_g": 4.0,
                    "total_fat_g": 0.5,
                    "total_carbohydrate_g": 42.0,
                    "energy_deviation_kcal": 0.0,
                    "absolute_energy_deviation": 0.0,
                    "match_status": "STRICT_MATCH",
                }
            },
            "candidate_costs_by_candidate_id": {
                "cand_m1": {
                    "candidate_id": "cand_m1",
                    "estimated_cost_idr": 18000,
                    "known_subtotal_idr": 18000,
                    "cost_completeness": "COMPLETE",
                    "priced_item_count": 1,
                    "total_item_count": 1,
                    "item_costs": [],
                    "confidence": "HIGH",
                    "uses_stale_prices": False,
                }
            },
        }

        res = await client.post("/api/v1/daily-nutrition-plan/preview", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "READY"
        assert data["logical_day_id"] == "ld_api_plan"
        assert data["nutrition_summary"]["planned_energy_kcal"] == 195.0
        assert data["budget_summary"]["planned_cost_idr"] == 18000
        assert data["budget_summary"]["remaining_after_plan_idr"] == 22000
        assert len(data["meal_entries"]) == 1
