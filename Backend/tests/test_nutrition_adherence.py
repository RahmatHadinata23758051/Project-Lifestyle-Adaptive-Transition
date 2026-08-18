import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from app.main import app
from app.db.session import get_db, SessionLocal
from app.models.user import User
from app.nutrition_adherence.constants import (
    MealCheckinStatus,
    MealCompletionState,
    TimingAdherenceStatus,
    FoodChoiceAdherence,
    EnergyAdherenceStatus,
    ReportingCompleteness,
    ActualIntakeCertainty,
    ActualFoodSourceType,
    DeviationReason,
)
from app.nutrition_adherence.models import (
    MealCheckinDTO,
    ActualFoodItemDTO,
    UnplannedIntakeDTO,
)
from app.daily_nutrition_plan.models import (
    DailyNutritionPlanDTO,
    DailyMealEntryDTO,
    DailyMealFoodItemDTO,
    DailyNutritionSummaryDTO,
    DailyBudgetSummaryDTO,
    DailyPlanProvenanceDTO,
)
from app.daily_nutrition_plan.constants import DailyPlanStatus, MacroCompleteness
from app.price_knowledge.constants import CostCompleteness
from app.meal_structure.constants import MealSlotType
from app.nutrition_adherence.validation import (
    validate_meal_checkin_input,
    validate_unplanned_intake_input,
)
from app.nutrition_adherence.timing import evaluate_timing_adherence
from app.nutrition_adherence.actual_intake import materialize_as_planned_items
from app.nutrition_adherence.adherence import evaluate_daily_nutrition_adherence
from app.repositories.nutrition_adherence_repository import NutritionAdherenceRepository
from app.services.nutrition_adherence_service import NutritionAdherenceService
from app.core.config import settings
import jwt


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _create_mock_plan() -> DailyNutritionPlanDTO:
    entry_m1 = DailyMealEntryDTO(
        slot_id="slot_m1",
        slot_type=MealSlotType.MAIN_MEAL,
        scheduled_time="08:00",
        earliest_time="07:30",
        latest_time="08:30",
        candidate_id="cand_m1",
        foods=[
            DailyMealFoodItemDTO(
                food_item_id="f_rice",
                canonical_name="Nasi Putih",
                role="STAPLE",
                serving_name="150g",
                grams=150.0,
                energy_kcal=195.0,
                protein_g=4.0,
                fat_g=0.5,
                carbohydrate_g=42.0,
            ),
            DailyMealFoodItemDTO(
                food_item_id="f_egg",
                canonical_name="Telur Ayam Rebus",
                role="PROTEIN_SOURCE",
                serving_name="2 butir",
                grams=110.0,
                energy_kcal=154.0,
                protein_g=12.6,
                fat_g=10.6,
                carbohydrate_g=1.1,
            ),
        ],
        planned_energy_kcal=349.0,
        planned_protein_g=16.6,
        planned_fat_g=11.1,
        planned_carbohydrate_g=43.1,
        nutrition_fit_status="STRICT_MATCH",
        estimated_cost_idr=12000,
        cost_completeness=CostCompleteness.COMPLETE,
        price_confidence="HIGH",
        uses_stale_prices=False,
    )

    entry_m2 = DailyMealEntryDTO(
        slot_id="slot_m2",
        slot_type=MealSlotType.MAIN_MEAL,
        scheduled_time="13:00",
        earliest_time="12:30",
        latest_time="13:30",
        candidate_id="cand_m2",
        foods=[
            DailyMealFoodItemDTO(
                food_item_id="f_chicken",
                canonical_name="Ayam Dada",
                role="PROTEIN_SOURCE",
                serving_name="100g",
                grams=100.0,
                energy_kcal=165.0,
                protein_g=31.0,
                fat_g=3.6,
                carbohydrate_g=0.0,
            )
        ],
        planned_energy_kcal=165.0,
        planned_protein_g=31.0,
        planned_fat_g=3.6,
        planned_carbohydrate_g=0.0,
        nutrition_fit_status="STRICT_MATCH",
        estimated_cost_idr=18000,
        cost_completeness=CostCompleteness.COMPLETE,
        price_confidence="HIGH",
        uses_stale_prices=False,
    )

    return DailyNutritionPlanDTO(
        plan_id="plan_test_ld1",
        date="2026-08-19",
        logical_day_id="ld_test_1",
        status=DailyPlanStatus.READY,
        nutrition_summary=DailyNutritionSummaryDTO(
            target_energy_kcal=514.0,
            planned_energy_kcal=514.0,
            energy_difference_kcal=0.0,
            planned_protein_g=47.6,
            planned_fat_g=14.7,
            planned_carbohydrate_g=43.1,
            macro_completeness=MacroCompleteness.COMPLETE,
            strict_match_slot_count=2,
            near_match_slot_count=0,
        ),
        budget_summary=DailyBudgetSummaryDTO(
            budget_envelope_idr=40000,
            planned_cost_idr=30000,
            remaining_after_plan_idr=10000,
            cost_completeness=CostCompleteness.COMPLETE,
            price_confidence="HIGH",
            uses_stale_prices=False,
            budget_source="USER_DECLARED",
        ),
        meal_entries=[entry_m1, entry_m2],
        warnings=[],
        provenance=DailyPlanProvenanceDTO(
            nutrition_policy_version="NUTRITION_V0_1",
            meal_structure_policy_version="MEAL_STRUCTURE_TRANSITION_V01",
            food_candidate_policy_version="FOOD_CANDIDATE_P1_2",
            price_policy_version="PRICE_KNOWLEDGE_P1_3",
            budget_selection_policy_version="BUDGET_SELECTION_P1_4",
            assembly_policy_version="DAILY_NUTRITION_PLAN_ASSEMBLY_P1_5",
        ),
        policy_versions={},
    )


