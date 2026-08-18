from typing import Optional, Dict, Any
from app.food_knowledge.constants import NutrientCompleteness, BasisType
from app.food_knowledge.models import NutrientProfileDTO


def determine_nutrient_completeness(
    energy_kcal: Optional[float],
    protein_g: Optional[float],
    fat_g: Optional[float],
    carbohydrate_g: Optional[float],
) -> NutrientCompleteness:
    core_nutrients = [energy_kcal, protein_g, fat_g, carbohydrate_g]
    non_null_count = sum(1 for n in core_nutrients if n is not None)

    if non_null_count == 4:
        return NutrientCompleteness.CORE_COMPLETE
    elif non_null_count > 0:
        return NutrientCompleteness.PARTIAL
    else:
        return NutrientCompleteness.INSUFFICIENT


def calculate_edible_weight(
    purchase_weight_g: float,
    edible_portion_percent: Optional[float] = None,
) -> float:
    if purchase_weight_g < 0:
        raise ValueError("Berat pembelian tidak boleh bernilai negatif.")

    if edible_portion_percent is None:
        return purchase_weight_g

    if not (0.0 <= edible_portion_percent <= 100.0):
        raise ValueError("Persentase bagian yang dapat dimakan (edible portion) harus antara 0 dan 100.")

    return round(purchase_weight_g * (edible_portion_percent / 100.0), 2)


def scale_nutrients(
    nutrients: NutrientProfileDTO,
    consumed_grams: float,
) -> NutrientProfileDTO:
    """
    Pure deterministic nutrient scaling.
    CRITICAL INVARIANT: Null != 0. If a nutrient value was None in the source, it must remain None after scaling.
    """
    if consumed_grams < 0:
        raise ValueError("Gram konsumsi tidak boleh negatif.")

    if nutrients.reference_amount <= 0:
        raise ValueError("Reference amount harus bernilai positif.")

    ratio = consumed_grams / nutrients.reference_amount

    def _scale(val: Optional[float]) -> Optional[float]:
        if val is None:
            return None
        return round(val * ratio, 2)

    scaled_energy = _scale(nutrients.energy_kcal)
    scaled_protein = _scale(nutrients.protein_g)
    scaled_fat = _scale(nutrients.fat_g)
    scaled_carb = _scale(nutrients.carbohydrate_g)
    scaled_fiber = _scale(nutrients.fiber_g)
    scaled_water = _scale(nutrients.water_g)

    scaled_micronutrients: Optional[Dict[str, Any]] = None
    if nutrients.optional_micronutrients is not None:
        scaled_micronutrients = {}
        for k, v in nutrients.optional_micronutrients.items():
            if isinstance(v, (int, float)):
                scaled_micronutrients[k] = round(v * ratio, 2)
            else:
                scaled_micronutrients[k] = v

    return NutrientProfileDTO(
        energy_kcal=scaled_energy,
        protein_g=scaled_protein,
        fat_g=scaled_fat,
        carbohydrate_g=scaled_carb,
        fiber_g=scaled_fiber,
        water_g=scaled_water,
        optional_micronutrients=scaled_micronutrients,
        basis_type=nutrients.basis_type,
        reference_amount=consumed_grams,
        reference_unit="g",
        edible_portion_percent=nutrients.edible_portion_percent,
        data_quality_status=nutrients.data_quality_status,
        completeness=determine_nutrient_completeness(scaled_energy, scaled_protein, scaled_fat, scaled_carb),
    )
