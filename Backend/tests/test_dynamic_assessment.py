import pytest
import jwt
from httpx import AsyncClient, ASGITransport
from datetime import date

from app.main import app
from app.core.config import settings
from app.assessment.field_registry import calculate_age_from_birthdate


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_derived_age_calculation():
    # Test born 2000-01-01
    age = calculate_age_from_birthdate("2000-01-01")
    expected = date.today().year - 2000 - ((date.today().month, date.today().day) < (1, 1))
    assert age == expected

    # Invalid string handling
    assert calculate_age_from_birthdate(None) is None
    assert calculate_age_from_birthdate("invalid-date") is None


@pytest.mark.asyncio
async def test_profile_reuse_birthdate_height_not_asked_again():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-reuse-profile", "reuse@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Update Core Profile initially
        await client.patch(
            "/api/v1/profile",
            json={
                "birth_date": "2002-05-15",
                "sex": "MALE",
                "height_cm": 178.0,
                "timezone": "Asia/Jakarta",
            },
            headers=headers,
        )

        # 2. Select Goal: NUTRITION_WEIGHT_GAIN
        goals_payload = {
            "goals": [
                {"domain": "NUTRITION_WEIGHT_GAIN", "priority": "PRIMARY", "status": "ACTIVE"}
            ]
        }
        res_goals = await client.post("/api/v1/assessment/goals", json=goals_payload, headers=headers)
        assert res_goals.status_code == 200

        # 3. GET Questions -> Profile fields already known MUST NOT be asked
        res_q = await client.get("/api/v1/assessment/questions", headers=headers)
        assert res_q.status_code == 200
        data = res_q.json()
        question_keys = [q["key"] for q in data["questions"]]

        assert "profile.birth_date" not in question_keys
        assert "profile.sex" not in question_keys
        assert "profile.height_cm" not in question_keys
        assert "profile.age" not in question_keys  # Derived field never asked

        # Missing required nutrition fields must be present
        assert "nutrition.current_weight_kg" in question_keys
        assert "nutrition.cooking_capability" in question_keys
        assert "nutrition.weekly_food_budget" in question_keys


@pytest.mark.asyncio
async def test_goal_routing_sleep_only_no_unrelated_questions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-sleep-only", "sleep@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        # Pre-fill profile
        await client.patch(
            "/api/v1/profile",
            json={"birth_date": "1999-10-10", "sex": "FEMALE", "height_cm": 160.0, "timezone": "Asia/Jakarta"},
            headers=headers,
        )

        # Set SLEEP_ROUTINE goal only
        await client.post(
            "/api/v1/assessment/goals",
            json={"goals": [{"domain": "SLEEP_ROUTINE", "priority": "PRIMARY", "status": "ACTIVE"}]},
            headers=headers,
        )

        res_q = await client.get("/api/v1/assessment/questions", headers=headers)
        data = res_q.json()
        question_keys = [q["key"] for q in data["questions"]]

        # Sleep questions present
        assert "sleep.current_bedtime" in question_keys
        assert "sleep.current_wake_time" in question_keys
        assert "sleep.target_wake_time" in question_keys

        # Nutrition and Activity questions must NOT be present!
        assert not any(k.startswith("nutrition.") for k in question_keys)
        assert not any(k.startswith("activity.") for k in question_keys)


@pytest.mark.asyncio
async def test_multi_goal_routing_merged_relevant_questions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-multi-goal", "multi@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        await client.patch(
            "/api/v1/profile",
            json={"birth_date": "1998-03-20", "sex": "MALE", "height_cm": 172.0, "timezone": "Asia/Jakarta"},
            headers=headers,
        )

        # Set SLEEP_ROUTINE and PHYSICAL_ACTIVITY (no nutrition)
        await client.post(
            "/api/v1/assessment/goals",
            json={
                "goals": [
                    {"domain": "SLEEP_ROUTINE", "priority": "PRIMARY", "status": "ACTIVE"},
                    {"domain": "PHYSICAL_ACTIVITY", "priority": "SECONDARY", "status": "ACTIVE"},
                ]
            },
            headers=headers,
        )

        res_q = await client.get("/api/v1/assessment/questions", headers=headers)
        data = res_q.json()
        question_keys = [q["key"] for q in data["questions"]]

        assert "sleep.current_bedtime" in question_keys
        assert "activity.experience_level" in question_keys
        assert "activity.equipment" in question_keys
        # No nutrition questions
        assert not any(k.startswith("nutrition.") for k in question_keys)


@pytest.mark.asyncio
async def test_completeness_and_zero_guessing_plan_gate():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-gate", "gate@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        # Set nutrition goal
        await client.post(
            "/api/v1/assessment/goals",
            json={"goals": [{"domain": "NUTRITION_WEIGHT_GAIN", "priority": "PRIMARY", "status": "ACTIVE"}]},
            headers=headers,
        )

        # Submit incomplete answers (missing current_weight_kg, weekly_food_budget, etc.)
        res_ans = await client.post(
            "/api/v1/assessment/answers",
            json={"answers": {"nutrition.cooking_capability": "LIMITED"}},
            headers=headers,
        )
        assert res_ans.status_code == 200
        status_data = res_ans.json()
        assert status_data["is_plan_ready"] is False
        assert status_data["overall_status"] == "IN_PROGRESS"
        assert len(status_data["missing_required_fields"]) > 0

        # Attempt to create snapshot -> Plan gate must reject with 409 Conflict
        res_snap = await client.post("/api/v1/assessment/snapshot", headers=headers)
        assert res_snap.status_code == 409
        assert "incomplete" in res_snap.json()["detail"].lower()


@pytest.mark.asyncio
async def test_full_assessment_flow_and_immutable_snapshot_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-complete-snap", "snap@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Set Goals: SLEEP_ROUTINE
        await client.post(
            "/api/v1/assessment/goals",
            json={"goals": [{"domain": "SLEEP_ROUTINE", "priority": "PRIMARY", "status": "ACTIVE"}]},
            headers=headers,
        )

        # 2. Answer all required profile + sleep fields
        complete_answers = {
            "profile.birth_date": "2001-08-20",
            "profile.sex": "MALE",
            "profile.height_cm": 175.0,
            "profile.timezone": "Asia/Jakarta",
            "sleep.current_bedtime": "03:00",
            "sleep.current_wake_time": "11:00",
            "sleep.target_wake_time": "07:00",
            "sleep.requested_transition_duration": 21,
        }
        res_ans = await client.post(
            "/api/v1/assessment/answers",
            json={"answers": complete_answers},
            headers=headers,
        )
        assert res_ans.status_code == 200
        assert res_ans.json()["is_plan_ready"] is True
        assert res_ans.json()["overall_status"] == "COMPLETE"

        # 3. Create Immutable Assessment Snapshot
        res_snap = await client.post("/api/v1/assessment/snapshot", headers=headers)
        assert res_snap.status_code == 201
        snap_data = res_snap.json()
        assert snap_data["snapshot_id"] is not None
        assert snap_data["snapshot_data"]["core_profile"]["birth_date"] == "2001-08-20"
        assert snap_data["snapshot_data"]["core_profile"]["age"] == calculate_age_from_birthdate("2001-08-20")
        assert snap_data["snapshot_data"]["sleep_domain"]["current_bedtime"] == "03:00"

        # 4. Mutate Live Profile later (e.g. height change or name change)
        await client.patch("/api/v1/profile", json={"height_cm": 185.0}, headers=headers)

        # 5. Verify snapshot remains immutable (height in snapshot data still 175.0)
        assert snap_data["snapshot_data"]["core_profile"]["height_cm"] == 175.0