def test_not_reported_vs_skipped_semantic_distinction():
    """
    NOT_REPORTED = missing observation (unknown energy/nutrients).
    SKIPPED = known behavior (0 kcal for that slot).
    """
    plan = _create_mock_plan()

    # Slot 1 is SKIPPED, Slot 2 is NOT_REPORTED (no checkin passed)
    checkin_s1 = MealCheckinDTO(
        plan_id=plan.plan_id,
        logical_day_id=plan.logical_day_id,
        slot_id="slot_m1",
        status=MealCheckinStatus.SKIPPED,
        checked_in_at="2026-08-19T08:30:00Z",
        actual_items=[],
        deviation_reason=DeviationReason.NOT_HUNGRY,
    )

    adherence = evaluate_daily_nutrition_adherence(plan, [checkin_s1], [])

    assert adherence.reporting_completeness == ReportingCompleteness.PARTIAL
    assert len(adherence.slot_adherences) == 2

    # Slot 1 (SKIPPED)
    slot1_adh = next(s for s in adherence.slot_adherences if s.slot_id == "slot_m1")
    assert slot1_adh.meal_completion == MealCompletionState.SKIPPED
    assert slot1_adh.food_choice_adherence == FoodChoiceAdherence.SKIPPED
    assert slot1_adh.actual_energy_kcal == 0.0
    assert slot1_adh.energy_adherence == EnergyAdherenceStatus.BELOW_PLANNED_RANGE

    # Slot 2 (NOT_REPORTED)
    slot2_adh = next(s for s in adherence.slot_adherences if s.slot_id == "slot_m2")
    assert slot2_adh.meal_completion == MealCompletionState.NOT_REPORTED
    assert slot2_adh.food_choice_adherence == FoodChoiceAdherence.NOT_REPORTED
    assert slot2_adh.actual_energy_kcal is None
    assert slot2_adh.energy_adherence == EnergyAdherenceStatus.UNKNOWN


