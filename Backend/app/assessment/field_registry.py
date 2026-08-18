from datetime import date, datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from app.assessment.constants import AssessmentDomain, FieldClassification


@dataclass
class FieldDefinition:
    domain: AssessmentDomain
    key: str
    label: str
    classification: FieldClassification
    field_type: str  # text, number, select, multiselect, time, date, boolean
    options: Optional[List[str]] = None
    description: Optional[str] = None
    is_profile_field: bool = False


# Pure helper for derived fields
def calculate_age_from_birthdate(birth_date_str: Optional[str]) -> Optional[int]:
    if not birth_date_str:
        return None
    try:
        born = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except (ValueError, TypeError):
        return None


# Global registry of all assessment fields across domains
FIELD_REGISTRY: Dict[str, FieldDefinition] = {
    # Core Profile Fields (Reusable across domains)
    "profile.birth_date": FieldDefinition(
        domain=AssessmentDomain.CORE_PROFILE,
        key="profile.birth_date",
        label="Tanggal Lahir",
        classification=FieldClassification.REQUIRED,
        field_type="date",
        description="Format YYYY-MM-DD",
        is_profile_field=True,
    ),
    "profile.age": FieldDefinition(
        domain=AssessmentDomain.CORE_PROFILE,
        key="profile.age",
        label="Usia",
        classification=FieldClassification.DERIVED,
        field_type="number",
        description="Dihitung otomatis dari tanggal lahir",
        is_profile_field=True,
    ),
    "profile.sex": FieldDefinition(
        domain=AssessmentDomain.CORE_PROFILE,
        key="profile.sex",
        label="Jenis Kelamin",
        classification=FieldClassification.REQUIRED,
        field_type="select",
        options=["MALE", "FEMALE"],
        is_profile_field=True,
    ),
    "profile.height_cm": FieldDefinition(
        domain=AssessmentDomain.CORE_PROFILE,
        key="profile.height_cm",
        label="Tinggi Badan (cm)",
        classification=FieldClassification.REQUIRED,
        field_type="number",
        is_profile_field=True,
    ),
    "profile.timezone": FieldDefinition(
        domain=AssessmentDomain.CORE_PROFILE,
        key="profile.timezone",
        label="Zona Waktu",
        classification=FieldClassification.REQUIRED,
        field_type="text",
        is_profile_field=True,
    ),
    "profile.occupation_type": FieldDefinition(
        domain=AssessmentDomain.CORE_PROFILE,
        key="profile.occupation_type",
        label="Jenis Pekerjaan / Aktivitas Utama",
        classification=FieldClassification.OPTIONAL,
        field_type="select",
        options=["STUDENT", "WORKER", "FREELANCE", "OTHER"],
        is_profile_field=True,
    ),

    # Sleep Routine Domain
    "sleep.current_bedtime": FieldDefinition(
        domain=AssessmentDomain.SLEEP_ROUTINE,
        key="sleep.current_bedtime",
        label="Jam Tidur Saat Ini",
        classification=FieldClassification.REQUIRED,
        field_type="time",
        description="Format 24 jam HH:MM",
    ),
    "sleep.current_wake_time": FieldDefinition(
        domain=AssessmentDomain.SLEEP_ROUTINE,
        key="sleep.current_wake_time",
        label="Jam Bangun Saat Ini",
        classification=FieldClassification.REQUIRED,
        field_type="time",
        description="Format 24 jam HH:MM",
    ),
    "sleep.target_wake_time": FieldDefinition(
        domain=AssessmentDomain.SLEEP_ROUTINE,
        key="sleep.target_wake_time",
        label="Target Jam Bangun",
        classification=FieldClassification.REQUIRED,
        field_type="time",
        description="Format 24 jam HH:MM",
    ),
    "sleep.target_bedtime": FieldDefinition(
        domain=AssessmentDomain.SLEEP_ROUTINE,
        key="sleep.target_bedtime",
        label="Target Jam Tidur",
        classification=FieldClassification.OPTIONAL,
        field_type="time",
    ),
    "sleep.requested_transition_duration": FieldDefinition(
        domain=AssessmentDomain.SLEEP_ROUTINE,
        key="sleep.requested_transition_duration",
        label="Target Durasi Transisi (Hari)",
        classification=FieldClassification.REQUIRED,
        field_type="number",
        description="Jumlah hari adaptasi (misal 14, 21, 30)",
    ),
    "sleep.sleep_consistency": FieldDefinition(
        domain=AssessmentDomain.SLEEP_ROUTINE,
        key="sleep.sleep_consistency",
        label="Konsistensi Jam Tidur",
        classification=FieldClassification.OPTIONAL,
        field_type="select",
        options=["VERY_IRREGULAR", "SOMEWHAT_REGULAR", "REGULAR"],
    ),
    "sleep.caffeine_pattern": FieldDefinition(
        domain=AssessmentDomain.SLEEP_ROUTINE,
        key="sleep.caffeine_pattern",
        label="Kebiasaan Konsumsi Kafein",
        classification=FieldClassification.OPTIONAL,
        field_type="select",
        options=["NONE", "MORNING_ONLY", "AFTERNOON", "EVENING_NIGHT"],
    ),
    "sleep.screen_habit": FieldDefinition(
        domain=AssessmentDomain.SLEEP_ROUTINE,
        key="sleep.screen_habit",
        label="Penggunaan Layar Sebelum Tidur",
        classification=FieldClassification.OPTIONAL,
        field_type="boolean",
    ),

    # Nutrition / Weight Gain Domain
    "nutrition.current_weight_kg": FieldDefinition(
        domain=AssessmentDomain.NUTRITION_WEIGHT_GAIN,
        key="nutrition.current_weight_kg",
        label="Berat Badan Saat Ini (kg)",
        classification=FieldClassification.REQUIRED,
        field_type="number",
    ),
    "nutrition.meals_per_day": FieldDefinition(
        domain=AssessmentDomain.NUTRITION_WEIGHT_GAIN,
        key="nutrition.meals_per_day",
        label="Frekuensi Makan Harian Saat Ini",
        classification=FieldClassification.REQUIRED,
        field_type="number",
        description="Jumlah kali makan besar dalam sehari",
    ),
    "nutrition.weekly_food_budget": FieldDefinition(
        domain=AssessmentDomain.NUTRITION_WEIGHT_GAIN,
        key="nutrition.weekly_food_budget",
        label="Anggaran Makan Mingguan (IDR)",
        classification=FieldClassification.REQUIRED,
        field_type="number",
    ),
    "nutrition.cooking_capability": FieldDefinition(
        domain=AssessmentDomain.NUTRITION_WEIGHT_GAIN,
        key="nutrition.cooking_capability",
        label="Akses & Kemampuan Memasak",
        classification=FieldClassification.REQUIRED,
        field_type="select",
        options=["CANNOT_COOK", "LIMITED", "FULL"],
    ),
    "nutrition.allergies": FieldDefinition(
        domain=AssessmentDomain.NUTRITION_WEIGHT_GAIN,
        key="nutrition.allergies",
        label="Alergi Makanan",
        classification=FieldClassification.REQUIRED,
        field_type="text",
        description="Tulis 'NONE' jika tidak memiliki alergi",
    ),
    "nutrition.food_restrictions": FieldDefinition(
        domain=AssessmentDomain.NUTRITION_WEIGHT_GAIN,
        key="nutrition.food_restrictions",
        label="Pantangan Makanan / Preferensi Diet",
        classification=FieldClassification.OPTIONAL,
        field_type="text",
    ),
    "nutrition.food_preferences": FieldDefinition(
        domain=AssessmentDomain.NUTRITION_WEIGHT_GAIN,
        key="nutrition.food_preferences",
        label="Makanan Favorit / Preferensi Makanan",
        classification=FieldClassification.OPTIONAL,
        field_type="text",
    ),
    "nutrition.target_weight_kg": FieldDefinition(
        domain=AssessmentDomain.NUTRITION_WEIGHT_GAIN,
        key="nutrition.target_weight_kg",
        label="Target Berat Badan (kg)",
        classification=FieldClassification.OPTIONAL,
        field_type="number",
    ),

    # Physical Activity Domain
    "activity.experience_level": FieldDefinition(
        domain=AssessmentDomain.PHYSICAL_ACTIVITY,
        key="activity.experience_level",
        label="Pengalaman Olahraga",
        classification=FieldClassification.REQUIRED,
        field_type="select",
        options=["BEGINNER", "INTERMEDIATE", "ADVANCED"],
    ),
    "activity.available_days_per_week": FieldDefinition(
        domain=AssessmentDomain.PHYSICAL_ACTIVITY,
        key="activity.available_days_per_week",
        label="Hari Tersedia per Minggu",
        classification=FieldClassification.REQUIRED,
        field_type="number",
        description="Jumlah hari dalam seminggu untuk aktivitas fisik",
    ),
    "activity.minutes_per_session": FieldDefinition(
        domain=AssessmentDomain.PHYSICAL_ACTIVITY,
        key="activity.minutes_per_session",
        label="Durasi per Sesi (Menit)",
        classification=FieldClassification.REQUIRED,
        field_type="number",
    ),
    "activity.equipment": FieldDefinition(
        domain=AssessmentDomain.PHYSICAL_ACTIVITY,
        key="activity.equipment",
        label="Alat Olahraga yang Dimiliki",
        classification=FieldClassification.REQUIRED,
        field_type="multiselect",
        options=["NONE", "DUMBBELL", "RESISTANCE_BAND", "PULL_UP_BAR", "YOGA_MAT", "BENCH", "GYM_MEMBERSHIP", "OTHER"],
    ),
    "activity.physical_limitations": FieldDefinition(
        domain=AssessmentDomain.PHYSICAL_ACTIVITY,
        key="activity.physical_limitations",
        label="Riwayat Cedera / Batasan Fisik",
        classification=FieldClassification.REQUIRED,
        field_type="text",
        description="Tulis 'NONE' jika tidak ada batasan atau cedera",
    ),
    "activity.available_space": FieldDefinition(
        domain=AssessmentDomain.PHYSICAL_ACTIVITY,
        key="activity.available_space",
        label="Ketersediaan Ruang Latihan",
        classification=FieldClassification.OPTIONAL,
        field_type="select",
        options=["COMPACT_ROOM", "SPACIOUS_LIVING_ROOM", "OUTDOOR", "GYM"],
    ),
    "activity.workout_preference": FieldDefinition(
        domain=AssessmentDomain.PHYSICAL_ACTIVITY,
        key="activity.workout_preference",
        label="Preferensi Latihan",
        classification=FieldClassification.OPTIONAL,
        field_type="select",
        options=["BODYWEIGHT", "STRENGTH", "CARDIO", "MOBILITY", "HYBRID"],
    ),
}
