from app.food_knowledge.constants import FoodCategory
from app.food_candidates.constants import FoodPlannerRole


def map_food_category_to_role(category: FoodCategory) -> FoodPlannerRole:
    """
    Deterministic mapping from standardized food category to planner semantic role.
    """
    if category in (FoodCategory.GRAIN_STAPLE, FoodCategory.TUBER):
        return FoodPlannerRole.STAPLE
    elif category in (
        FoodCategory.POULTRY,
        FoodCategory.MEAT,
        FoodCategory.FISH_SEAFOOD,
        FoodCategory.EGG,
        FoodCategory.SOY_PRODUCT,
        FoodCategory.LEGUME,
    ):
        return FoodPlannerRole.PROTEIN_SOURCE
    elif category == FoodCategory.VEGETABLE:
        return FoodPlannerRole.VEGETABLE
    elif category == FoodCategory.FRUIT:
        return FoodPlannerRole.FRUIT
    elif category in (FoodCategory.FAT_OIL, FoodCategory.SUGAR_SWEETENER, FoodCategory.CONDIMENT):
        return FoodPlannerRole.ENERGY_ADDON
    elif category in (FoodCategory.SNACK, FoodCategory.NUT_SEED):
        return FoodPlannerRole.SNACK_ITEM
    elif category == FoodCategory.BEVERAGE:
        return FoodPlannerRole.BEVERAGE
    else:
        return FoodPlannerRole.OTHER
