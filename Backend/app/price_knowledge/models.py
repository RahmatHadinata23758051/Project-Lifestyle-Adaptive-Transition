from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from app.price_knowledge.constants import (
    PriceUnit,
    PriceBasis,
    PriceSourceType,
    PriceScopeType,
    PriceQuality,
    PriceConfidence,
    LocationMatch,
    PriceFreshness,
    PriceResolutionStatus,
    CostCompleteness,
    PricePolicy,
)


@dataclass
class LocationDTO:
    country: str = "ID"
    province: Optional[str] = None
    city_regency: Optional[str] = None
    district: Optional[str] = None
    market_or_store: Optional[str] = None


@dataclass
class FoodPriceObservationDTO:
    id: str
    food_item_id: str
    amount: float
    unit: PriceUnit
    price_idr: int
    currency_code: str = PricePolicy.DEFAULT_CURRENCY
    price_basis: PriceBasis = PriceBasis.AS_SOLD
    source_type: PriceSourceType = PriceSourceType.MANUAL_CURATED
    source_id: Optional[str] = None
    source_reference: Optional[str] = None
    observed_at: datetime = field(default_factory=datetime.utcnow)
    location: LocationDTO = field(default_factory=LocationDTO)
    scope_type: PriceScopeType = PriceScopeType.GLOBAL_REFERENCE
    owner_user_id: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_promotional: bool = False
    confidence: PriceConfidence = PriceConfidence.HIGH
    quality_status: PriceQuality = PriceQuality.VERIFIED
    package_quantity_grams: Optional[float] = None


@dataclass
class ResolvedFoodPriceDTO:
    food_item_id: str
    requested_quantity: float
    requested_unit: PriceUnit
    estimated_cost_idr: Optional[int]
    source_observation_ids: List[str]
    normalized_unit_price_idr: Optional[float]
    location_match: LocationMatch
    freshness_status: PriceFreshness
    confidence: PriceConfidence
    resolution_status: PriceResolutionStatus
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ItemCostEstimateDTO:
    food_item_id: str
    canonical_name: str
    grams: float
    estimated_cost_idr: Optional[int]
    resolution_status: PriceResolutionStatus
    confidence: PriceConfidence
    location_match: LocationMatch
    source_observation_ids: List[str] = field(default_factory=list)


@dataclass
class CandidateCostEstimateDTO:
    candidate_id: str
    estimated_cost_idr: Optional[int]
    known_subtotal_idr: int
    cost_completeness: CostCompleteness
    priced_item_count: int
    total_item_count: int
    item_costs: List[ItemCostEstimateDTO]
    confidence: PriceConfidence
    price_policy_version: str = PricePolicy.VERSION
