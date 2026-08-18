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
