from enum import Enum


class PhysicalActivityCategory(str, Enum):
    INACTIVE = "INACTIVE"
    LOW_ACTIVE = "LOW_ACTIVE"
    ACTIVE = "ACTIVE"
    VERY_ACTIVE = "VERY_ACTIVE"


class NutritionEligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NEEDS_MORE_DATA = "NEEDS_MORE_DATA"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    PROFESSIONAL_GUIDANCE_RECOMMENDED = "PROFESSIONAL_GUIDANCE_RECOMMENDED"


class NutritionPolicy:
    VERSION: str = "NUTRITION_V0_1"
    EER_METHOD: str = "DRI_EER_2023"
    MINIMUM_SUPPORTED_AGE: int = 19
    DEFAULT_INITIAL_SURPLUS_KCAL: int = 300
    MAX_STARTING_SURPLUS_KCAL: int = 500
    PROTEIN_RDA_FLOOR_G_PER_KG: float = 0.8

    # Acceptable Macronutrient Distribution Ranges (AMDR) Percentages of Total Energy
    AMDR_CARBOHYDRATE_PERCENT: tuple[int, int] = (45, 65)
    AMDR_FAT_PERCENT: tuple[int, int] = (20, 35)
    AMDR_PROTEIN_PERCENT: tuple[int, int] = (10, 35)
