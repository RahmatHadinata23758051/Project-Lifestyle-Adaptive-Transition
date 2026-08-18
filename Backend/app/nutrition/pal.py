from typing import Optional, List
from dataclasses import dataclass
from app.nutrition.constants import PhysicalActivityCategory


@dataclass
class PALAssessmentResult:
    category: PhysicalActivityCategory
    reason: str
    is_valid: bool = True


class PALClassifier:
    """
    Structured PAL (Physical Activity Level) Classifier.
    Maps lifestyle movement and exercise habits into 2023 DRI PAL categories with full traceability.
    """

    @classmethod
    def classify(
        cls,
        occupation_type: Optional[str] = None,
        available_days_per_week: Optional[int] = None,
        minutes_per_session: Optional[int] = None,
        pal_override: Optional[PhysicalActivityCategory] = None,
    ) -> PALAssessmentResult:
        if pal_override:
            return PALAssessmentResult(
                category=pal_override,
                reason=f"Kategori PAL diset langsung sebagai {pal_override.value}.",
            )

        days = available_days_per_week or 0
        minutes = minutes_per_session or 0
        occ = (occupation_type or "").upper()
        total_weekly_exercise_minutes = days * minutes

        # Active physical worker (e.g. construction, manual laborer, active field worker)
        if occ in ["FIELD_WORKER", "MANUAL_LABOR", "ATHLETE"]:
            if total_weekly_exercise_minutes >= 180:
                return PALAssessmentResult(
                    category=PhysicalActivityCategory.VERY_ACTIVE,
                    reason="Aktivitas kerja fisik tinggi ditambah latihan terstruktur intensif (>=180 menit/minggu).",
                )
            return PALAssessmentResult(
                category=PhysicalActivityCategory.ACTIVE,
                reason="Pekerjaan aktif fisik harian dengan kebutuhan energi dinamis.",
            )

        # Standard Sedentary / Desk worker / Student
        if total_weekly_exercise_minutes >= 240:
            return PALAssessmentResult(
                category=PhysicalActivityCategory.VERY_ACTIVE,
                reason="Aktivitas harian umum dengan volume latihan terstruktur sangat tinggi (>=240 menit/minggu).",
            )
        elif total_weekly_exercise_minutes >= 120 or days >= 4:
            return PALAssessmentResult(
                category=PhysicalActivityCategory.ACTIVE,
                reason=f"Latihan terstruktur rutin ({days} hari/minggu, total {total_weekly_exercise_minutes} menit).",
            )
        elif total_weekly_exercise_minutes >= 45 or days >= 2:
            return PALAssessmentResult(
                category=PhysicalActivityCategory.LOW_ACTIVE,
                reason=f"Aktivitas harian ringan dengan latihan moderat ({days} hari/minggu, {total_weekly_exercise_minutes} menit).",
            )
        else:
            return PALAssessmentResult(
                category=PhysicalActivityCategory.INACTIVE,
                reason="Aktivitas harian dominan menetap/sedentari dengan latihan minimal (<45 menit/minggu).",
            )
