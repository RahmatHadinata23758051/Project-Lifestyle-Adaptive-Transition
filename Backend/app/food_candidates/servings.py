from typing import List
from app.food_knowledge.models import FoodKnowledgeItemDTO
from app.food_knowledge.nutrients import scale_nutrients
from app.food_candidates.constants import FoodPlannerRole, CandidatePolicy
from app.food_candidates.models import FoodCandidateItemDTO
from app.food_candidates.roles import map_food_category_to_role


def generate_portion_options_for_food(
    food: FoodKnowledgeItemDTO,
    role: FoodPlannerRole,
    multipliers: List[float] = CandidatePolicy.DEFAULT_SERVING_MULTIPLIERS,
) -> List[FoodCandidateItemDTO]:
    """
    Generates deterministic candidate item portions for a given food.
    """
    items: List[FoodCandidateItemDTO] = []

    if food.servings:
        primary_serving = food.servings[0]
        base_grams = primary_serving.grams
        serving_id = primary_serving.id
        serving_name = primary_serving.serving_name

        for mult in multipliers[:CandidatePolicy.MAX_SERVING_OPTIONS_PER_FOOD]:
            consumed_grams = round(base_grams * mult, 1)
            scaled = scale_nutrients(food.nutrients, consumed_grams=consumed_grams)

            display_name = f"{mult} {serving_name}" if mult != 1.0 else serving_name
            items.append(
                FoodCandidateItemDTO(
                    food_item_id=food.id,
                    canonical_name=food.canonical_name,
                    role=role,
                    serving_id=serving_id,
                    serving_name=display_name,
                    grams=consumed_grams,
                    energy_kcal=scaled.energy_kcal or 0.0,
                    protein_g=scaled.protein_g,
                    fat_g=scaled.fat_g,
                    carbohydrate_g=scaled.carbohydrate_g,
                )
            )
    else:
        # Default gram-based increments
        gram_options = [50.0, 100.0, 150.0, 200.0][:CandidatePolicy.MAX_SERVING_OPTIONS_PER_FOOD]
        for g in gram_options:
            scaled = scale_nutrients(food.nutrients, consumed_grams=g)
            items.append(
                FoodCandidateItemDTO(
                    food_item_id=food.id,
                    canonical_name=food.canonical_name,
                    role=role,
                    serving_id=None,
                    serving_name=f"{g:.0f} g",
                    grams=g,
                    energy_kcal=scaled.energy_kcal or 0.0,
                    protein_g=scaled.protein_g,
                    fat_g=scaled.fat_g,
                    carbohydrate_g=scaled.carbohydrate_g,
                )
            )

    return items