def test_ate_as_planned_intake_materialization():
    """
    ATE_AS_PLANNED materializes full planned items from snapshot.
    """
    plan = _create_mock_plan()
    entry_m1 = plan.meal_entries[0]

    materialized = materialize_as_planned_items(entry_m1)
    assert len(materialized) == 2
    assert materialized[0].display_name == "Nasi Putih"
    assert materialized[0].energy_kcal == 195.0
    assert materialized[1].display_name == "Telur Ayam Rebus"
    assert materialized[1].energy_kcal == 154.0

    checkin_s1 = MealCheckinDTO(
        plan_id=plan.plan_id,
        logical_day_id=plan.logical_day_id,
        slot_id="slot_m1",
        status=MealCheckinStatus.ATE_AS_PLANNED,
        meal_occurred_at="08:00",
        checked_in_at="2026-08-19T08:15:00Z",
        actual_items=materialized,
        actual_spend_idr=12000,
    )

    adherence = evaluate_daily_nutrition_adherence(plan, [checkin_s1], [])
    slot1_adh = next(s for s in adherence.slot_adherences if s.slot_id == "slot_m1")
    assert slot1_adh.meal_completion == MealCompletionState.FULL
    assert slot1_adh.food_choice_adherence == FoodChoiceAdherence.AS_PLANNED
    assert slot1_adh.timing_adherence == TimingAdherenceStatus.WITHIN_WINDOW
    assert slot1_adh.actual_energy_kcal == 349.0
    assert slot1_adh.energy_adherence == EnergyAdherenceStatus.WITHIN_PLANNED_RANGE


def test_ate_partially_portion_calculation():
    """
    ATE_PARTIALLY calculates actual reported portions, not assuming 50%.
    """
    plan = _create_mock_plan()

    # User ate only 1 egg (77 kcal) and 100g rice (130 kcal)
    partial_items = [
        ActualFoodItemDTO(
            food_item_id="f_rice",
            display_name="Nasi Putih",
            grams=100.0,
            quantity=0.67,
            energy_kcal=130.0,
            protein_g=2.7,
            fat_g=0.3,
            carbohydrate_g=28.0,
            source_type=ActualFoodSourceType.PLANNED_ITEM,
            certainty=ActualIntakeCertainty.EXACT,
        ),
        ActualFoodItemDTO(
            food_item_id="f_egg",
            display_name="Telur Ayam Rebus (1 butir)",
            grams=55.0,
            quantity=1.0,
            energy_kcal=77.0,
            protein_g=6.3,
            fat_g=5.3,
            carbohydrate_g=0.5,
            source_type=ActualFoodSourceType.PLANNED_ITEM,
            certainty=ActualIntakeCertainty.EXACT,
        ),
    ]

    checkin = MealCheckinDTO(
        plan_id=plan.plan_id,
        logical_day_id=plan.logical_day_id,
        slot_id="slot_m1",
        status=MealCheckinStatus.ATE_PARTIALLY,
        meal_occurred_at="08:10",
        checked_in_at="2026-08-19T08:30:00Z",
        actual_items=partial_items,
        deviation_reason=DeviationReason.NOT_HUNGRY,
    )

    adherence = evaluate_daily_nutrition_adherence(plan, [checkin], [])
    slot1_adh = next(s for s in adherence.slot_adherences if s.slot_id == "slot_m1")
    assert slot1_adh.meal_completion == MealCompletionState.PARTIAL
    assert slot1_adh.food_choice_adherence == FoodChoiceAdherence.PARTIAL_MATCH
    assert slot1_adh.actual_energy_kcal == 207.0
    assert slot1_adh.energy_adherence == EnergyAdherenceStatus.BELOW_PLANNED_RANGE


def test_different_food_with_resolved_and_unresolved_nutrition():
    """
    Unresolved food sets nutrition completeness to PARTIAL and never becomes 0 kcal.
    """
    plan = _create_mock_plan()

    diff_items = [
        ActualFoodItemDTO(
            food_item_id=None,
            display_name="Gorengan Misterius",
            quantity=2.0,
            energy_kcal=None,  # Unresolved
            source_type=ActualFoodSourceType.USER_REPORTED_UNRESOLVED,
            certainty=ActualIntakeCertainty.UNKNOWN,
        )
    ]

    checkin = MealCheckinDTO(
        plan_id=plan.plan_id,
        logical_day_id=plan.logical_day_id,
        slot_id="slot_m1",
        status=MealCheckinStatus.ATE_DIFFERENT_FOOD,
        meal_occurred_at="08:20",
        checked_in_at="2026-08-19T08:40:00Z",
        actual_items=diff_items,
        deviation_reason=DeviationReason.FOOD_UNAVAILABLE,
    )

    adherence = evaluate_daily_nutrition_adherence(plan, [checkin], [])
    assert adherence.actual_nutrition_summary.completeness == MacroCompleteness.PARTIAL
    assert adherence.actual_nutrition_summary.unresolved_item_count == 1
    assert adherence.actual_nutrition_summary.protein_g is None


