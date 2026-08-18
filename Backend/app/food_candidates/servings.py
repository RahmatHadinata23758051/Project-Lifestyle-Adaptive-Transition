from typing import List, Optional
from app.food_knowledge.constants import ServingDivisibility
from app.food_knowledge.models import FoodKnowledgeItemDTO
from app.food_knowledge.nutrients import scale_nutrients
from app.food_candidates.constants import FoodPlannerRole, CandidatePolicy
from app.food_candidates.models import FoodCandidateItemDTO


def generate_portion_options_for_food(
    food: FoodKnowledgeItemDTO,
    role: FoodPlannerRole,
    multipliers: Optional[List[float]] = None,
) -> List[FoodCandidateItemDTO]:
    """
    Generates deterministic candidate item portions for a given food.
    Respects discrete vs continuous food serving semantics (H3).
    """
    items: List[FoodCandidateItemDTO] = []

    if food.servings:
        primary_serving = food.servings[0]
        base_grams = primary_serving.grams
        serving_id = primary_serving.id
        serving_name = primary_serving.serving_name

        is_discrete = (
            getattr(primary_serving, "is_discrete", False)
            or getattr(primary_serving, "divisibility", ServingDivisibility.CONTINUOUS) == ServingDivisibility.DISCRETE
        )

        if multipliers is not None:
            chosen_multipliers = multipliers
        else:
            chosen_multipliers = (
                CandidatePolicy.DEFAULT_DISCRETE_MULTIPLIERS
                if is_discrete
                else CandidatePolicy.DEFAULT_CONTINUOUS_MULTIPLIERS
            )

        for mult in chosen_multipliers[:CandidatePolicy.MAX_SERVING_OPTIONS_PER_FOOD]:
            consumed_grams = round(base_grams * mult, 1)
            scaled = scale_nutrients(food.nutrients, consumed_grams=consumed_grams)

            if is_discrete and mult.is_integer():
                display_name = f"{int(mult)} {serving_name}" if mult > 1 else serving_name
            else:
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
        # Default gram-based increments for continuous bulk foods
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
