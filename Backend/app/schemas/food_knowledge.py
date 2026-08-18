from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.food_knowledge.constants import (
    SourceType,
    FoodCategory,
    PreparationState,
    FoodEntityType,
    BasisType,
    DataQualityStatus,
    NutrientCompleteness,
    AliasType,
    ServingSourceType,
    ServingConfidence,
    AllergenType,
    AllergenRelationshipType,
    PrepComplexity,
    KitchenEquipment,
)


class SourceProvenanceResponse(BaseModel):
    id: Optional[str] = None
    code: str
    name: str
    publisher: Optional[str] = None
    edition: Optional[str] = None
    publication_year: Optional[int] = None
    source_type: SourceType = SourceType.FOOD_COMPOSITION_TABLE
    reference_url: Optional[str] = None
    license_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NutrientProfileResponse(BaseModel):
    energy_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    carbohydrate_g: Optional[float] = None
    fiber_g: Optional[float] = None
    water_g: Optional[float] = None
    optional_micronutrients: Optional[Dict[str, Any]] = None
    basis_type: BasisType = BasisType.PER_100_G_EDIBLE
    reference_amount: float = 100.0
    reference_unit: str = "g"
    edible_portion_percent: Optional[float] = None
    data_quality_status: DataQualityStatus = DataQualityStatus.VERIFIED_OFFICIAL
    completeness: NutrientCompleteness = NutrientCompleteness.CORE_COMPLETE

    model_config = ConfigDict(from_attributes=True)


class FoodAliasResponse(BaseModel):
    id: Optional[str] = None
    alias: str
    alias_type: AliasType
    language: str = "id"
    region: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FoodServingResponse(BaseModel):
    id: Optional[str] = None
    serving_name: str
    grams: float
    source_type: ServingSourceType = ServingSourceType.MEASURED_CURATED
    confidence: ServingConfidence = ServingConfidence.HIGH
    region: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FoodAllergenResponse(BaseModel):
    allergen_type: AllergenType
    relationship_type: AllergenRelationshipType = AllergenRelationshipType.CONTAINS
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PreparationRequirementsResponse(BaseModel):
    requires_cooking: bool
    minimum_capability: str
    prep_complexity: PrepComplexity
    required_equipment: List[KitchenEquipment]

    model_config = ConfigDict(from_attributes=True)


class FoodItemResponse(BaseModel):
    id: str
    canonical_name: str
    local_name: Optional[str] = None
    scientific_name: Optional[str] = None
    entity_type: FoodEntityType
    food_category: FoodCategory
    preparation_state: PreparationState
    is_generic_food: bool
    source: SourceProvenanceResponse
    source_food_code: Optional[str] = None
    nutrients: Optional[NutrientProfileResponse] = None
    aliases: List[FoodAliasResponse] = []
    servings: List[FoodServingResponse] = []
    allergens: List[FoodAllergenResponse] = []
    preparation_requirements: Optional[PreparationRequirementsResponse] = None
    data_quality_status: DataQualityStatus
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class FoodSearchResponse(BaseModel):
    total_matches: int
    query: str
    results: List[FoodItemResponse]

    model_config = ConfigDict(from_attributes=True)


class ServingCalculationInput(BaseModel):
    grams: Optional[float] = Field(None, gt=0, description="Amount in grams to scale nutrients to.")
    serving_id: Optional[str] = Field(None, description="Optional UUID of a predefined serving unit.")
    serving_count: float = Field(1.0, gt=0, description="Multiplier for the chosen serving unit.")


class ServingCalculationResponse(BaseModel):
    food_id: str
    canonical_name: str
    consumed_grams: float
    serving_used: Optional[Dict[str, Any]] = None
    scaled_nutrients: Dict[str, Any]
    source_provenance: Dict[str, Any]
    data_quality_status: str

    model_config = ConfigDict(from_attributes=True)
