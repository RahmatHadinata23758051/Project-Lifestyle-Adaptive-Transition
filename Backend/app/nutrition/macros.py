from typing import Dict, Any, Optional
from dataclasses import dataclass
from app.nutrition.constants import NutritionPolicy


@dataclass
class MacroReferenceResult:
    protein_rda_floor_g: float
    training_target_g: Optional[float]
    amdr_percentages: Dict[str, list[int]]
    amdr_gram_ranges: Dict[str, list[int]]


class MacroCalculator:
    """
    Calculates nutritional baseline guardrails and references based on IOM / National Academies AMDR & RDA.
    """

    @staticmethod
    def calculate_protein_rda_floor(weight_kg: float) -> float:
        if weight_kg <= 0:
            raise ValueError("Berat badan harus bernilai positif.")
        return round(weight_kg * NutritionPolicy.PROTEIN_RDA_FLOOR_G_PER_KG, 1)

    @classmethod
    def calculate_macro_reference(
        cls,
        weight_kg: float,
        target_kcal: float,
    ) -> MacroReferenceResult:
        protein_floor = cls.calculate_protein_rda_floor(weight_kg)

        carb_min_kcal = target_kcal * (NutritionPolicy.AMDR_CARBOHYDRATE_PERCENT[0] / 100.0)
        carb_max_kcal = target_kcal * (NutritionPolicy.AMDR_CARBOHYDRATE_PERCENT[1] / 100.0)

        fat_min_kcal = target_kcal * (NutritionPolicy.AMDR_FAT_PERCENT[0] / 100.0)
        fat_max_kcal = target_kcal * (NutritionPolicy.AMDR_FAT_PERCENT[1] / 100.0)

        protein_min_kcal = target_kcal * (NutritionPolicy.AMDR_PROTEIN_PERCENT[0] / 100.0)
        protein_max_kcal = target_kcal * (NutritionPolicy.AMDR_PROTEIN_PERCENT[1] / 100.0)

        # Gram conversion: Carb 4 kcal/g, Protein 4 kcal/g, Fat 9 kcal/g
        gram_ranges = {
            "carbohydrate_g": [int(round(carb_min_kcal / 4.0)), int(round(carb_max_kcal / 4.0))],
            "fat_g": [int(round(fat_min_kcal / 9.0)), int(round(fat_max_kcal / 9.0))],
            "protein_g": [int(round(protein_min_kcal / 4.0)), int(round(protein_max_kcal / 4.0))],
        }

        percentages = {
            "carbohydrate_percent": list(NutritionPolicy.AMDR_CARBOHYDRATE_PERCENT),
            "fat_percent": list(NutritionPolicy.AMDR_FAT_PERCENT),
            "protein_percent": list(NutritionPolicy.AMDR_PROTEIN_PERCENT),
        }

        return MacroReferenceResult(
            protein_rda_floor_g=protein_floor,
            training_target_g=None,  # TBD per specification section 19
            amdr_percentages=percentages,
            amdr_gram_ranges=gram_ranges,
        )
