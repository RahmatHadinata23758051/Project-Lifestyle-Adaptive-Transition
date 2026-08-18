from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from app.price_knowledge.constants import (
    PriceUnit,
    PriceBasis,
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
from app.price_knowledge.units import (
    normalize_to_base_unit_decimal,
    convert_quantity_to_base_units_decimal,
)
from app.price_knowledge.freshness import determine_price_freshness
from app.price_knowledge.confidence import evaluate_location_match, derive_resolution_confidence
from app.price_knowledge.aggregation import aggregate_normalized_rates_decimal


def resolve_food_price(
    food_item_id: str,
    requested_quantity: float,
    requested_unit: PriceUnit,
    requested_basis: PriceBasis = PriceBasis.EDIBLE_PORTION,
    edible_portion_factor: Optional[float] = None,
    user_location: Optional[LocationDTO] = None,
    observations: Optional[List[FoodPriceObservationDTO]] = None,
    reference_date: Optional[datetime] = None,
    include_promotions: bool = False,
) -> ResolvedFoodPriceDTO:
    """
    Pure deterministic price resolver (PRICE_RESOLUTION_V01).
    Zero-I/O: Resolves target quantity cost against preloaded price observations.
    Enforces exact Decimal calculations (PRICE_ROUNDING_V01) and AS_SOLD vs EDIBLE_PORTION basis checks.
    """
    target_base_qty_dec, target_base_unit = convert_quantity_to_base_units_decimal(requested_quantity, requested_unit)
    if target_base_qty_dec is None or target_base_unit is None:
        return ResolvedFoodPriceDTO(
            food_item_id=food_item_id,
            requested_quantity=requested_quantity,
            requested_unit=requested_unit,
            requested_basis=requested_basis,
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
            requested_basis=requested_basis,
            estimated_cost_idr=None,
            source_observation_ids=[],
            normalized_unit_price_idr=None,
            location_match=LocationMatch.UNKNOWN,
            freshness_status=PriceFreshness.STALE,
            confidence=PriceConfidence.UNKNOWN,
            resolution_status=PriceResolutionStatus.NO_PRICE_DATA,
            provenance={"reason": "No price observations found for this food."},
        )

    # 1. Evaluate Observations (Normalize, Freshness, Location, Basis Compatibility)
    evaluated_items = []
    has_basis_incompatibility = False

    for obs in food_obs:
        rate_dec, base_unit = normalize_to_base_unit_decimal(
            amount=obs.amount,
            unit=obs.unit,
            price_idr=obs.price_idr,
            package_quantity_grams=obs.package_quantity_grams,
        )
        if rate_dec is None or base_unit != target_base_unit:
            continue  # Incompatible unit dimension (e.g. ml vs g)

        # Basis alignment check
        basis_conversion_applied = False
        effective_qty_factor = Decimal("1.0")

        if obs.unit in (PriceUnit.PER_UNIT, PriceUnit.PER_SERVING):
            # Discrete unit pricing is inherently per-unit/serving
            effective_qty_factor = Decimal("1.0")
        elif obs.price_basis == requested_basis:
            effective_qty_factor = Decimal("1.0")
        elif requested_basis == PriceBasis.EDIBLE_PORTION and obs.price_basis == PriceBasis.AS_SOLD:
            # Need edible portion factor to convert edible weight to as-sold weight
            if edible_portion_factor is not None and 0.0 < edible_portion_factor <= 1.0:
                effective_qty_factor = Decimal("1.0") / Decimal(str(edible_portion_factor))
                basis_conversion_applied = True
            else:
                has_basis_incompatibility = True
                continue  # Cannot resolve AS_SOLD price for EDIBLE_PORTION without factor!
        elif requested_basis == PriceBasis.AS_SOLD and obs.price_basis == PriceBasis.EDIBLE_PORTION:
            if edible_portion_factor is not None and 0.0 < edible_portion_factor <= 1.0:
                effective_qty_factor = Decimal(str(edible_portion_factor))
                basis_conversion_applied = True
            else:
                has_basis_incompatibility = True
                continue

        freshness = determine_price_freshness(obs.observed_at, reference_date=reference_date)
        loc_match = evaluate_location_match(obs.location, user_location)

        evaluated_items.append({
            "observation": obs,
            "rate_dec": rate_dec,
            "effective_qty_factor": effective_qty_factor,
            "freshness": freshness,
            "location_match": loc_match,
            "basis_conversion_applied": basis_conversion_applied,
        })

    if not evaluated_items:
        res_status = (
            PriceResolutionStatus.INCOMPATIBLE_BASIS
            if has_basis_incompatibility
            else PriceResolutionStatus.INCOMPATIBLE_UNIT
        )
        reason_msg = (
            "Observation price basis is AS_SOLD but requested EDIBLE_PORTION without known edible portion factor."
            if has_basis_incompatibility
            else "No price observation compatible with requested unit dimension."
        )
        return ResolvedFoodPriceDTO(
            food_item_id=food_item_id,
            requested_quantity=requested_quantity,
            requested_unit=requested_unit,
            requested_basis=requested_basis,
            estimated_cost_idr=None,
            source_observation_ids=[],
            normalized_unit_price_idr=None,
            location_match=LocationMatch.UNKNOWN,
            freshness_status=PriceFreshness.STALE,
            confidence=PriceConfidence.UNKNOWN,
            resolution_status=res_status,
            provenance={"reason": reason_msg},
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

    # 3. Median Aggregation & Exact Decimal Rounding (PRICE_AGGREGATION_V01 & PRICE_ROUNDING_V01)
    rates_dec = [it["rate_dec"] for it in selected_tier_items]
    aggregated_rate_dec = aggregate_normalized_rates_decimal(rates_dec)

    # Apply basis conversion factor (if any)
    primary_item = selected_tier_items[0]
    effective_qty_dec = target_base_qty_dec * primary_item["effective_qty_factor"]

    # Decimal exact calculation with ROUND_HALF_UP
    total_cost_dec = (effective_qty_dec * aggregated_rate_dec).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    total_cost_idr = int(total_cost_dec)

    # Provenance and Multi-Dimensional Confidence
    loc_match = primary_item["location_match"]
    freshness = primary_item["freshness"]
    source_type = primary_item["observation"].source_type
    quality_status = primary_item["observation"].quality_status
    basis_conv = primary_item["basis_conversion_applied"]

    confidence = derive_resolution_confidence(
        location_match=loc_match,
        freshness=freshness,
        source_type=source_type,
        quality_status=quality_status,
        observation_count=len(selected_tier_items),
        basis_conversion_applied=basis_conv,
    )

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
        "rounding_policy_version": PricePolicy.ROUNDING_POLICY_VERSION,
        "confidence_policy_version": PricePolicy.CONFIDENCE_POLICY_VERSION,
        "base_rate_idr": float(round(aggregated_rate_dec, 4)),
        "base_unit": target_base_unit,
        "basis_conversion_applied": basis_conv,
    }

    return ResolvedFoodPriceDTO(
        food_item_id=food_item_id,
        requested_quantity=requested_quantity,
        requested_unit=requested_unit,
        requested_basis=requested_basis,
        estimated_cost_idr=total_cost_idr,
        source_observation_ids=obs_ids,
        normalized_unit_price_idr=float(round(aggregated_rate_dec, 4)),
        location_match=loc_match,
        freshness_status=freshness,
        confidence=confidence,
        resolution_status=resolution_status,
        edible_portion_factor_applied=edible_portion_factor if basis_conv else None,
        provenance=provenance,
    )
