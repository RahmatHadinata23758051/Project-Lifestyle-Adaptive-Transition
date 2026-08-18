import pytest
import jwt
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_missing_auth_token_rejected_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/profile")
        assert res.status_code == 401
        assert "detail" in res.json()


@pytest.mark.asyncio
async def test_invalid_jwt_token_rejected_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid signature
        fake_token = create_mock_jwt("user-1", "user1@chronos.local", secret="wrong-secret-key-that-fails-signature")
        res = await client.get(
            "/api/v1/profile",
            headers={"Authorization": f"Bearer {fake_token}"},
        )
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_valid_jwt_and_profile_get_and_patch():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-123", "alice@example.com")
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 1. GET Profile (Auto-created on first access)
        res_get = await client.get("/api/v1/profile", headers=auth_headers)
        assert res_get.status_code == 200
        data = res_get.json()
        assert data["user_id"] == "user-123"
        assert data["onboarding_status"] == "NOT_STARTED"

        # 2. PATCH Profile
        patch_payload = {
            "display_name": "Alice Chronos",
            "timezone": "Asia/Jakarta",
            "height_cm": 165.5,
            "current_weight_kg": 55.0,
            "occupation_type": "STUDENT",
            "onboarding_status": "IN_PROGRESS",
        }
        res_patch = await client.patch("/api/v1/profile", json=patch_payload, headers=auth_headers)
        assert res_patch.status_code == 200
        updated = res_patch.json()
        assert updated["display_name"] == "Alice Chronos"
        assert updated["height_cm"] == 165.5
        assert updated["onboarding_status"] == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_ownership_isolation_user_a_cannot_access_user_b():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_a = create_mock_jwt("user-A", "userA@example.com")
        token_b = create_mock_jwt("user-B", "userB@example.com")

        # User A creates a constraint
        constraint_payload = {
            "title": "User A Private Lecture",
            "category": "UNIVERSITY",
            "day_of_week": "MONDAY",
            "start_time": "09:00",
            "end_time": "11:00",
            "is_flexible": False,
        }
        res_create_a = await client.post(
            "/api/v1/user-state/constraints",
            json=constraint_payload,
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res_create_a.status_code == 201
        constraint_a_id = res_create_a.json()["id"]

        # User B lists constraints -> Must NOT see User A's constraint!
        res_list_b = await client.get(
            "/api/v1/user-state/constraints",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_list_b.status_code == 200
        assert len(res_list_b.json()) == 0

        # User B attempts to DELETE User A's constraint -> 404 (Access Denied / Not Found)
        res_delete = await client.delete(
            f"/api/v1/user-state/constraints/{constraint_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_delete.status_code == 404


@pytest.mark.asyncio
async def test_historical_sleep_baseline_preserved():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-baseline", "baseline@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create Initial Sleep Baseline
        b1_payload = {"bedtime": "02:30", "wake_time": "10:30"}
        res_b1 = await client.post("/api/v1/user-state/baselines/sleep", json=b1_payload, headers=headers)
        assert res_b1.status_code == 201
        assert res_b1.json()["is_current"] is True

        # 2. Create Updated Sleep Baseline (Week 2 revision)
        b2_payload = {"bedtime": "01:30", "wake_time": "09:30"}
        res_b2 = await client.post("/api/v1/user-state/baselines/sleep", json=b2_payload, headers=headers)
        assert res_b2.status_code == 201
        assert res_b2.json()["is_current"] is True

        # 3. GET Current Baseline -> Must return the latest one (01:30)
        res_current = await client.get("/api/v1/user-state/baselines/sleep", headers=headers)
        assert res_current.status_code == 200
        assert res_current.json()["bedtime"] == "01:30"
        assert res_current.json()["wake_time"] == "09:30"

        # 4. GET Baseline History -> Must contain BOTH baselines (Initial baseline preserved!)
        res_history = await client.get("/api/v1/user-state/baselines/sleep/history", headers=headers)
        assert res_history.status_code == 200
        history = res_history.json()
        assert len(history) == 2
        # One is current, one is non-current (historical)
        current_count = sum(1 for b in history if b["is_current"])
        historical_count = sum(1 for b in history if not b["is_current"])
        assert current_count == 1
        assert historical_count == 1


@pytest.mark.asyncio
async def test_financial_profile_and_goals_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_mock_jwt("user-financial", "finance@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Financial Profile GET & PUT
        res_get_fin = await client.get("/api/v1/user-state/financial-profile", headers=headers)
        assert res_get_fin.status_code == 200
        assert res_get_fin.json()["weekly_food_budget"] == 350000.0

        res_put_fin = await client.put(
            "/api/v1/user-state/financial-profile",
            json={"weekly_food_budget": 500000.0, "currency": "IDR"},
            headers=headers,
        )
        assert res_put_fin.status_code == 200
        assert res_put_fin.json()["weekly_food_budget"] == 500000.0

        # 2. Goal Creation & List
        goal_payload = {
            "domain": "SLEEP_ROUTINE",
            "priority": "PRIMARY",
            "status": "ACTIVE",
            "target_description": "Bangun jam 07:00 tanpa alarm",
        }
        res_goal = await client.post("/api/v1/user-state/goals", json=goal_payload, headers=headers)
        assert res_goal.status_code == 201
        assert res_goal.json()["domain"] == "SLEEP_ROUTINE"

        res_list_goals = await client.get("/api/v1/user-state/goals", headers=headers)
        assert res_list_goals.status_code == 200
        assert len(res_list_goals.json()) == 1
