from typing import List, Optional
from dataclasses import dataclass
from app.nutrition.constants import NutritionEligibilityStatus, NutritionPolicy


@dataclass
class EligibilityResult:
    status: NutritionEligibilityStatus
    reasons: List[str]
    guidance: Optional[str] = None
    is_eligible: bool = False


class NutritionEligibilityEvaluator:
    """
    Conservative safety evaluator for automated nutrition calculation.
    Enforces ethical boundaries and flags conditions outside lifestyle scope without diagnosing.
    """

    @classmethod
    def evaluate(
        cls,
        age: Optional[int],
        is_pregnant_or_lactating: bool = False,
        has_prescribed_medical_diet: bool = False,
        has_eating_disorder_history: bool = False,
        has_unexplained_weight_loss: bool = False,
        has_major_metabolic_condition: bool = False,
    ) -> EligibilityResult:
        reasons: List[str] = []

        if age is None:
            return EligibilityResult(
                status=NutritionEligibilityStatus.NEEDS_MORE_DATA,
                reasons=["Data umur diperlukan untuk menghitung kebutuhan energi."],
                guidance="Harap lengkapi tanggal lahir di profil.",
                is_eligible=False,
            )

        if age < NutritionPolicy.MINIMUM_SUPPORTED_AGE:
            return EligibilityResult(
                status=NutritionEligibilityStatus.OUT_OF_SCOPE,
                reasons=[f"Usia {age} tahun di bawah batas minimal ({NutritionPolicy.MINIMUM_SUPPORTED_AGE}+ tahun) untuk persamaan 2023 DRI EER dewasa."],
                guidance="Kebutuhan nutrisi remaja/pediatri memerlukan formula pertumbuhan khusus yang berada di luar lingkup modul dewasa v0.1.",
                is_eligible=False,
            )

        if is_pregnant_or_lactating:
            reasons.append("Kehamilan atau masa laktasi memerlukan evaluasi nutrisi klinis khusus.")

        if has_prescribed_medical_diet:
            reasons.append("Diet klinis medis memerlukan pengawasan langsung dari dokter atau dietisien profesional.")

        if has_eating_disorder_history:
            reasons.append("Riwayat gangguan makan memerlukan pendampingan spesialis kesehatan.")

        if has_major_metabolic_condition:
            reasons.append("Kondisi metabolik/penyakit penyerta memerlukan penyesuaian nutrisi klinis.")

        if len(reasons) > 0:
            return EligibilityResult(
                status=NutritionEligibilityStatus.OUT_OF_SCOPE,
                reasons=reasons,
                guidance="Chronos merekomendasikan berkonsultasi dengan dokter atau ahli gizi teregistrasi untuk panduan nutrisi yang aman.",
                is_eligible=False,
            )

        if has_unexplained_weight_loss:
            return EligibilityResult(
                status=NutritionEligibilityStatus.PROFESSIONAL_GUIDANCE_RECOMMENDED,
                reasons=["Penurunan berat badan mendadak tanpa penyebab jelas."],
                guidance="Disarankan melakukan pemeriksaan medis untuk memastikan tidak ada kondisi kesehatan mendasar sebelum memulai program surplus energi.",
                is_eligible=False,
            )

        return EligibilityResult(
            status=NutritionEligibilityStatus.ELIGIBLE,
            reasons=[],
            guidance=None,
            is_eligible=True,
        )
