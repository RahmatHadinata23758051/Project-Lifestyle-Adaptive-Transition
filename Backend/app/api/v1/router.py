from fastapi import APIRouter
from app.api.v1.endpoints import health, engine, roadmaps, profile, user_state, assessment, nutrition

api_router = APIRouter()

api_router.include_router(health.router, prefix="", tags=["Health"])
api_router.include_router(engine.router, prefix="/engine", tags=["Adaptive Engine"])
api_router.include_router(roadmaps.router, prefix="/roadmaps", tags=["Roadmaps & User State"])
api_router.include_router(profile.router, prefix="/profile", tags=["Identity & Profile"])
api_router.include_router(user_state.router, prefix="/user-state", tags=["User State & Domain Baselines"])
api_router.include_router(assessment.router, prefix="/assessment", tags=["Dynamic Assessment Intelligence"])
api_router.include_router(nutrition.router, prefix="/nutrition", tags=["Nutrition Intelligence"])
