from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from app.nutrition.constants import (
    PhysicalActivityCategory,
    NutritionEligibilityStatus,
    CalculationSource,
    PALResolutionMethod,
    NutritionPolicy,
)


class NutritionCalculationInput(BaseModel):
    age: Optional[int] = Field(None, ge=1, le=120)
    sex: Optional[str] = None
    height_cm: Optional[float] = Field(None, gt=0, le=300)
    current_weight_kg: Optional[float] = Field(None, gt=0, le=500)
    pal_category: Optional[PhysicalActivityCategory | str] = None
    confirmed_pal_category: Optional[PhysicalActivityCategory | str] = None
    starting_surplus_kcal: int = Field(300, ge=0, le=2000)
    weekly_food_budget: Optional[int] = Field(None, ge=0)

    # Optional Context (Non-authoritative in v0.1 hardening)
    occupation_type: Optional[str] = None
    available_days_per_week: Optional[int] = Field(None, ge=0, le=7)
    minutes_per_session: Optional[int] = Field(None, ge=0, le=300)

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
    requested_surplus_kcal: int
    applied_surplus_kcal: int
    surplus_was_adjusted: bool
    target_kcal: float
    rounded_display_kcal: int


class NutritionMacroResponse(BaseModel):
    protein_rda_reference_g: float
    training_target_g: Optional[float] = None
    amdr_percentages: Dict[str, List[int]]
    amdr_gram_ranges: Dict[str, List[int]]


class NutritionCalculationResultResponse(BaseModel):
    user_id: str
    calculation_source: CalculationSource = CalculationSource.LIVE_PREVIEW
    energy_method: str = NutritionPolicy.EER_METHOD
    pal_resolution_method: Optional[PALResolutionMethod] = None
    policy_version: str = NutritionPolicy.VERSION
    assessment_snapshot_id: Optional[str] = None
    calculation_ready: bool
    plan_ready: bool
    missing_for_calculation: List[str] = []
    missing_for_plan: List[str] = []
    eligibility: NutritionEligibilityResponse
    energy: Optional[NutritionEnergyResponse] = None
    macros: Optional[NutritionMacroResponse] = None
    weekly_food_budget: Optional[int] = None
    currency: str = "IDR"
    bmi_context: Optional[float] = None
    explanation: str

    model_config = ConfigDict(from_attributes=True)
