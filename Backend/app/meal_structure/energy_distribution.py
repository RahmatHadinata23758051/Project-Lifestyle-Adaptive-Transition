from typing import List, Optional, Dict
from app.meal_structure.constants import MealSlotType, MealPolicy
from app.meal_structure.models import MealSlotDTO


def get_default_energy_shares(slot_types: List[MealSlotType]) -> List[float]:
    main_count = sum(1 for st in slot_types if st == MealSlotType.MAIN_MEAL)
    snack_count = sum(1 for st in slot_types if st == MealSlotType.SNACK)

    if main_count == 2 and snack_count == 0:
        return [0.50, 0.50]
    elif main_count == 2 and snack_count == 1:
        return [0.40, 0.40, 0.20]
    elif main_count == 3 and snack_count == 0:
        return [0.30, 0.35, 0.35]
    elif main_count == 3 and snack_count == 1:
        return [0.25, 0.30, 0.30, 0.15]
    elif main_count == 3 and snack_count == 2:
        return [0.25, 0.25, 0.25, 0.125, 0.125]
    else:
        # Generic proportional weighting: main meal = 2x weight of snack
        weights = [2.0 if st == MealSlotType.MAIN_MEAL else 1.0 for st in slot_types]
        total_w = sum(weights)
        return [round(w / total_w, 4) for w in weights]


def validate_energy_shares(shares: List[float]) -> None:
    if not shares:
        raise ValueError("Energy shares list cannot be empty.")
    
    total = sum(shares)
    if abs(total - 1.0) > MealPolicy.ENERGY_SHARE_TOLERANCE:
        raise ValueError(
            f"Jumlah proporsi alokasi energi ({total:.4f}) harus bernilai 1.0 (toleransi {MealPolicy.ENERGY_SHARE_TOLERANCE})."
        )
    for s in shares:
        if s <= 0.0:
            raise ValueError("Setiap porsi pembagian energi harus bernilai positif > 0.")


def allocate_slot_energy_targets(
    total_target_kcal: float,
    slots: List[MealSlotDTO],
    custom_shares: Optional[List[float]] = None,
    tolerance_ratio: float = 0.15,
) -> List[MealSlotDTO]:
    if total_target_kcal <= 0:
        raise ValueError("Total target energi harian harus bernilai positif.")

    if not slots:
        return []

    shares = custom_shares if custom_shares is not None else get_default_energy_shares([s.slot_type for s in slots])
    
    if len(shares) != len(slots):
        raise ValueError(f"Jumlah alokasi share ({len(shares)}) tidak sesuai dengan jumlah slot ({len(slots)}).")

    validate_energy_shares(shares)

    updated_slots: List[MealSlotDTO] = []
    for slot, share in zip(slots, shares):
        target_kcal = round(total_target_kcal * share, 1)
        min_kcal = round(target_kcal * (1.0 - tolerance_ratio), 1)
        max_kcal = round(target_kcal * (1.0 + tolerance_ratio), 1)

        updated_slots.append(
            MealSlotDTO(
                slot_id=slot.slot_id,
                slot_type=slot.slot_type,
                sequence=slot.sequence,
                preferred_time=slot.preferred_time,
                earliest_time=slot.earliest_time,
                latest_time=slot.latest_time,
                duration_minutes=slot.duration_minutes,
                target_kcal=target_kcal,
                min_kcal=min_kcal,
                max_kcal=max_kcal,
                schedule_source=slot.schedule_source,
                reason_code=slot.reason_code,
                window_type=slot.window_type,
                is_user_fixed=slot.is_user_fixed,
                location_context=slot.location_context,
                prep_context=slot.prep_context,
            )
        )

    return updated_slots
