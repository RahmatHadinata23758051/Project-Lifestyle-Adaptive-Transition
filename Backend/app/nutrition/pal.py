from typing import Optional
from dataclasses import dataclass
from app.nutrition.constants import (
    PhysicalActivityCategory,
    PALAssessmentStatus,
    PALResolutionMethod,
)


@dataclass
class PALContext:
    occupation_movement: Optional[str] = None
    transport_activity: Optional[str] = None
    daily_movement: Optional[str] = None
    planned_exercise: Optional[str] = None
    recreational_activity: Optional[str] = None


@dataclass
class PALAssessmentResult:
    category: Optional[PhysicalActivityCategory]
    status: PALAssessmentStatus
    reason: str
    resolution_method: Optional[PALResolutionMethod] = None
    is_valid: bool = True


class PALClassifier:
    """
    Structured PAL (Physical Activity Level) Classifier for Nutrition Intelligence v0.1.
    Adheres strictly to the Zero-Guessing principle: no automatic minute-based heuristic mappings.
    PAL must be explicitly confirmed or resolved through validated assessment.
    """

    @classmethod
    def classify(
        cls,
        confirmed_pal_category: Optional[PhysicalActivityCategory | str] = None,
        pal_override: Optional[PhysicalActivityCategory | str] = None,
        context: Optional[PALContext] = None,
        # Legacy parameters accepted but not used as authoritative heuristics in v0.1 hardening
        occupation_type: Optional[str] = None,
        available_days_per_week: Optional[int] = None,
        minutes_per_session: Optional[int] = None,
    ) -> PALAssessmentResult:
        pal_input = confirmed_pal_category or pal_override

        if pal_input is not None:
            if isinstance(pal_input, PhysicalActivityCategory):
                resolved_cat = pal_input
            elif isinstance(pal_input, str):
                try:
                    resolved_cat = PhysicalActivityCategory(pal_input.upper())
                except ValueError:
                    return PALAssessmentResult(
                        category=None,
                        status=PALAssessmentStatus.INVALID,
                        reason=f"Kategori PAL '{pal_input}' tidak valid.",
                        resolution_method=None,
                        is_valid=False,
                    )
            else:
                return PALAssessmentResult(
                    category=None,
                    status=PALAssessmentStatus.INVALID,
                    reason="Tipe input kategori PAL tidak valid.",
                    resolution_method=None,
                    is_valid=False,
                )

            return PALAssessmentResult(
                category=resolved_cat,
                status=PALAssessmentStatus.RESOLVED,
                reason="Kategori PAL telah dikonfirmasi secara eksplisit melalui assessment pengguna.",
                resolution_method=PALResolutionMethod.USER_CONFIRMED,
                is_valid=True,
            )

        # In v0.1 hardening: without confirmed PAL, status remains UNDETERMINED.
        # Zero-guessing rule: Never default to INACTIVE or derive authoritative PAL from exercise minutes alone.
        return PALAssessmentResult(
            category=None,
            status=PALAssessmentStatus.UNDETERMINED,
            reason="Konteks aktivitas fisik belum mencukupi untuk menentukan kategori PAL secara definitif. Konfirmasi kategori PAL diperlukan.",
            resolution_method=None,
            is_valid=True,
        )
