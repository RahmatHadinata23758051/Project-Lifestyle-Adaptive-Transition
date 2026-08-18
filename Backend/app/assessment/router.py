from typing import List, Dict, Any, Set
from app.assessment.constants import AssessmentDomain, FieldClassification
from app.assessment.field_registry import FIELD_REGISTRY, FieldDefinition


class AssessmentRouter:
    """
    Pure Adaptive Assessment Router.
    Determines relevant questions to ask by analyzing active goals and already-known user context.
    Enforces 'Ask Only What Is Missing' and 'Ask Only What Is Relevant'.
    """

    @staticmethod
    def get_relevant_domains(active_goals: List[str]) -> Set[AssessmentDomain]:
        domains: Set[AssessmentDomain] = {AssessmentDomain.CORE_PROFILE}
        for goal in active_goals:
            g = goal.upper()
            if "SLEEP" in g:
                domains.add(AssessmentDomain.SLEEP_ROUTINE)
            elif "NUTRITION" in g or "WEIGHT" in g:
                domains.add(AssessmentDomain.NUTRITION_WEIGHT_GAIN)
            elif "ACTIVITY" in g or "EXERCISE" in g or "WORKOUT" in g:
                domains.add(AssessmentDomain.PHYSICAL_ACTIVITY)
        return domains

    @classmethod
    def determine_missing_fields(
        cls,
        active_goals: List[str],
        known_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculates missing required and optional fields based on active goals and existing data.
        Derived fields (e.g. age) are calculated automatically from source fields and not requested.
        """
        relevant_domains = cls.get_relevant_domains(active_goals)
        missing_required: List[str] = []
        missing_optional: List[str] = []
        questions_to_ask: List[Dict[str, Any]] = []

        for key, definition in FIELD_REGISTRY.items():
            # Filter by relevant domains
            if definition.domain not in relevant_domains:
                continue

            # Skip DERIVED fields (e.g. age) from being asked directly
            if definition.classification == FieldClassification.DERIVED:
                continue

            # Skip HISTORICAL tracking fields
            if definition.classification == FieldClassification.HISTORICAL:
                continue

            val = known_data.get(key)
            is_empty = val is None or (isinstance(val, str) and val.strip() == "")

            if is_empty:
                if definition.classification == FieldClassification.REQUIRED:
                    missing_required.append(key)
                elif definition.classification == FieldClassification.OPTIONAL:
                    missing_optional.append(key)

                questions_to_ask.append({
                    "key": definition.key,
                    "domain": definition.domain.value,
                    "label": definition.label,
                    "classification": definition.classification.value,
                    "field_type": definition.field_type,
                    "options": definition.options,
                    "description": definition.description,
                    "is_profile_field": definition.is_profile_field,
                })

        return {
            "active_goals": active_goals,
            "relevant_domains": [d.value for d in relevant_domains],
            "missing_required_fields": missing_required,
            "missing_optional_fields": missing_optional,
            "questions": questions_to_ask,
        }
