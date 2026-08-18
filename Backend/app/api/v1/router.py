from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    engine,
    roadmaps,
    profile,
    user_state,
    assessment,
    nutrition,
    foods,
    meal_structure,
    food_candidates,
    prices,
    budget_selection,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="", tags=["Health"])
api_router.include_router(engine.router, prefix="/engine", tags=["Adaptive Engine"])
api_router.include_router(roadmaps.router, prefix="/roadmaps", tags=["Roadmaps & User State"])
api_router.include_router(profile.router, prefix="/profile", tags=["Identity & Profile"])
api_router.include_router(user_state.router, prefix="/user-state", tags=["User State & Domain Baselines"])
api_router.include_router(assessment.router, prefix="/assessment", tags=["Dynamic Assessment Intelligence"])
api_router.include_router(nutrition.router, prefix="/nutrition", tags=["Nutrition Intelligence"])
api_router.include_router(foods.router, prefix="/foods", tags=["Food Knowledge Foundation"])
api_router.include_router(meal_structure.router, prefix="/meal-structure", tags=["Meal Structure & Scheduling"])
api_router.include_router(food_candidates.router, prefix="/food-candidates", tags=["Food Candidate Generation"])
api_router.include_router(prices.router, prefix="/prices", tags=["Price Knowledge Foundation"])
api_router.include_router(budget_selection.router, prefix="/budget-selection", tags=["Budget-Aware Candidate Selection"])
