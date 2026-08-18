import pytest
import jwt
import json
from httpx import AsyncClient, ASGITransport
from datetime import date

from app.main import app
from app.core.config import settings
from app.assessment.field_registry import calculate_age_from_birthdate
from app.models.assessment import AssessmentSnapshotRecord


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_derived_age_calculation():
    age = calculate_age_from_birthdate("2000-01-01")
    expected = date.today().year - 2000 - ((date.today().month, date.today().day) < (1, 1))
    assert age == expected

    assert calculate_age_from_birthdate(None) is None
    assert calculate_age_from_birthdate("invalid-date") is None


@pytest.mark.asyncio
async def test_goal_priority_constraint_multiple_primary_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-priority-test", "priority@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt to set 2 PRIMARY active goals -> Must fail validation (422 Unprocessable Entity)
        invalid_goals_payload = {
            "goals": [
                {"domain": "SLEEP_ROUTINE", "priority": "PRIMARY", "status": "ACTIVE"},
                {"domain": "NUTRITION_WEIGHT_GAIN", "priority": "PRIMARY", "status": "ACTIVE"},
            ]
        }
        res = await client.post("/api/v1/assessment/goals", json=invalid_goals_payload, headers=headers)
        assert res.status_code == 422
        assert "PRIMARY" in str(res.json())


@pytest.mark.asyncio
async def test_partial_profile_only_asks_missing_height():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-partial-profile", "partial@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        # Partial Profile: birth_date and sex provided, height_cm is missing
        await client.patch(
            "/api/v1/profile",
            json={
                "birth_date": "2002-05-15",
                "sex": "MALE",
                "timezone": "Asia/Jakarta",
            },
            headers=headers,
        )

        # Select Nutrition Goal
        await client.post(
            "/api/v1/assessment/goals",
            json={"goals": [{"domain": "NUTRITION_WEIGHT_GAIN", "priority": "PRIMARY", "status": "ACTIVE"}]},
            headers=headers,
        )

        res_q = await client.get("/api/v1/assessment/questions", headers=headers)
        assert res_q.status_code == 200
        data = res_q.json()
        question_keys = [q["key"] for q in data["questions"]]

        # Known fields NOT asked
        assert "profile.birth_date" not in question_keys
        assert "profile.sex" not in question_keys
        assert "profile.age" not in question_keys

        # Missing profile field MUST be asked
        assert "profile.height_cm" in question_keys

        # Domain specific required fields MUST be asked
        assert "nutrition.current_weight_kg" in question_keys
        assert "nutrition.cooking_capability" in question_keys


@pytest.mark.asyncio
async def test_goal_routing_sleep_only_no_unrelated_questions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-sleep-only", "sleep@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        await client.patch(
            "/api/v1/profile",
            json={"birth_date": "1999-10-10", "sex": "FEMALE", "height_cm": 160.0, "timezone": "Asia/Jakarta"},
            headers=headers,
        )

        await client.post(
            "/api/v1/assessment/goals",
            json={"goals": [{"domain": "SLEEP_ROUTINE", "priority": "PRIMARY", "status": "ACTIVE"}]},
            headers=headers,
        )

        res_q = await client.get("/api/v1/assessment/questions", headers=headers)
        data = res_q.json()
        question_keys = [q["key"] for q in data["questions"]]

        assert "sleep.current_bedtime" in question_keys
        assert "sleep.current_wake_time" in question_keys
        assert "sleep.target_wake_time" in question_keys

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

        # 1 PRIMARY, 1 SECONDARY
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
        assert not any(k.startswith("nutrition.") for k in question_keys)


@pytest.mark.asyncio
async def test_completeness_and_zero_guessing_plan_gate():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-gate", "gate@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        await client.post(
            "/api/v1/assessment/goals",
            json={"goals": [{"domain": "NUTRITION_WEIGHT_GAIN", "priority": "PRIMARY", "status": "ACTIVE"}]},
            headers=headers,
        )

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

        res_snap = await client.post("/api/v1/assessment/snapshot", headers=headers)
        assert res_snap.status_code == 409
        assert "incomplete" in res_snap.json()["detail"].lower()


@pytest.mark.asyncio
async def test_full_assessment_flow_and_immutable_snapshot_database_integrity(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-complete-snap", "snap@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        await client.post(
            "/api/v1/assessment/goals",
            json={"goals": [{"domain": "SLEEP_ROUTINE", "priority": "PRIMARY", "status": "ACTIVE"}]},
            headers=headers,
        )

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
        await client.post(
            "/api/v1/assessment/answers",
            json={"answers": complete_answers},
            headers=headers,
        )

        res_snap = await client.post("/api/v1/assessment/snapshot", headers=headers)
        assert res_snap.status_code == 201
        snap_id = res_snap.json()["snapshot_id"]

        # Mutate Live Profile, Sleep, and Budget after snapshot creation
        await client.patch("/api/v1/profile", json={"height_cm": 188.0}, headers=headers)
        await client.post(
            "/api/v1/user-state/baselines/sleep",
            json={"bedtime": "01:00", "wake_time": "08:00"},
            headers=headers,
        )

        # Query snapshot record directly from DB to verify raw immutability
        db_snap = db_session.query(AssessmentSnapshotRecord).filter(AssessmentSnapshotRecord.id == snap_id).first()
        assert db_snap is not None
        saved_dict = json.loads(db_snap.snapshot_data)

        # Snapshot data is 100% frozen: Height remains 175.0, bedtime remains 03:00
        assert saved_dict["core_profile"]["height_cm"] == 175.0
        assert saved_dict["sleep_domain"]["current_bedtime"] == "03:00"


@pytest.mark.asyncio
async def test_multi_user_isolation_user_a_and_user_b():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_a = create_mock_jwt("user-A-unique", "userA@chronos.local")
        token_b = create_mock_jwt("user-B-unique", "userB@chronos.local")

        # User A sets goals and completes answers
        await client.post(
            "/api/v1/assessment/goals",
            json={"goals": [{"domain": "SLEEP_ROUTINE", "priority": "PRIMARY", "status": "ACTIVE"}]},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        await client.post(
            "/api/v1/assessment/answers",
            json={"answers": {"profile.birth_date": "2000-01-01", "profile.sex": "FEMALE", "profile.height_cm": 165.0, "sleep.current_bedtime": "02:00", "sleep.current_wake_time": "10:00", "sleep.target_wake_time": "06:00", "sleep.requested_transition_duration": 14}},
            headers={"Authorization": f"Bearer {token_a}"},
        )

        # User B checks status -> Must NOT see User A's goals or answers (must be empty/not-started)
        res_b_status = await client.get("/api/v1/assessment/status", headers={"Authorization": f"Bearer {token_b}"})
        assert res_b_status.status_code == 200
        assert res_b_status.json()["overall_status"] == "NOT_STARTED"
        assert res_b_status.json()["is_plan_ready"] is False
