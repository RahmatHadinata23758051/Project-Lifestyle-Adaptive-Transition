from typing import Optional
from app.food_knowledge.models import FoodServingDTO


def convert_serving_to_grams(
    serving: FoodServingDTO,
    count: float = 1.0,
) -> float:
    if count <= 0:
        raise ValueError("Jumlah porsi (serving count) harus lebih besar dari 0.")

    if serving.grams <= 0:
        raise ValueError("Gramatur per porsi harus lebih besar dari 0.")

    return round(serving.grams * count, 2)
