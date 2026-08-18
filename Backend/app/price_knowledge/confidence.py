from typing import Optional
from app.price_knowledge.constants import (
    LocationMatch,
    PriceConfidence,
    PriceFreshness,
    PriceSourceType,
    PriceQuality,
)
from app.price_knowledge.models import LocationDTO


def evaluate_location_match(
    obs_location: LocationDTO,
    user_location: Optional[LocationDTO],
) -> LocationMatch:
    """
    Evaluates geographical specificity between observed price location and user location context.
    """
    if user_location is None:
        return LocationMatch.NATIONAL if obs_location.country == "ID" else LocationMatch.UNKNOWN

    if (
        obs_location.market_or_store
        and user_location.market_or_store
        and obs_location.market_or_store.lower() == user_location.market_or_store.lower()
    ):
        return LocationMatch.EXACT_LOCAL

    if (
        obs_location.city_regency
        and user_location.city_regency
        and obs_location.city_regency.lower() == user_location.city_regency.lower()
    ):
        return LocationMatch.SAME_CITY

    if (
        obs_location.province
        and user_location.province
        and obs_location.province.lower() == user_location.province.lower()
    ):
        return LocationMatch.SAME_PROVINCE

    if obs_location.country and user_location.country and obs_location.country.upper() == user_location.country.upper():
        return LocationMatch.NATIONAL

    return LocationMatch.UNKNOWN


def derive_resolution_confidence(
    location_match: LocationMatch,
    freshness: PriceFreshness,
    source_type: PriceSourceType,
    quality_status: PriceQuality,
    observation_count: int,
    basis_conversion_applied: bool = False,
) -> PriceConfidence:
    """
    Deterministic Confidence Policy (PRICE_CONFIDENCE_V01).
    Evaluates multi-dimensional evidence:
    - Source trustworthiness & verification status
    - Location proximity
    - Observation freshness
    - Basis alignment
    """
    is_trusted_source = source_type in (
        PriceSourceType.GOVERNMENT_DATA,
        PriceSourceType.MANUAL_CURATED,
        PriceSourceType.RETAILER_FEED,
    ) and quality_status in (PriceQuality.VERIFIED, PriceQuality.CURATED)

    # Stale data is always LOW
    if freshness == PriceFreshness.STALE:
        return PriceConfidence.LOW

    # Fresh + Trusted Source
    if freshness == PriceFreshness.FRESH and is_trusted_source:
        if location_match in (LocationMatch.EXACT_LOCAL, LocationMatch.SAME_CITY):
            return PriceConfidence.HIGH
        elif location_match == LocationMatch.SAME_PROVINCE:
            return PriceConfidence.MEDIUM
        elif location_match == LocationMatch.NATIONAL:
            return PriceConfidence.MEDIUM if observation_count >= 2 else PriceConfidence.LOW

    # Fresh + User Reported
    if freshness == PriceFreshness.FRESH and not is_trusted_source:
        if location_match in (LocationMatch.EXACT_LOCAL, LocationMatch.SAME_CITY):
            return PriceConfidence.MEDIUM
        return PriceConfidence.LOW

    # Aging
    if freshness == PriceFreshness.AGING:
        if is_trusted_source and location_match in (LocationMatch.EXACT_LOCAL, LocationMatch.SAME_CITY):
            return PriceConfidence.MEDIUM
        return PriceConfidence.LOW

    return PriceConfidence.LOW