def test_unplanned_intake_inclusion_in_daily_summary():
    """
    Unplanned intake (e.g. snack at 22:30) is included in actual daily totals without penalty.
    """
    plan = _create_mock_plan()

    unplanned = UnplannedIntakeDTO(
        logical_day_id=plan.logical_day_id,
        occurred_at="22:30",
        recorded_at="2026-08-19T22:35:00Z",
        items=[
            ActualFoodItemDTO(
                food_item_id="f_banana",
                display_name="Pisang Cavendish",
                grams=120.0,
                quantity=1.0,
                energy_kcal=105.0,
                protein_g=1.3,
                fat_g=0.4,
                carbohydrate_g=27.0,
                source_type=ActualFoodSourceType.FOOD_KNOWLEDGE_MATCH,
            )
        ],
        actual_spend_idr=5000,
        reason="Late night study snack",
    )

    adherence = evaluate_daily_nutrition_adherence(plan, [], [unplanned])
    assert len(adherence.unplanned_intakes) == 1
    assert adherence.actual_nutrition_summary.energy_kcal == 105.0
    assert adherence.actual_spend_summary.known_spend_idr == 5000


def test_actual_spend_reporting_complete_partial_and_unavailable():
    """
    Missing actual spend is None, never 0.
    """
    plan = _create_mock_plan()

    chk1 = MealCheckinDTO(
        plan_id=plan.plan_id,
        logical_day_id=plan.logical_day_id,
        slot_id="slot_m1",
        status=MealCheckinStatus.ATE_AS_PLANNED,
        checked_in_at="2026-08-19T08:00:00Z",
        actual_items=[],
        actual_spend_idr=15000,
    )
    chk2 = MealCheckinDTO(
        plan_id=plan.plan_id,
        logical_day_id=plan.logical_day_id,
        slot_id="slot_m2",
        status=MealCheckinStatus.ATE_AS_PLANNED,
        checked_in_at="2026-08-19T13:00:00Z",
        actual_items=[],
        actual_spend_idr=None,  # Missing spend
    )

    adherence = evaluate_daily_nutrition_adherence(plan, [chk1, chk2], [])
    assert adherence.actual_spend_summary.known_spend_idr == 15000
    assert adherence.actual_spend_summary.completeness == CostCompleteness.PARTIAL
    assert adherence.actual_spend_summary.missing_spend_count == 1


def test_timing_adherence_within_and_outside_window():
    """
    Evaluates timing adherence within slot window (07:30 to 08:30).
    """
    assert evaluate_timing_adherence("08:00", "07:30", "08:30") == TimingAdherenceStatus.WITHIN_WINDOW
    assert evaluate_timing_adherence("07:30", "07:30", "08:30") == TimingAdherenceStatus.WITHIN_WINDOW
    assert evaluate_timing_adherence("08:30", "07:30", "08:30") == TimingAdherenceStatus.WITHIN_WINDOW
    assert evaluate_timing_adherence("09:15", "07:30", "08:30") == TimingAdherenceStatus.OUTSIDE_WINDOW
    assert evaluate_timing_adherence("06:45", "07:30", "08:30") == TimingAdherenceStatus.OUTSIDE_WINDOW
    assert evaluate_timing_adherence(None, "07:30", "08:30") == TimingAdherenceStatus.UNKNOWN

    # Cross midnight window (23:30 to 01:30)
    assert evaluate_timing_adherence("00:15", "23:30", "01:30") == TimingAdherenceStatus.WITHIN_WINDOW
    assert evaluate_timing_adherence("02:00", "23:30", "01:30") == TimingAdherenceStatus.OUTSIDE_WINDOW


