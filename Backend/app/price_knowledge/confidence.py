from typing import Optional
from app.price_knowledge.constants import LocationMatch, PriceConfidence, PriceFreshness
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
    observation_count: int,
) -> PriceConfidence:
    """
    Categorical confidence derivation based on location match and data freshness.
    """
    if freshness == PriceFreshness.FRESH:
        if location_match in (LocationMatch.EXACT_LOCAL, LocationMatch.SAME_CITY):
            return PriceConfidence.HIGH
        elif location_match == LocationMatch.SAME_PROVINCE:
            return PriceConfidence.MEDIUM
        elif location_match == LocationMatch.NATIONAL:
            return PriceConfidence.MEDIUM if observation_count >= 3 else PriceConfidence.LOW

    if freshness == PriceFreshness.AGING:
        if location_match in (LocationMatch.EXACT_LOCAL, LocationMatch.SAME_CITY):
            return PriceConfidence.MEDIUM
        return PriceConfidence.LOW

    return PriceConfidence.LOW
