from typing import List, Optional
from datetime import datetime
from app.price_knowledge.constants import (
    PriceUnit,
    PriceConfidence,
    PriceResolutionStatus,
    CostCompleteness,
    LocationMatch,
    PricePolicy,
)
from app.price_knowledge.models import (
    LocationDTO,
    FoodPriceObservationDTO,
    ItemCostEstimateDTO,
    CandidateCostEstimateDTO,
)
from app.price_knowledge.resolver import resolve_food_price
from app.food_candidates.models import FoodCandidateSetDTO


def _get_weakest_confidence(confidences: List[PriceConfidence]) -> PriceConfidence:
    if not confidences:
        return PriceConfidence.UNKNOWN
    if PriceConfidence.UNKNOWN in confidences:
        return PriceConfidence.UNKNOWN
    if PriceConfidence.LOW in confidences:
        return PriceConfidence.LOW
    if PriceConfidence.MEDIUM in confidences:
        return PriceConfidence.MEDIUM
    return PriceConfidence.HIGH


def estimate_candidate_cost(
    candidate: FoodCandidateSetDTO,
    user_location: Optional[LocationDTO] = None,
    observations: Optional[List[FoodPriceObservationDTO]] = None,
    reference_date: Optional[datetime] = None,
) -> CandidateCostEstimateDTO:
    """
    Pure deterministic candidate cost estimation (CANDIDATE_COST_V01).
    Estimates consumption cost for a food candidate set without optimizing budget.
    Preserves completeness state (COMPLETE vs PARTIAL vs UNAVAILABLE).
    """
    item_costs: List[ItemCostEstimateDTO] = []
    priced_sum = 0
    priced_count = 0
    confidences: List[PriceConfidence] = []

    for item in candidate.items:
        # Determine quantity and unit based on grams or discrete unit
        res = resolve_food_price(
            food_item_id=item.food_item_id,
            requested_quantity=item.grams,
            requested_unit=PriceUnit.PER_GRAM,
            user_location=user_location,
            observations=observations,
            reference_date=reference_date,
        )

        item_costs.append(
            ItemCostEstimateDTO(
                food_item_id=item.food_item_id,
                canonical_name=item.canonical_name,
                grams=item.grams,
                estimated_cost_idr=res.estimated_cost_idr,
                resolution_status=res.resolution_status,
                confidence=res.confidence,
                location_match=res.location_match,
                source_observation_ids=res.source_observation_ids,
            )
        )

        if res.estimated_cost_idr is not None and res.resolution_status in (
            PriceResolutionStatus.RESOLVED,
            PriceResolutionStatus.RESOLVED_WITH_FALLBACK,
            PriceResolutionStatus.STALE_ONLY,
        ):
            priced_sum += res.estimated_cost_idr
            priced_count += 1
            confidences.append(res.confidence)
        else:
            confidences.append(PriceConfidence.UNKNOWN)

    total_items = len(candidate.items)
    if priced_count == total_items and total_items > 0:
        completeness = CostCompleteness.COMPLETE
        estimated_total = priced_sum
    elif priced_count > 0:
        completeness = CostCompleteness.PARTIAL
        estimated_total = None  # Never present partial subtotal as complete total!
    else:
        completeness = CostCompleteness.UNAVAILABLE
        estimated_total = None

    candidate_conf = _get_weakest_confidence(confidences) if priced_count > 0 else PriceConfidence.UNKNOWN

    return CandidateCostEstimateDTO(
        candidate_id=candidate.candidate_id,
        estimated_cost_idr=estimated_total,
        known_subtotal_idr=priced_sum,
        cost_completeness=completeness,
        priced_item_count=priced_count,
        total_item_count=total_items,
        item_costs=item_costs,
        confidence=candidate_conf,
        price_policy_version=PricePolicy.CANDIDATE_COST_POLICY_VERSION,
    )