def test_contradictory_input_validation():
    """
    SKIPPED with actual items or negative spend raises validation error.
    """
    chk_invalid_skip = MealCheckinDTO(
        plan_id="p1",
        logical_day_id="ld1",
        slot_id="s1",
        status=MealCheckinStatus.SKIPPED,
        checked_in_at="2026-08-19T08:00:00Z",
        actual_items=[ActualFoodItemDTO(display_name="Food", energy_kcal=100.0)],
    )
    is_valid, err = validate_meal_checkin_input(chk_invalid_skip)
    assert not is_valid
    assert "SKIPPED" in err

    chk_negative_spend = MealCheckinDTO(
        plan_id="p1",
        logical_day_id="ld1",
        slot_id="s1",
        status=MealCheckinStatus.ATE_AS_PLANNED,
        checked_in_at="2026-08-19T08:00:00Z",
        actual_spend_idr=-5000,
    )
    is_valid, err = validate_meal_checkin_input(chk_negative_spend)
    assert not is_valid
    assert "negative" in err


def test_checkin_persistence_revision_and_idempotency():
    """
    Updating slot checkin marks previous active checkin as inactive and increments revision.
    """
    import uuid
    db = SessionLocal()
    user_id = f"user_adh_test_{uuid.uuid4()}"
    try:
        # Create user if needed
        existing = db.query(User).filter(User.id == user_id).first()
        if not existing:
            db.add(User(id=user_id, email=f"{user_id}@chronos.local"))
            db.commit()

        # Submit revision 1
        chk1 = MealCheckinDTO(
            plan_id="plan_rev_test",
            logical_day_id="ld_rev_1",
            slot_id="slot_m1",
            status=MealCheckinStatus.ATE_AS_PLANNED,
            meal_occurred_at="08:00",
            checked_in_at="2026-08-19T08:05:00Z",
            actual_items=[ActualFoodItemDTO(display_name="Nasi Putih", energy_kcal=195.0)],
            actual_spend_idr=10000,
        )
        saved1 = NutritionAdherenceRepository.save_meal_checkin(db, user_id, chk1)
        assert saved1.revision == 1

        # Submit revision 2 (user amends log)
        chk2 = MealCheckinDTO(
            plan_id="plan_rev_test",
            logical_day_id="ld_rev_1",
            slot_id="slot_m1",
            status=MealCheckinStatus.ATE_PARTIALLY,
            meal_occurred_at="08:00",
            checked_in_at="2026-08-19T08:15:00Z",
            actual_items=[ActualFoodItemDTO(display_name="Nasi Putih (setengah)", energy_kcal=100.0)],
            actual_spend_idr=10000,
        )
        saved2 = NutritionAdherenceRepository.save_meal_checkin(db, user_id, chk2)
        assert saved2.revision == 2

        active_checkins = NutritionAdherenceRepository.get_active_meal_checkins_for_day(db, user_id, "ld_rev_1")
        assert len(active_checkins) == 1
        assert active_checkins[0].status == MealCheckinStatus.ATE_PARTIALLY
        assert active_checkins[0].revision == 2
    finally:
        db.close()


