from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.budget_selection.constants import (
    BudgetPeriod,
    BudgetSource,
    CandidateBudgetStatus,
    BudgetSelectionStatus,
    BudgetSelectionPolicy,
)
from app.price_knowledge.constants import PriceConfidence
from app.food_candidates.constants import CandidateMatchStatus


class BudgetContextInput(BaseModel):
    currency_code: str = "IDR"
    budget_period: BudgetPeriod = BudgetPeriod.DAILY
    total_food_budget_idr: int = Field(..., ge=0)
    spent_food_budget_idr: Optional[int] = Field(None, ge=0)
    remaining_food_budget_idr: Optional[int] = None
    period_days_remaining: int = Field(1, ge=1)
    explicit_today_budget_idr: Optional[int] = Field(None, ge=0)
    budget_source: BudgetSource = BudgetSource.USER_DECLARED


class BudgetCandidateEvaluationResponse(BaseModel):
    candidate_id: str
    slot_id: str
    estimated_cost_idr: Optional[int] = None
    budget_status: CandidateBudgetStatus
    price_confidence: PriceConfidence
    uses_stale_prices: bool
    nutrition_fit_status: CandidateMatchStatus
    preference_score: int = 0
    absolute_energy_deviation: float = 0.0
    explanations: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class DailyCandidateCombinationResponse(BaseModel):
    combination_id: str
    selections: Dict[str, BudgetCandidateEvaluationResponse]
    total_estimated_cost_idr: int
    budget_envelope_idr: int
    remaining_after_selection_idr: int
    price_confidence: PriceConfidence
    uses_stale_prices: bool
    nutrition_deviation_score: float
    preference_score: int
    all_strict_nutrition: bool

    model_config = ConfigDict(from_attributes=True)


class BudgetAwareSelectionPreviewResponse(BaseModel):
    date: str
    logical_day_id: str
    status: BudgetSelectionStatus
    budget_envelope_idr: Optional[int] = None
    selected_combination: Optional[DailyCandidateCombinationResponse] = None
    alternatives: List[DailyCandidateCombinationResponse] = []
    shortfall_idr: Optional[int] = None
    search_truncated: bool = False
    explanations: List[str] = []
    policy_versions: Dict[str, str] = {}

    model_config = ConfigDict(from_attributes=True)
