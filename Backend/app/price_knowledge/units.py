from typing import Optional, Tuple
from app.price_knowledge.constants import PriceUnit


def normalize_to_base_unit(
    amount: float,
    unit: PriceUnit,
    price_idr: int,
    package_quantity_grams: Optional[float] = None,
) -> Tuple[Optional[float], Optional[str]]:
    """
    Normalizes price observation into standard base rate (Rp/g, Rp/ml, or Rp/unit).
    Invariant: Never converts ml to grams without explicit density.
    Returns (price_per_base_unit, base_unit_name) or (None, None) if invalid/unknown package.
    """
    if amount <= 0 or price_idr <= 0:
        return None, None

    if unit == PriceUnit.PER_KG:
        total_grams = amount * 1000.0
        return price_idr / total_grams, "g"
    elif unit == PriceUnit.PER_100_G:
        total_grams = amount * 100.0
        return price_idr / total_grams, "g"
    elif unit == PriceUnit.PER_GRAM:
        total_grams = amount * 1.0
        return price_idr / total_grams, "g"
    elif unit == PriceUnit.PER_LITER:
        total_ml = amount * 1000.0
        return price_idr / total_ml, "ml"
    elif unit == PriceUnit.PER_100_ML:
        total_ml = amount * 100.0
        return price_idr / total_ml, "ml"
    elif unit == PriceUnit.PER_ML:
        total_ml = amount * 1.0
        return price_idr / total_ml, "ml"
    elif unit in (PriceUnit.PER_UNIT, PriceUnit.PER_SERVING):
        return price_idr / amount, "unit"
    elif unit == PriceUnit.PER_PACKAGE:
        if package_quantity_grams and package_quantity_grams > 0:
            total_grams = amount * package_quantity_grams
            return price_idr / total_grams, "g"
        return None, None

    return None, None


def convert_quantity_to_base_units(
    quantity: float,
    unit: PriceUnit,
) -> Tuple[Optional[float], Optional[str]]:
    """
    Converts a requested quantity and unit into base units ('g', 'ml', 'unit').
    """
    if quantity <= 0:
        return None, None

    if unit == PriceUnit.PER_KG:
        return quantity * 1000.0, "g"
    elif unit == PriceUnit.PER_100_G:
        return quantity * 100.0, "g"
    elif unit == PriceUnit.PER_GRAM:
        return quantity * 1.0, "g"
    elif unit == PriceUnit.PER_LITER:
        return quantity * 1000.0, "ml"
    elif unit == PriceUnit.PER_100_ML:
        return quantity * 100.0, "ml"
    elif unit == PriceUnit.PER_ML:
        return quantity * 1.0, "ml"
    elif unit in (PriceUnit.PER_UNIT, PriceUnit.PER_SERVING):
        return quantity, "unit"

    return None, None
