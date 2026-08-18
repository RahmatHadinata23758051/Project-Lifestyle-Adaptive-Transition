from typing import List, Optional, Dict, Any
from datetime import datetime
from app.price_knowledge.constants import (
    PriceUnit,
    PriceFreshness,
    LocationMatch,
    PriceResolutionStatus,
    PriceConfidence,
    PricePolicy,
)
from app.price_knowledge.models import (
    LocationDTO,
    FoodPriceObservationDTO,
    ResolvedFoodPriceDTO,
)
from app.price_knowledge.units import normalize_to_base_unit, convert_quantity_to_base_units
from app.price_knowledge.freshness import determine_price_freshness
from app.price_knowledge.confidence import evaluate_location_match, derive_resolution_confidence
from app.price_knowledge.aggregation import aggregate_normalized_rates


def resolve_food_price(
    food_item_id: str,
    requested_quantity: float,
    requested_unit: PriceUnit,
    user_location: Optional[LocationDTO] = None,
    observations: Optional[List[FoodPriceObservationDTO]] = None,
    reference_date: Optional[datetime] = None,
    include_promotions: bool = False,
) -> ResolvedFoodPriceDTO:
    """
    Pure deterministic price resolver (PRICE_RESOLUTION_V01).
    Zero-I/O: Resolves target quantity cost against preloaded price observations.
    Follows deterministic location and freshness fallback hierarchy.
    """
    target_base_qty, target_base_unit = convert_quantity_to_base_units(requested_quantity, requested_unit)
    if target_base_qty is None or target_base_unit is None:
        return ResolvedFoodPriceDTO(
            food_item_id=food_item_id,
            requested_quantity=requested_quantity,
            requested_unit=requested_unit,
            estimated_cost_idr=None,
            source_observation_ids=[],
            normalized_unit_price_idr=None,
            location_match=LocationMatch.UNKNOWN,
            freshness_status=PriceFreshness.STALE,
            confidence=PriceConfidence.UNKNOWN,
            resolution_status=PriceResolutionStatus.INCOMPATIBLE_UNIT,
            provenance={"reason": "Invalid requested quantity or unit."},
        )

    all_obs = observations or []
    food_obs = [o for o in all_obs if o.food_item_id == food_item_id]

    if not include_promotions:
        food_obs = [o for o in food_obs if not o.is_promotional]

    if not food_obs:
        return ResolvedFoodPriceDTO(
            food_item_id=food_item_id,
            requested_quantity=requested_quantity,
            requested_unit=requested_unit,
            estimated_cost_idr=None,
            source_observation_ids=[],
            normalized_unit_price_idr=None,
            location_match=LocationMatch.UNKNOWN,
            freshness_status=PriceFreshness.STALE,
            confidence=PriceConfidence.UNKNOWN,
            resolution_status=PriceResolutionStatus.NO_PRICE_DATA,
            provenance={"reason": "No price observations found for this food."},
        )

    # 1. Evaluate Observations (Normalize, Freshness, Location)
    evaluated_items = []
    for obs in food_obs:
        rate, base_unit = normalize_to_base_unit(
            amount=obs.amount,
            unit=obs.unit,
            price_idr=obs.price_idr,
            package_quantity_grams=obs.package_quantity_grams,
        )
        if rate is None or base_unit != target_base_unit:
            continue  # Incompatible unit dimension (e.g. ml vs g)

        freshness = determine_price_freshness(obs.observed_at, reference_date=reference_date)
        loc_match = evaluate_location_match(obs.location, user_location)

        evaluated_items.append({
            "observation": obs,
            "rate": rate,
            "freshness": freshness,
            "location_match": loc_match,
        })

    if not evaluated_items:
        return ResolvedFoodPriceDTO(
            food_item_id=food_item_id,
            requested_quantity=requested_quantity,
            requested_unit=requested_unit,
            estimated_cost_idr=None,
            source_observation_ids=[],
            normalized_unit_price_idr=None,
            location_match=LocationMatch.UNKNOWN,
            freshness_status=PriceFreshness.STALE,
            confidence=PriceConfidence.UNKNOWN,
            resolution_status=PriceResolutionStatus.INCOMPATIBLE_UNIT,
            provenance={"reason": "No price observation compatible with requested unit dimension."},
        )

    # 2. Deterministic Fallback Hierarchy (PRICE_RESOLUTION_V01)
    tier_definitions = [
        # Tier 1: Exact local fresh
        lambda item: item["freshness"] == PriceFreshness.FRESH and item["location_match"] == LocationMatch.EXACT_LOCAL,
        # Tier 2: Same city fresh
        lambda item: item["freshness"] == PriceFreshness.FRESH and item["location_match"] == LocationMatch.SAME_CITY,
        # Tier 3: Same province fresh
        lambda item: item["freshness"] == PriceFreshness.FRESH and item["location_match"] == LocationMatch.SAME_PROVINCE,
        # Tier 4: National fresh
        lambda item: item["freshness"] == PriceFreshness.FRESH and item["location_match"] == LocationMatch.NATIONAL,
        # Tier 5: Local / City aging
        lambda item: item["freshness"] == PriceFreshness.AGING and item["location_match"] in (LocationMatch.EXACT_LOCAL, LocationMatch.SAME_CITY),
        # Tier 6: Broader aging
        lambda item: item["freshness"] == PriceFreshness.AGING and item["location_match"] in (LocationMatch.SAME_PROVINCE, LocationMatch.NATIONAL),
        # Tier 7: Any stale
        lambda item: item["freshness"] == PriceFreshness.STALE,
    ]

    selected_tier_items = []
    tier_index = -1
    for idx, tier_pred in enumerate(tier_definitions):
        matches = [it for it in evaluated_items if tier_pred(it)]
        if matches:
            selected_tier_items = matches
            tier_index = idx
            break

    if not selected_tier_items:
        selected_tier_items = evaluated_items

    # 3. Median Aggregation (PRICE_AGGREGATION_V01)
    rates = [it["rate"] for it in selected_tier_items]
    aggregated_rate = aggregate_normalized_rates(rates)
    total_cost_idr = int(round(aggregated_rate * target_base_qty))

    # Provenance and Confidence
    primary_item = selected_tier_items[0]
    loc_match = primary_item["location_match"]
    freshness = primary_item["freshness"]
    confidence = derive_resolution_confidence(loc_match, freshness, len(selected_tier_items))

    resolution_status = (
        PriceResolutionStatus.RESOLVED
        if tier_index == 0
        else (PriceResolutionStatus.STALE_ONLY if freshness == PriceFreshness.STALE else PriceResolutionStatus.RESOLVED_WITH_FALLBACK)
    )

    obs_ids = [it["observation"].id for it in selected_tier_items]

    provenance = {
        "fallback_tier": tier_index + 1,
        "observations_used_count": len(selected_tier_items),
        "policy_version": PricePolicy.RESOLUTION_POLICY_VERSION,
        "aggregation_policy_version": PricePolicy.AGGREGATION_POLICY_VERSION,
        "base_rate_idr": aggregated_rate,
        "base_unit": target_base_unit,
    }

    return ResolvedFoodPriceDTO(
        food_item_id=food_item_id,
        requested_quantity=requested_quantity,
        requested_unit=requested_unit,
        estimated_cost_idr=total_cost_idr,
        source_observation_ids=obs_ids,
        normalized_unit_price_idr=aggregated_rate,
        location_match=loc_match,
        freshness_status=freshness,
        confidence=confidence,
        resolution_status=resolution_status,
        provenance=provenance,
    )
