from typing import List, Dict
from collections import Counter
from app.nutrition_adaptation.constants import EvaluationConfidence
from app.nutrition_adaptation.models import (
    NutritionEvidenceDayDTO,
    ReasonPatternSummaryDTO,
)
from app.nutrition_adherence.constants import DeviationReason


def evaluate_reason_patterns(days: List[NutritionEvidenceDayDTO]) -> ReasonPatternSummaryDTO:
    """
    Detects repeated deviation patterns across evidence days.
    """
    all_reasons: List[str] = []
    for d in days:
        for r in d.deviation_reasons:
            val = r.value if hasattr(r, "value") else str(r)
            all_reasons.append(val)

    if not all_reasons:
        return ReasonPatternSummaryDTO(
            reason_counts={},
            dominant_reasons=[],
            pattern_confidence=EvaluationConfidence.UNKNOWN,
        )

    counts = Counter(all_reasons)
    # Dominant if frequency >= 2
    dominant: List[DeviationReason] = []
    for r_str, count in counts.items():
        if count >= 2:
            try:
                dominant.append(DeviationReason(r_str))
            except Exception:
                pass

    confidence = EvaluationConfidence.HIGH if len(all_reasons) >= 4 else EvaluationConfidence.MEDIUM

    return ReasonPatternSummaryDTO(
        reason_counts=dict(counts),
        dominant_reasons=dominant,
        pattern_confidence=confidence,
    )
