from typing import Dict, Any, Optional
from dataclasses import dataclass
from app.nutrition.constants import PhysicalActivityCategory, NutritionPolicy


@dataclass
class EnergyCalculationResult:
    method: str
    policy_version: str
    pal_category: PhysicalActivityCategory
    pal_reason: str
    maintenance_estimate_kcal: float
    requested_surplus_kcal: int
    applied_surplus_kcal: int
    surplus_was_adjusted: bool
    target_kcal: float
    rounded_display_kcal: int


class EnergyCalculator:
    """
    Pure deterministic energy requirement calculator based on 2023 DRI EER equations.
    Zero DB, Zero Network, Zero LLM.
    """

    @staticmethod
    def calculate_eer(
        sex: str,
        age: int,
        height_cm: float,
        weight_kg: float,
        pal: PhysicalActivityCategory,
    ) -> float:
        if age < NutritionPolicy.MINIMUM_SUPPORTED_AGE:
            raise ValueError(f"Usia {age} di bawah batas minimal {NutritionPolicy.MINIMUM_SUPPORTED_AGE} tahun untuk 2023 DRI EER dewasa.")

        if height_cm <= 0 or weight_kg <= 0:
            raise ValueError("Tinggi badan dan berat badan harus bernilai positif.")

        s = sex.upper()

        if s in ["MALE", "LAKI_LAKI", "PRIA"]:
            if pal == PhysicalActivityCategory.INACTIVE:
                eer = 753.07 - (10.83 * age) + (6.50 * height_cm) + (14.10 * weight_kg)
            elif pal == PhysicalActivityCategory.LOW_ACTIVE:
                eer = 581.47 - (10.83 * age) + (8.30 * height_cm) + (14.94 * weight_kg)
            elif pal == PhysicalActivityCategory.ACTIVE:
                eer = 1004.82 - (10.83 * age) + (6.52 * height_cm) + (15.91 * weight_kg)
            elif pal == PhysicalActivityCategory.VERY_ACTIVE:
                eer = -517.88 - (10.83 * age) + (15.61 * height_cm) + (19.11 * weight_kg)
            else:
                raise ValueError(f"Kategori PAL '{pal}' tidak dikenal.")
        elif s in ["FEMALE", "PEREMPUAN", "WANITA"]:
            if pal == PhysicalActivityCategory.INACTIVE:
                eer = 584.90 - (7.01 * age) + (5.72 * height_cm) + (11.71 * weight_kg)
            elif pal == PhysicalActivityCategory.LOW_ACTIVE:
                eer = 575.77 - (7.01 * age) + (6.60 * height_cm) + (12.14 * weight_kg)
            elif pal == PhysicalActivityCategory.ACTIVE:
                eer = 710.25 - (7.01 * age) + (6.54 * height_cm) + (12.34 * weight_kg)
            elif pal == PhysicalActivityCategory.VERY_ACTIVE:
                eer = 511.83 - (7.01 * age) + (9.07 * height_cm) + (12.56 * weight_kg)
            else:
                raise ValueError(f"Kategori PAL '{pal}' tidak dikenal.")
        else:
            raise ValueError(f"Jenis kelamin '{sex}' tidak valid. Gunakan 'MALE' atau 'FEMALE'.")

        return round(eer, 2)

    @classmethod
    def calculate_weight_gain_target(
        cls,
        sex: str,
        age: int,
        height_cm: float,
        weight_kg: float,
        pal: PhysicalActivityCategory,
        pal_reason: str = "Klasifikasi aktivitas terstruktur.",
        starting_surplus_kcal: int = NutritionPolicy.DEFAULT_INITIAL_SURPLUS_KCAL,
    ) -> EnergyCalculationResult:
        maintenance = cls.calculate_eer(
            sex=sex,
            age=age,
            height_cm=height_cm,
            weight_kg=weight_kg,
            pal=pal,
        )

        requested_surplus = starting_surplus_kcal
        applied_surplus = min(max(requested_surplus, 0), NutritionPolicy.MAX_STARTING_SURPLUS_KCAL)
        surplus_adjusted = applied_surplus != requested_surplus

        target = round(maintenance + applied_surplus, 2)
        rounded_display = int(round(target / 50.0) * 50)

        return EnergyCalculationResult(
            method=NutritionPolicy.EER_METHOD,
            policy_version=NutritionPolicy.VERSION,
            pal_category=pal,
            pal_reason=pal_reason,
            maintenance_estimate_kcal=maintenance,
            requested_surplus_kcal=requested_surplus,
            applied_surplus_kcal=applied_surplus,
            surplus_was_adjusted=surplus_adjusted,
            target_kcal=target,
            rounded_display_kcal=rounded_display,
        )
