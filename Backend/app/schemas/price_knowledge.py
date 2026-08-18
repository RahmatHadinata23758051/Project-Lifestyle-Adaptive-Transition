from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
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


class LocationSchema(BaseModel):
    country: str = "ID"
    province: Optional[str] = None
    city_regency: Optional[str] = None
    district: Optional[str] = None
    market_or_store: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FoodPriceObservationResponse(BaseModel):
    id: str
    food_item_id: str
    amount: float
    unit: PriceUnit
    price_idr: int
    currency_code: str = "IDR"
    price_basis: PriceBasis = PriceBasis.AS_SOLD
    source_type: PriceSourceType
    source_reference: Optional[str] = None
    observed_at: datetime
    location: LocationSchema
    scope_type: PriceScopeType
    is_promotional: bool = False
    confidence: PriceConfidence
    quality_status: PriceQuality

    model_config = ConfigDict(from_attributes=True)


class ResolveFoodPriceInput(BaseModel):
    food_item_id: str
    requested_quantity: float = Field(..., gt=0)
    requested_unit: PriceUnit = PriceUnit.PER_GRAM
    user_location: Optional[LocationSchema] = None
    include_promotions: bool = False


class ResolveFoodPriceResponse(BaseModel):
    food_item_id: str
    requested_quantity: float
    requested_unit: PriceUnit
    estimated_cost_idr: Optional[int] = None
    source_observation_ids: List[str] = []
    normalized_unit_price_idr: Optional[float] = None
    location_match: LocationMatch
    freshness_status: PriceFreshness
    confidence: PriceConfidence
    resolution_status: PriceResolutionStatus
    provenance: Dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)


class CandidateItemCostResponse(BaseModel):
    food_item_id: str
    canonical_name: str
    grams: float
    estimated_cost_idr: Optional[int] = None
    resolution_status: PriceResolutionStatus
    confidence: PriceConfidence
    location_match: LocationMatch
    source_observation_ids: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class CandidateCostPreviewResponse(BaseModel):
    candidate_id: str
    estimated_cost_idr: Optional[int] = None
    known_subtotal_idr: int
    cost_completeness: CostCompleteness
    priced_item_count: int
    total_item_count: int
    item_costs: List[CandidateItemCostResponse]
    confidence: PriceConfidence
    price_policy_version: str = PricePolicy.VERSION

    model_config = ConfigDict(from_attributes=True)
