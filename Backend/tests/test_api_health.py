import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_root_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "Project Chronos" in data["service"]


@pytest.mark.asyncio
async def test_api_v1_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_api_v1_feasibility_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "baseline_wake_time": "13:00",
            "target_wake_time": "06:00",
            "duration_days": 60,
            "baseline_bedtime": "04:00",
            "target_bedtime": "22:00",
        }
        response = await client.post("/api/v1/engine/feasibility", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["is_feasible"] is True
        assert data["wake_delta_minutes"] == 420


@pytest.mark.asyncio
async def test_api_v1_evaluate_day_with_recent_history():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request with previous day MISSED + current day MISSED -> REDUCE_STEP_SIZE
        payload = {
            "target_time": "08:00",
            "actual_time": "09:10",
            "did_open_app": True,
            "recent_history": ["MISSED"],
        }
        response = await client.post("/api/v1/engine/evaluate-day", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["evaluation"]["result"] == "MISSED"
        assert data["recommended_action"] == "REDUCE_STEP_SIZE"


@pytest.mark.asyncio
async def test_api_v1_evaluate_day_no_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "target_time": "08:00",
            "actual_time": None,
            "did_open_app": False,
        }
        response = await client.post("/api/v1/engine/evaluate-day", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["evaluation"]["result"] == "NO_DATA"
        assert data["evaluation"]["deviation_minutes"] is None
        assert data["recommended_action"] == "MAINTAIN_STEP"


@pytest.mark.asyncio
async def test_api_v1_strict_time_validation_rejection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid time: 24:00 and 99:99
        payload = {
            "baseline_wake_time": "24:00",
            "target_wake_time": "99:99",
            "duration_days": 60,
            "baseline_bedtime": "04:00",
            "target_bedtime": "22:00",
        }
        response = await client.post("/api/v1/engine/feasibility", json=payload)
        assert response.status_code == 422  # Pydantic validation error
