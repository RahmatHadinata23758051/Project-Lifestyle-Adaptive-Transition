from typing import Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from app.price_knowledge.constants import PriceUnit


def normalize_to_base_unit_decimal(
    amount: float,
    unit: PriceUnit,
    price_idr: int,
    package_quantity_grams: Optional[float] = None,
) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Normalizes price observation into standard base rate Decimal (Rp/g, Rp/ml, or Rp/unit).
    Invariant: Never converts ml to grams without explicit density.
    Returns (price_per_base_unit: Decimal, base_unit_name) or (None, None).
    """
    if amount <= 0 or price_idr <= 0:
        return None, None

    dec_amount = Decimal(str(amount))
    dec_price = Decimal(str(price_idr))

    if unit == PriceUnit.PER_KG:
        total_grams = dec_amount * Decimal("1000")
        return dec_price / total_grams, "g"
    elif unit == PriceUnit.PER_100_G:
        total_grams = dec_amount * Decimal("100")
        return dec_price / total_grams, "g"
    elif unit == PriceUnit.PER_GRAM:
        total_grams = dec_amount * Decimal("1")
        return dec_price / total_grams, "g"
    elif unit == PriceUnit.PER_LITER:
        total_ml = dec_amount * Decimal("1000")
        return dec_price / total_ml, "ml"
    elif unit == PriceUnit.PER_100_ML:
        total_ml = dec_amount * Decimal("100")
        return dec_price / total_ml, "ml"
    elif unit == PriceUnit.PER_ML:
        total_ml = dec_amount * Decimal("1")
        return dec_price / total_ml, "ml"
    elif unit in (PriceUnit.PER_UNIT, PriceUnit.PER_SERVING):
        return dec_price / dec_amount, "unit"
    elif unit == PriceUnit.PER_PACKAGE:
        if package_quantity_grams and package_quantity_grams > 0:
            total_grams = dec_amount * Decimal(str(package_quantity_grams))
            return dec_price / total_grams, "g"
        return None, None

    return None, None


def normalize_to_base_unit(
    amount: float,
    unit: PriceUnit,
    price_idr: int,
    package_quantity_grams: Optional[float] = None,
) -> Tuple[Optional[float], Optional[str]]:
    rate_dec, unit_str = normalize_to_base_unit_decimal(
        amount=amount,
        unit=unit,
        price_idr=price_idr,
        package_quantity_grams=package_quantity_grams,
    )
    if rate_dec is None:
        return None, None
    return float(rate_dec), unit_str


def convert_quantity_to_base_units_decimal(
    quantity: float,
    unit: PriceUnit,
) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Converts a requested quantity and unit into base units Decimal ('g', 'ml', 'unit').
    """
    if quantity <= 0:
        return None, None

    dec_qty = Decimal(str(quantity))

    if unit == PriceUnit.PER_KG:
        return dec_qty * Decimal("1000"), "g"
    elif unit == PriceUnit.PER_100_G:
        return dec_qty * Decimal("100"), "g"
    elif unit == PriceUnit.PER_GRAM:
        return dec_qty * Decimal("1"), "g"
    elif unit == PriceUnit.PER_LITER:
        return dec_qty * Decimal("1000"), "ml"
    elif unit == PriceUnit.PER_100_ML:
        return dec_qty * Decimal("100"), "ml"
    elif unit == PriceUnit.PER_ML:
        return dec_qty * Decimal("1"), "ml"
    elif unit in (PriceUnit.PER_UNIT, PriceUnit.PER_SERVING):
        return dec_qty, "unit"

    return None, None


def convert_quantity_to_base_units(
    quantity: float,
    unit: PriceUnit,
) -> Tuple[Optional[float], Optional[str]]:
    qty_dec, unit_str = convert_quantity_to_base_units_decimal(quantity, unit)
    if qty_dec is None:
        return None, None
    return float(qty_dec), unit_str