@pytest.mark.asyncio
async def test_api_nutrition_checkin_and_preview_authenticated():
    """
    End-to-end API test for recording meal check-in and previewing daily adherence.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-api-adh-test", "adh_api@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Post meal checkin
        chk_payload = {
            "plan_id": "plan_api_1",
            "logical_day_id": "ld_api_1",
            "slot_id": "slot_m1",
            "status": "ATE_AS_PLANNED",
            "meal_occurred_at": "08:00",
            "checked_in_at": "2026-08-19T08:15:00Z",
            "actual_items": [
                {
                    "food_item_id": "f_rice",
                    "display_name": "Nasi Putih",
                    "grams": 150.0,
                    "quantity": 1.0,
                    "energy_kcal": 195.0,
                    "protein_g": 4.0,
                    "fat_g": 0.5,
                    "carbohydrate_g": 42.0,
                    "source_type": "PLANNED_ITEM",
                    "certainty": "EXACT",
                }
            ],
            "actual_spend_idr": 12000,
            "deviation_reason": None,
        }

        res = await client.post("/api/v1/nutrition-checkins/meals", json=chk_payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["slot_id"] == "slot_m1"
        assert data["status"] == "ATE_AS_PLANNED"

        # 2. Post unplanned intake
        unp_payload = {
            "logical_day_id": "ld_api_1",
            "occurred_at": "22:00",
            "recorded_at": "2026-08-19T22:05:00Z",
            "items": [
                {
                    "food_item_id": "f_apple",
                    "display_name": "Apel Fuji",
                    "grams": 100.0,
                    "quantity": 1.0,
                    "energy_kcal": 52.0,
                    "protein_g": 0.3,
                    "fat_g": 0.2,
                    "carbohydrate_g": 14.0,
                    "source_type": "FOOD_KNOWLEDGE_MATCH",
                    "certainty": "EXACT",
                }
            ],
            "actual_spend_idr": 6000,
            "reason": "Midnight snack",
        }
        res_unp = await client.post("/api/v1/nutrition-checkins/unplanned", json=unp_payload, headers=headers)
        assert res_unp.status_code == 201

        # 3. Preview adherence
        plan = _create_mock_plan()
        preview_payload = {
            "plan": {
                "plan_id": plan.plan_id,
                "date": plan.date,
                "logical_day_id": plan.logical_day_id,
                "status": "READY",
                "nutrition_summary": {
                    "target_energy_kcal": 514.0,
                    "planned_energy_kcal": 514.0,
                    "energy_difference_kcal": 0.0,
                    "planned_protein_g": 47.6,
                    "planned_fat_g": 14.7,
                    "planned_carbohydrate_g": 43.1,
                    "macro_completeness": "COMPLETE",
                    "strict_match_slot_count": 2,
                    "near_match_slot_count": 0,
                },
                "budget_summary": {
                    "budget_envelope_idr": 40000,
                    "planned_cost_idr": 30000,
                    "remaining_after_plan_idr": 10000,
                    "cost_completeness": "COMPLETE",
                    "price_confidence": "HIGH",
                    "uses_stale_prices": False,
                    "budget_source": "USER_DECLARED",
                },
                "meal_entries": [
                    {
                        "slot_id": "slot_m1",
                        "slot_type": "MAIN_MEAL",
                        "scheduled_time": "08:00",
                        "earliest_time": "07:30",
                        "latest_time": "08:30",
                        "candidate_id": "cand_m1",
                        "foods": [
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
                        "planned_energy_kcal": 195.0,
                        "planned_protein_g": 4.0,
                        "planned_fat_g": 0.5,
                        "planned_carbohydrate_g": 42.0,
                        "nutrition_fit_status": "STRICT_MATCH",
                        "estimated_cost_idr": 12000,
                        "cost_completeness": "COMPLETE",
                        "price_confidence": "HIGH",
                        "uses_stale_prices": False,
                    }
                ],
                "warnings": [],
                "provenance": {
                    "nutrition_policy_version": "NUTRITION_V0_1",
                    "meal_structure_policy_version": "MEAL_STRUCTURE_TRANSITION_V01",
                    "food_candidate_policy_version": "FOOD_CANDIDATE_P1_2",
                    "price_policy_version": "PRICE_KNOWLEDGE_P1_3",
                    "budget_selection_policy_version": "BUDGET_SELECTION_P1_4",
                    "assembly_policy_version": "DAILY_NUTRITION_PLAN_ASSEMBLY_P1_5",
                },
                "policy_versions": {},
            },
            "checkins": [chk_payload],
            "unplanned_intakes": [unp_payload],
        }

        res_prev = await client.post("/api/v1/nutrition-checkins/adherence/preview", json=preview_payload, headers=headers)
        if res_prev.status_code != 200:
            print("422 DETAIL:", res_prev.json())
        assert res_prev.status_code == 200
        prev_data = res_prev.json()
        assert prev_data["reporting_completeness"] == "COMPLETE"
        assert prev_data["actual_nutrition_summary"]["energy_kcal"] == 247.0
        assert prev_data["actual_spend_summary"]["known_spend_idr"] == 18000
