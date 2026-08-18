from typing import List, Optional, Dict
from app.nutrition_adherence.constants import (
    MealCheckinStatus,
    ActualFoodSourceType,
    ActualIntakeCertainty,
)
from app.nutrition_adherence.models import ActualFoodItemDTO, MealCheckinDTO
from app.daily_nutrition_plan.models import DailyMealEntryDTO


def materialize_as_planned_items(
    planned_entry: DailyMealEntryDTO,
) -> List[ActualFoodItemDTO]:
    """
    Materializes actual food items from the planned meal snapshot when user confirms ATE_AS_PLANNED.
    """
    items: List[ActualFoodItemDTO] = []
    for food in planned_entry.foods:
        items.append(
            ActualFoodItemDTO(
                food_item_id=food.food_item_id,
                display_name=food.canonical_name,
                serving_name=food.serving_name,
                grams=food.grams,
                quantity=1.0,
                energy_kcal=food.energy_kcal,
                protein_g=food.protein_g,
                fat_g=food.fat_g,
                carbohydrate_g=food.carbohydrate_g,
                source_type=ActualFoodSourceType.PLANNED_ITEM,
                certainty=ActualIntakeCertainty.EXACT,
            )
        )
    return items
