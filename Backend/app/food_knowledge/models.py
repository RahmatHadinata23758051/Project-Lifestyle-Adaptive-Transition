from typing import Optional, List, Dict, Any
from dataclasses import dataclass
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
    ServingDivisibility,
    HalalStatus,
    AllergenType,
    AllergenRelationshipType,
    PrepComplexity,
    KitchenEquipment,
    FoodPlannerEligibilityStatus,
)


@dataclass
class SourceProvenanceDTO:
    id: Optional[str]
    code: str
    name: str
    publisher: Optional[str] = None
    edition: Optional[str] = None
    publication_year: Optional[int] = None
    source_type: SourceType = SourceType.FOOD_COMPOSITION_TABLE
    reference_url: Optional[str] = None
    license_status: Optional[str] = None


@dataclass
class NutrientProfileDTO:
    energy_kcal: Optional[float]
    protein_g: Optional[float]
    fat_g: Optional[float]
    carbohydrate_g: Optional[float]
    fiber_g: Optional[float] = None
    water_g: Optional[float] = None
    optional_micronutrients: Optional[Dict[str, Any]] = None
    basis_type: BasisType = BasisType.PER_100_G_EDIBLE
    reference_amount: float = 100.0
    reference_unit: str = "g"
    edible_portion_percent: Optional[float] = None
    data_quality_status: DataQualityStatus = DataQualityStatus.VERIFIED_OFFICIAL
    completeness: NutrientCompleteness = NutrientCompleteness.CORE_COMPLETE


@dataclass
class FoodAliasDTO:
    id: Optional[str]
    alias: str
    alias_type: AliasType
    language: str = "id"
    region: Optional[str] = None


@dataclass
class FoodServingDTO:
    id: Optional[str]
    serving_name: str
    grams: float
    source_type: ServingSourceType = ServingSourceType.MEASURED_CURATED
    confidence: ServingConfidence = ServingConfidence.HIGH
    region: Optional[str] = None
    notes: Optional[str] = None
    divisibility: ServingDivisibility = ServingDivisibility.CONTINUOUS
    is_discrete: bool = False


@dataclass
class FoodAllergenDTO:
    allergen_type: AllergenType
    relationship_type: AllergenRelationshipType = AllergenRelationshipType.CONTAINS
    notes: Optional[str] = None


@dataclass
class PreparationRequirementsDTO:
    requires_cooking: bool
    minimum_capability: str
    prep_complexity: PrepComplexity
    required_equipment: List[KitchenEquipment]


@dataclass
class FoodKnowledgeItemDTO:
    id: str
    canonical_name: str
    local_name: Optional[str]
    scientific_name: Optional[str]
    entity_type: FoodEntityType
    food_category: FoodCategory
    preparation_state: PreparationState
    is_generic_food: bool
    source: SourceProvenanceDTO
    source_food_code: Optional[str]
    nutrients: Optional[NutrientProfileDTO]
    aliases: List[FoodAliasDTO]
    servings: List[FoodServingDTO]
    allergens: List[FoodAllergenDTO]
    preparation_requirements: Optional[PreparationRequirementsDTO]
    data_quality_status: DataQualityStatus
    halal_status: HalalStatus = HalalStatus.UNKNOWN
    is_active: bool = True
