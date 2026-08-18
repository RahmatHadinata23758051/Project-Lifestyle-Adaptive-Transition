from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from app.nutrition.constants import PhysicalActivityCategory, NutritionEligibilityStatus


class NutritionCalculationInput(BaseModel):
    age: Optional[int] = Field(None, ge=1, le=120)
    sex: Optional[str] = None
    height_cm: Optional[float] = Field(None, gt=0, le=300)
    current_weight_kg: Optional[float] = Field(None, gt=0, le=500)
    pal_category: Optional[PhysicalActivityCategory] = None
    occupation_type: Optional[str] = None
    available_days_per_week: Optional[int] = Field(None, ge=0, le=7)
    minutes_per_session: Optional[int] = Field(None, ge=0, le=300)
    starting_surplus_kcal: int = Field(300, ge=0, le=500)

    # Safety Screening Flags
    is_pregnant_or_lactating: bool = False
    has_prescribed_medical_diet: bool = False
    has_eating_disorder_history: bool = False
    has_unexplained_weight_loss: bool = False
    has_major_metabolic_condition: bool = False


class NutritionEligibilityResponse(BaseModel):
    status: NutritionEligibilityStatus
    is_eligible: bool
    reasons: List[str]
    guidance: Optional[str] = None


class NutritionEnergyResponse(BaseModel):
    method: str
    policy_version: str
    pal_category: PhysicalActivityCategory
    pal_reason: str
    maintenance_estimate_kcal: float
    starting_surplus_kcal: int
    target_kcal: float
    rounded_display_kcal: int


class NutritionMacroResponse(BaseModel):
    protein_rda_floor_g: float
    training_target_g: Optional[float] = None
    amdr_percentages: Dict[str, List[int]]
    amdr_gram_ranges: Dict[str, List[int]]


class NutritionCalculationResultResponse(BaseModel):
    user_id: str
    policy_version: str
    eligibility: NutritionEligibilityResponse
    energy: Optional[NutritionEnergyResponse] = None
    macros: Optional[NutritionMacroResponse] = None
    weekly_food_budget: Optional[float] = None
    currency: str = "IDR"
    bmi_context: Optional[float] = None
    explanation: str

    model_config = ConfigDict(from_attributes=True)
