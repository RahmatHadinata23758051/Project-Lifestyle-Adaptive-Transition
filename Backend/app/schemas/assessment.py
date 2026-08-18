from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.models.identity import GoalDomain, GoalPriority, GoalStatus
from app.assessment.constants import DomainCompleteness, FieldClassification


class AssessmentGoalInput(BaseModel):
    domain: GoalDomain
    priority: GoalPriority = GoalPriority.PRIMARY
    status: GoalStatus = GoalStatus.ACTIVE
    target_description: Optional[str] = None


class AssessmentGoalsUpdate(BaseModel):
    goals: List[AssessmentGoalInput] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_single_primary_goal(self) -> "AssessmentGoalsUpdate":
        primary_count = sum(1 for g in self.goals if g.priority == GoalPriority.PRIMARY and g.status == GoalStatus.ACTIVE)
        if primary_count > 1:
            raise ValueError("Maksimal hanya boleh ada 1 active goal dengan priority PRIMARY untuk mencegah konflik adaptasi lintas domain.")
        if primary_count == 0:
            raise ValueError("Minimal harus ada 1 active goal dengan priority PRIMARY sebagai acuan utama.")
        return self


class DomainStatusSummary(BaseModel):
    status: DomainCompleteness
    completion_percentage: float
    missing_required: List[str]
    total_required: int
    filled_required: int


class AssessmentStatusResponse(BaseModel):
    overall_status: DomainCompleteness
    is_plan_ready: bool
    missing_required_fields: List[str]
    domains: Dict[str, DomainStatusSummary]


class AssessmentQuestion(BaseModel):
    key: str
    domain: str
    label: str
    classification: FieldClassification
    field_type: str
    options: Optional[List[str]] = None
    description: Optional[str] = None
    is_profile_field: bool = False


class AssessmentQuestionsResponse(BaseModel):
    active_goals: List[str]
    relevant_domains: List[str]
    missing_required_fields: List[str]
    missing_optional_fields: List[str]
    questions: List[AssessmentQuestion]


class AssessmentAnswerPayload(BaseModel):
    answers: Dict[str, Any] = Field(..., description="Map of question key to answer value")


class AssessmentSnapshotResponse(BaseModel):
    snapshot_id: str
    user_id: str
    created_at: str
    snapshot_data: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
