from fastapi import APIRouter
from app.api.v1.endpoints import health, engine, roadmaps

api_router = APIRouter()

api_router.include_router(health.router, prefix="", tags=["Health"])
api_router.include_router(engine.router, prefix="/engine", tags=["Adaptive Engine"])
api_router.include_router(roadmaps.router, prefix="/roadmaps", tags=["Roadmaps & User State"])
