import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.schemas.profile import CurrentSelfBaseline, TargetSelfGoal, CookingCapability, ExerciseFacility, BodyObjective
from app.schemas.constraints import UserConstraint, ConstraintCategory, DayOfWeek
from app.services.roadmap_service import create_user_transition_roadmap, get_active_daily_plan
from app.services.checkin_service import process_item_checkin, evaluate_daily_plan_completion


# In-memory SQLite with StaticPool so all connections share the same in-memory tables
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_roadmap_generation_and_checkin_flow():
    db = TestingSessionLocal()

    baseline = CurrentSelfBaseline(
        bedtime="02:00",
        wake_time="10:00",
        current_weight=65.0,
        meals_per_day=2,
        weekly_food_budget=350000.0,
        cooking_access=CookingCapability.LIMITED,
        exercise_access=ExerciseFacility.NO_EQUIPMENT,
    )
    goal = TargetSelfGoal(
        target_wake_time="07:00",
        target_bedtime="23:00",
        body_objective=BodyObjective.ROUTINE_ONLY,
        duration_days=30,
    )
    constraint = UserConstraint(
        title="College Morning Lecture",
        category=ConstraintCategory.UNIVERSITY,
        day_of_week=DayOfWeek.MONDAY,
        start_time="08:00",
        end_time="12:00",
    )

    # 1. Generate Roadmap
    result = create_user_transition_roadmap(
        db=db,
        email="test_user@example.com",
        baseline_data=baseline,
        goal_data=goal,
        constraints_data=[constraint],
        start_date_str="2026-08-18",
    )
    assert result["roadmap_id"] is not None
    assert result["total_days"] == 30
    assert result["daily_budget"] == 50000.0

    roadmap_id = result["roadmap_id"]

    # 2. Get today's plan
    today_plan = get_active_daily_plan(db, roadmap_id=roadmap_id, day_number=1)
    assert today_plan is not None
    assert len(today_plan["items"]) == 4
    assert today_plan["total_spent_today"] == 0.0
    assert today_plan["remaining_budget_today"] == 50000.0

    # 3. Check-in on Lunch item with spending
    lunch_item = next(i for i in today_plan["items"] if "Makan Siang" in i["title"])
    checkin_res = process_item_checkin(
        db=db,
        item_id=lunch_item["id"],
        actual_time_str="12:45",
        actual_cost=25000.0,
    )
    assert checkin_res["status"] == "COMPLETED"
    assert checkin_res["actual_cost"] == 25000.0

    # 4. Check-in on Wake item (on-time at 10:05, target 10:00 -> within 20m success)
    wake_item = next(i for i in today_plan["items"] if "Bangun" in i["title"])
    process_item_checkin(
        db=db,
        item_id=wake_item["id"],
        actual_time_str="10:05",
    )

    # 5. Evaluate Day 1 completion
    eval_res = evaluate_daily_plan_completion(
        db=db,
        daily_plan_id=today_plan["daily_plan_id"],
        did_open_app=True,
    )
    assert eval_res["evaluation_result"] == "SUCCESS"
    assert eval_res["adaptation_action"] == "ADVANCE_STEP"
    assert eval_res["updated_step_index"] == 1
    assert eval_res["updated_roadmap_day"] == 2

    # Verify updated plan reflects spending
    updated_plan = get_active_daily_plan(db, roadmap_id=roadmap_id, day_number=1)
    assert updated_plan["total_spent_today"] == 25000.0
    assert updated_plan["remaining_budget_today"] == 25000.0


@pytest.mark.asyncio
async def test_api_roadmap_onboarding_and_checkin_integration():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Onboard user via REST API
        onboard_payload = {
            "email": "api_user@example.com",
            "baseline": {
                "bedtime": "01:00",
                "wake_time": "09:00",
                "weekly_food_budget": 420000.0,
            },
            "goal": {
                "target_wake_time": "07:00",
                "target_bedtime": "23:00",
                "duration_days": 20,
            },
            "constraints": [],
            "start_date": "2026-08-18",
        }
        res_onboard = await client.post("/api/v1/roadmaps/onboard", json=onboard_payload)
        assert res_onboard.status_code == 200
        onboard_data = res_onboard.json()
        roadmap_id = onboard_data["roadmap_id"]

        # 2. Get today's plan
        res_plan = await client.get(f"/api/v1/roadmaps/{roadmap_id}/today")
        assert res_plan.status_code == 200
        plan_data = res_plan.json()
        assert plan_data["day_number"] == 1
        assert len(plan_data["items"]) == 4

        first_item_id = plan_data["items"][0]["id"]

        # 3. 1-Tap Check-in item
        checkin_payload = {
            "item_id": first_item_id,
            "actual_time": "09:05",
            "actual_cost": 0.0,
            "is_late": False,
        }
        res_checkin = await client.post("/api/v1/roadmaps/checkin", json=checkin_payload)
        assert res_checkin.status_code == 200
        assert res_checkin.json()["status"] == "COMPLETED"

        # 4. Evaluate day
        eval_payload = {
            "daily_plan_id": plan_data["daily_plan_id"],
            "did_open_app": True,
        }
        res_eval = await client.post("/api/v1/roadmaps/evaluate", json=eval_payload)
        assert res_eval.status_code == 200
        assert res_eval.json()["evaluation_result"] == "SUCCESS"
