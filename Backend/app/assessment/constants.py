from enum import Enum


class AssessmentDomain(str, Enum):
    CORE_PROFILE = "CORE_PROFILE"
    SLEEP_ROUTINE = "SLEEP_ROUTINE"
    NUTRITION_WEIGHT_GAIN = "NUTRITION_WEIGHT_GAIN"
    PHYSICAL_ACTIVITY = "PHYSICAL_ACTIVITY"


class FieldClassification(str, Enum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    DERIVED = "DERIVED"
    HISTORICAL = "HISTORICAL"


class DomainCompleteness(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"


class CookingCapability(str, Enum):
    CANNOT_COOK = "CANNOT_COOK"
    LIMITED = "LIMITED"
    FULL = "FULL"


class ActivityExperienceLevel(str, Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class EquipmentItem(str, Enum):
    NONE = "NONE"
    DUMBBELL = "DUMBBELL"
    RESISTANCE_BAND = "RESISTANCE_BAND"
    PULL_UP_BAR = "PULL_UP_BAR"
    YOGA_MAT = "YOGA_MAT"
    BENCH = "BENCH"
    GYM_MEMBERSHIP = "GYM_MEMBERSHIP"
    OTHER = "OTHER"
