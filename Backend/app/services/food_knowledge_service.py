from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.food_knowledge import FoodItemRecord, FoodServingRecord
from app.repositories.food_repository import FoodRepository
from app.food_knowledge.models import (
    FoodKnowledgeItemDTO,
    SourceProvenanceDTO,
    NutrientProfileDTO,
    FoodAliasDTO,
    FoodServingDTO,
    FoodAllergenDTO,
    PreparationRequirementsDTO,
)
from app.food_knowledge.constants import (
    SourceType,
    FoodCategory,
    PreparationState,
    FoodEntityType,
    BasisType,
    DataQualityStatus,
    AliasType,
    ServingSourceType,
    ServingConfidence,
    AllergenType,
    AllergenRelationshipType,
    PrepComplexity,
    KitchenEquipment,
)
from app.food_knowledge.nutrients import scale_nutrients, determine_nutrient_completeness
from app.food_knowledge.servings import convert_serving_to_grams


class FoodKnowledgeService:
    """
    Service orchestrating retrieval, DTO conversion, and deterministic serving calculations.
    """

    @classmethod
    def record_to_dto(cls, record: FoodItemRecord) -> FoodKnowledgeItemDTO:
        source_dto = SourceProvenanceDTO(
            id=record.source.id if record.source else None,
            code=record.source.code if record.source else "UNKNOWN",
            name=record.source.name if record.source else "Unknown Source",
            publisher=record.source.publisher if record.source else None,
            edition=record.source.edition if record.source else None,
            publication_year=record.source.publication_year if record.source else None,
            source_type=SourceType(record.source.source_type) if record.source else SourceType.FOOD_COMPOSITION_TABLE,
            reference_url=record.source.reference_url if record.source else None,
            license_status=record.source.license_status if record.source else None,
        )

        nutrients_dto: Optional[NutrientProfileDTO] = None
        if record.nutrients:
            nr = record.nutrients
            completeness = determine_nutrient_completeness(
                nr.energy_kcal, nr.protein_g, nr.fat_g, nr.carbohydrate_g
            )
            nutrients_dto = NutrientProfileDTO(
                energy_kcal=nr.energy_kcal,
                protein_g=nr.protein_g,
                fat_g=nr.fat_g,
                carbohydrate_g=nr.carbohydrate_g,
                fiber_g=nr.fiber_g,
                water_g=nr.water_g,
                optional_micronutrients=nr.optional_micronutrients_json,
                basis_type=BasisType(nr.basis_type),
                reference_amount=nr.reference_amount,
                reference_unit=nr.reference_unit,
                edible_portion_percent=nr.edible_portion_percent,
                data_quality_status=DataQualityStatus(nr.data_quality_status),
                completeness=completeness,
            )

        aliases_dto: List[FoodAliasDTO] = [
            FoodAliasDTO(
                id=a.id,
                alias=a.alias,
                alias_type=AliasType(a.alias_type),
                language=a.language,
                region=a.region,
            )
            for a in (record.aliases or [])
        ]

        servings_dto: List[FoodServingDTO] = [
            FoodServingDTO(
                id=s.id,
                serving_name=s.serving_name,
                grams=s.grams,
                source_type=ServingSourceType(s.source_type),
                confidence=ServingConfidence(s.confidence),
                region=s.region,
                notes=s.notes,
            )
            for s in (record.servings or [])
        ]

        allergens_dto: List[FoodAllergenDTO] = [
            FoodAllergenDTO(
                allergen_type=AllergenType(al.allergen_type),
                relationship_type=AllergenRelationshipType(al.relationship_type),
                notes=al.notes,
            )
            for al in (record.allergens or [])
        ]

        prep_dto: Optional[PreparationRequirementsDTO] = None
        if record.preparation_requirements:
            pr = record.preparation_requirements
            equip = [KitchenEquipment(e) for e in (pr.required_equipment_json or [])]
            prep_dto = PreparationRequirementsDTO(
                requires_cooking=pr.requires_cooking,
                minimum_capability=pr.minimum_capability,
                prep_complexity=PrepComplexity(pr.prep_complexity),
                required_equipment=equip,
            )

        return FoodKnowledgeItemDTO(
            id=record.id,
            canonical_name=record.canonical_name,
            local_name=record.local_name,
            scientific_name=record.scientific_name,
            entity_type=FoodEntityType(record.entity_type),
            food_category=FoodCategory(record.food_category),
            preparation_state=PreparationState(record.preparation_state),
            is_generic_food=record.is_generic_food,
            source=source_dto,
            source_food_code=record.source_food_code,
            nutrients=nutrients_dto,
            aliases=aliases_dto,
            servings=servings_dto,
            allergens=allergens_dto,
            preparation_requirements=prep_dto,
            data_quality_status=DataQualityStatus(record.data_quality_status),
            is_active=record.is_active,
        )

    @classmethod
    def search_foods(
        cls,
        db: Session,
        query: str,
        category: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[FoodKnowledgeItemDTO]:
        records = FoodRepository.search_foods(
            db=db,
            query=query,
            category=category,
            is_active_only=True,
            limit=limit,
            offset=offset,
        )
        return [cls.record_to_dto(r) for r in records]

    @classmethod
    def get_food_detail(cls, db: Session, food_id: str) -> Optional[FoodKnowledgeItemDTO]:
        record = FoodRepository.get_food_by_id(db, food_id=food_id)
        if not record:
            return None
        return cls.record_to_dto(record)

    @classmethod
    def calculate_serving_nutrients(
        cls,
        db: Session,
        food_id: str,
        grams: Optional[float] = None,
        serving_id: Optional[str] = None,
        serving_count: float = 1.0,
    ) -> Dict[str, Any]:
        record = FoodRepository.get_food_by_id(db, food_id=food_id)
        if not record:
            raise ValueError(f"Food item dengan ID '{food_id}' tidak ditemukan.")

        if not record.nutrients:
            raise ValueError(f"Food item '{record.canonical_name}' tidak memiliki data profil nutrisi.")

        target_grams: float
        serving_used_info: Optional[Dict[str, Any]] = None

        if serving_id:
            matched_serving = next((s for s in (record.servings or []) if s.id == serving_id), None)
            if not matched_serving:
                raise ValueError(f"Serving ID '{serving_id}' tidak valid untuk makanan '{record.canonical_name}'.")
            target_grams = convert_serving_to_grams(
                FoodServingDTO(
                    id=matched_serving.id,
                    serving_name=matched_serving.serving_name,
                    grams=matched_serving.grams,
                    source_type=ServingSourceType(matched_serving.source_type),
                    confidence=ServingConfidence(matched_serving.confidence),
                ),
                count=serving_count,
            )
            serving_used_info = {
                "serving_id": matched_serving.id,
                "serving_name": matched_serving.serving_name,
                "serving_count": serving_count,
                "calculated_grams": target_grams,
            }
        elif grams is not None:
            if grams <= 0:
                raise ValueError("Gramatur harus bernilai positif.")
            target_grams = float(grams)
        else:
            raise ValueError("Harap tentukan salah satu dari 'grams' atau 'serving_id'.")

        dto = cls.record_to_dto(record)
        assert dto.nutrients is not None
        scaled = scale_nutrients(nutrients=dto.nutrients, consumed_grams=target_grams)

        return {
            "food_id": record.id,
            "canonical_name": record.canonical_name,
            "consumed_grams": target_grams,
            "serving_used": serving_used_info,
            "scaled_nutrients": {
                "basis_type": scaled.basis_type.value,
                "reference_amount": scaled.reference_amount,
                "reference_unit": scaled.reference_unit,
                "energy_kcal": scaled.energy_kcal,
                "protein_g": scaled.protein_g,
                "fat_g": scaled.fat_g,
                "carbohydrate_g": scaled.carbohydrate_g,
                "fiber_g": scaled.fiber_g,
                "water_g": scaled.water_g,
                "completeness": scaled.completeness.value,
            },
            "source_provenance": {
                "code": dto.source.code,
                "publisher": dto.source.publisher,
                "publication_year": dto.source.publication_year,
            },
            "data_quality_status": dto.data_quality_status.value,
        }
