from typing import List, Tuple
from app.food_knowledge.constants import AllergenType, AllergenRelationshipType
from app.food_knowledge.models import FoodAllergenDTO


def check_allergen_conflict(
    user_allergies: List[AllergenType | str],
    food_allergens: List[FoodAllergenDTO],
) -> Tuple[bool, List[str]]:
    """
    Pure deterministic allergen safety filter.
    Returns (has_conflict, reasons).
    - If user has allergy X and food CONTAINS X -> (True, ["Mengandung alergen terlarang: X"]) (Hard block).
    - If food has allergen relationship UNKNOWN -> (True, ["Status alergen tidak pasti/belum diverifikasi."]) (Unknown != Safe).
    """
    if not user_allergies:
        return False, []

    normalized_user_allergies = set()
    for a in user_allergies:
        if isinstance(a, AllergenType):
            normalized_user_allergies.add(a.value)
        elif isinstance(a, str):
            try:
                normalized_user_allergies.add(AllergenType(a.upper()).value)
            except ValueError:
                normalized_user_allergies.add(a.upper())

    reasons: List[str] = []
    has_conflict = False

    for fa in food_allergens:
        allergen_val = fa.allergen_type.value if isinstance(fa.allergen_type, AllergenType) else str(fa.allergen_type)

        if fa.relationship_type == AllergenRelationshipType.CONTAINS:
            if allergen_val in normalized_user_allergies:
                has_conflict = True
                reasons.append(f"Makanan mengandung alergen '{allergen_val}' yang dihindari pengguna.")
        elif fa.relationship_type == AllergenRelationshipType.UNKNOWN:
            if allergen_val in normalized_user_allergies:
                has_conflict = True
                reasons.append(f"Status keberadaan alergen '{allergen_val}' pada makanan belum dapat dipastikan (UNKNOWN).")

    return has_conflict, reasons
