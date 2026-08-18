from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.models.food_knowledge import (
    FoodDataSourceRecord,
    FoodItemRecord,
    FoodNutrientsRecord,
    FoodAliasRecord,
    FoodServingRecord,
    FoodItemAllergenRecord,
    FoodPreparationRequirementRecord,
)
from app.food_knowledge.normalization import normalize_food_search_query
from app.food_knowledge.constants import (
    DataQualityStatus,
    BasisType,
    FoodCategory,
    PreparationState,
    FoodEntityType,
)


@dataclass
class ImportResult:
    source_code: str
    total_parsed: int = 0
    valid_count: int = 0
    rejected_count: int = 0
    duplicate_count: int = 0
    persisted_count: int = 0
    is_dry_run: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class FoodImportPipeline:
    """
    Deterministic import pipeline for food composition and reference data.
    Supports Dry-Run mode, strict validation, and idempotent persistence.
    """

    @classmethod
    def import_dataset(
        cls,
        db: Session,
        source_record: FoodDataSourceRecord,
        raw_items: List[Dict[str, Any]],
        dry_run: bool = True,
    ) -> ImportResult:
        result = ImportResult(source_code=source_record.code, total_parsed=len(raw_items), is_dry_run=dry_run)

        existing_codes = {
            item.source_food_code
            for item in db.query(FoodItemRecord.source_food_code)
            .filter(FoodItemRecord.source_id == source_record.id)
            .all()
            if item.source_food_code
        }

        for idx, raw in enumerate(raw_items, 1):
            canonical_name = raw.get("canonical_name", "").strip()
            source_food_code = raw.get("source_food_code", "").strip() if raw.get("source_food_code") else None

            # Validation 1: Required Identity
            if not canonical_name:
                result.rejected_count += 1
                result.errors.append(f"Row {idx}: Nama makanan (canonical_name) wajib diisi.")
                continue

            if not source_food_code:
                result.rejected_count += 1
                result.errors.append(f"Row {idx} ('{canonical_name}'): source_food_code wajib diisi.")
                continue

            # Validation 2: Duplicate check
            if source_food_code in existing_codes:
                result.duplicate_count += 1
                result.warnings.append(f"Row {idx}: Food code '{source_food_code}' sudah terdaftar. Melewati duplikasi (idempotent).")
                continue

            # Validation 3: Nutrient Values Plausibility
            nutrients_raw = raw.get("nutrients", {})
            energy = nutrients_raw.get("energy_kcal")
            protein = nutrients_raw.get("protein_g")
            fat = nutrients_raw.get("fat_g")
            carb = nutrients_raw.get("carbohydrate_g")
            edible_portion = nutrients_raw.get("edible_portion_percent")

            if energy is not None and energy < 0:
                result.rejected_count += 1
                result.errors.append(f"Row {idx} ('{canonical_name}'): Nilai energi tidak boleh negatif ({energy}).")
                continue

            if protein is not None and protein < 0:
                result.rejected_count += 1
                result.errors.append(f"Row {idx} ('{canonical_name}'): Nilai protein tidak boleh negatif ({protein}).")
                continue

            if fat is not None and fat < 0:
                result.rejected_count += 1
                result.errors.append(f"Row {idx} ('{canonical_name}'): Nilai lemak tidak boleh negatif ({fat}).")
                continue

            if carb is not None and carb < 0:
                result.rejected_count += 1
                result.errors.append(f"Row {idx} ('{canonical_name}'): Nilai karbohidrat tidak boleh negatif ({carb}).")
                continue

            if edible_portion is not None and not (0.0 <= edible_portion <= 100.0):
                result.rejected_count += 1
                result.errors.append(f"Row {idx} ('{canonical_name}'): edible_portion_percent harus antara 0 dan 100.")
                continue

            result.valid_count += 1

            if not dry_run:
                normalized_name = normalize_food_search_query(canonical_name)
                food_category = raw.get("food_category", FoodCategory.OTHER.value).upper()
                prep_state = raw.get("preparation_state", PreparationState.RAW.value).upper()
                quality_status = raw.get("data_quality_status", DataQualityStatus.VERIFIED_OFFICIAL.value).upper()

                food_rec = FoodItemRecord(
                    canonical_name=canonical_name,
                    normalized_name=normalized_name,
                    local_name=raw.get("local_name"),
                    scientific_name=raw.get("scientific_name"),
                    entity_type=raw.get("entity_type", FoodEntityType.GENERIC_FOOD.value).upper(),
                    food_category=food_category,
                    preparation_state=prep_state,
                    is_generic_food=raw.get("is_generic_food", True),
                    source_id=source_record.id,
                    source_food_code=source_food_code,
                    data_quality_status=quality_status,
                    is_active=raw.get("is_active", True),
                )
                db.add(food_rec)
                db.flush()

                # Add nutrients
                basis_type = nutrients_raw.get("basis_type", BasisType.PER_100_G_EDIBLE.value).upper()
                nutrient_rec = FoodNutrientsRecord(
                    food_item_id=food_rec.id,
                    energy_kcal=energy,
                    protein_g=protein,
                    fat_g=fat,
                    carbohydrate_g=carb,
                    fiber_g=nutrients_raw.get("fiber_g"),
                    water_g=nutrients_raw.get("water_g"),
                    optional_micronutrients_json=nutrients_raw.get("optional_micronutrients"),
                    basis_type=basis_type,
                    reference_amount=nutrients_raw.get("reference_amount", 100.0),
                    reference_unit=nutrients_raw.get("reference_unit", "g"),
                    edible_portion_percent=edible_portion,
                    data_quality_status=quality_status,
                )
                db.add(nutrient_rec)

                # Add aliases
                for alias_item in raw.get("aliases", []):
                    alias_str = alias_item.get("alias", "").strip()
                    if alias_str:
                        db.add(
                            FoodAliasRecord(
                                food_item_id=food_rec.id,
                                alias=alias_str,
                                normalized_alias=normalize_food_search_query(alias_str),
                                language=alias_item.get("language", "id"),
                                region=alias_item.get("region"),
                                alias_type=alias_item.get("alias_type", "COMMON_NAME").upper(),
                            )
                        )

                # Add servings
                for s in raw.get("servings", []):
                    if s.get("serving_name") and s.get("grams", 0) > 0:
                        db.add(
                            FoodServingRecord(
                                food_item_id=food_rec.id,
                                serving_name=s.get("serving_name"),
                                grams=float(s.get("grams")),
                                source_type=s.get("source_type", "MEASURED_CURATED").upper(),
                                confidence=s.get("confidence", "HIGH").upper(),
                                region=s.get("region"),
                                notes=s.get("notes"),
                            )
                        )

                # Add allergens
                for al in raw.get("allergens", []):
                    if al.get("allergen_type"):
                        db.add(
                            FoodItemAllergenRecord(
                                food_item_id=food_rec.id,
                                allergen_type=al.get("allergen_type").upper(),
                                relationship_type=al.get("relationship_type", "CONTAINS").upper(),
                                notes=al.get("notes"),
                            )
                        )

                # Add preparation requirements
                prep_raw = raw.get("preparation_requirements")
                if prep_raw:
                    db.add(
                        FoodPreparationRequirementRecord(
                            food_item_id=food_rec.id,
                            requires_cooking=prep_raw.get("requires_cooking", False),
                            minimum_capability=prep_raw.get("minimum_capability", "CAN_COOK"),
                            prep_complexity=prep_raw.get("prep_complexity", "NONE").upper(),
                            required_equipment_json=prep_raw.get("required_equipment", []),
                        )
                    )

                existing_codes.add(source_food_code)
                result.persisted_count += 1

        if not dry_run:
            db.commit()

        return result
