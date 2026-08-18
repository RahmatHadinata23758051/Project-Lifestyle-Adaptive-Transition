from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from app.budget_selection.constants import (
    BudgetPeriod,
    BudgetSource,
    CandidateBudgetStatus,
    BudgetSelectionStatus,
    BudgetSelectionPolicy,
)
from app.price_knowledge.constants import PriceConfidence, CostCompleteness
from app.price_knowledge.models import CandidateCostEstimateDTO
from app.food_candidates.constants import CandidateMatchStatus
from app.food_candidates.models import FoodCandidateSetDTO


@dataclass
class BudgetContextDTO:
    currency_code: str = BudgetSelectionPolicy.DEFAULT_CURRENCY
    budget_period: BudgetPeriod = BudgetPeriod.DAILY
    total_food_budget_idr: int = 0
    spent_food_budget_idr: Optional[int] = None
    remaining_food_budget_idr: Optional[int] = None
    period_days_remaining: int = 1
    explicit_today_budget_idr: Optional[int] = None
    budget_source: BudgetSource = BudgetSource.USER_DECLARED


@dataclass
class BudgetCandidateEvaluationDTO:
    candidate_id: str
    slot_id: str
    estimated_cost_idr: Optional[int]
    budget_status: CandidateBudgetStatus
    price_confidence: PriceConfidence
    uses_stale_prices: bool
    nutrition_fit_status: CandidateMatchStatus
    preference_score: int = 0
    absolute_energy_deviation: float = 0.0
    explanations: List[str] = field(default_factory=list)


@dataclass
class DailyCandidateCombinationDTO:
    combination_id: str
    selections: Dict[str, BudgetCandidateEvaluationDTO]
    total_estimated_cost_idr: int
    budget_envelope_idr: int
    remaining_after_selection_idr: int
    price_confidence: PriceConfidence
    uses_stale_prices: bool
    nutrition_deviation_score: float
    preference_score: int
    all_strict_nutrition: bool


@dataclass
class BudgetAwareSelectionInputDTO:
    date: str
    logical_day_id: str
    slot_ids: List[str]
    candidates_by_slot: Dict[str, List[FoodCandidateSetDTO]]
    candidate_costs_by_candidate_id: Dict[str, CandidateCostEstimateDTO]
    budget_context: Optional[BudgetContextDTO] = None
    user_preferences_by_food_id: Optional[Dict[str, int]] = None
    policy_version: str = BudgetSelectionPolicy.VERSION


@dataclass
class BudgetAwareSelectionResultDTO:
    date: str
    logical_day_id: str
    status: BudgetSelectionStatus
    budget_envelope_idr: Optional[int]
    selected_combination: Optional[DailyCandidateCombinationDTO]
    alternatives: List[DailyCandidateCombinationDTO]
    shortfall_idr: Optional[int] = None
    search_truncated: bool = False
    explanations: List[str] = field(default_factory=list)
    policy_versions: Dict[str, str] = field(default_factory=dict)
