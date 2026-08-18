from typing import List, Dict, Any
from app.assessment.constants import AssessmentDomain, FieldClassification, DomainCompleteness
from app.assessment.field_registry import FIELD_REGISTRY
from app.assessment.router import AssessmentRouter


class AssessmentCompletenessEvaluator:
    """
    Evaluates completeness of user assessment per domain and overall plan readiness.
    Enforces 'Never Guess Required Data': If required fields are missing, plan is NOT ready.
    """

    @classmethod
    def evaluate(
        cls,
        active_goals: List[str],
        known_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        relevant_domains = AssessmentRouter.get_relevant_domains(active_goals)
        domain_results: Dict[str, Any] = {}
        all_missing_required: List[str] = []

        for domain in relevant_domains:
            domain_fields = [f for f in FIELD_REGISTRY.values() if f.domain == domain]
            required_fields = [f for f in domain_fields if f.classification == FieldClassification.REQUIRED]
            optional_fields = [f for f in domain_fields if f.classification == FieldClassification.OPTIONAL]

            missing_req = [
                f.key for f in required_fields
                if known_data.get(f.key) is None or (isinstance(known_data.get(f.key), str) and str(known_data.get(f.key)).strip() == "")
            ]
            all_missing_required.extend(missing_req)

            filled_req_count = len(required_fields) - len(missing_req)
            total_req_count = len(required_fields)

            if len(missing_req) == 0:
                domain_status = DomainCompleteness.COMPLETE
            elif filled_req_count > 0:
                domain_status = DomainCompleteness.IN_PROGRESS
            else:
                domain_status = DomainCompleteness.NOT_STARTED

            completion_percentage = (
                round((filled_req_count / total_req_count) * 100.0, 1) if total_req_count > 0 else 100.0
            )

            domain_results[domain.value] = {
                "status": domain_status.value,
                "completion_percentage": completion_percentage,
                "missing_required": missing_req,
                "total_required": total_req_count,
                "filled_required": filled_req_count,
            }

        # Overall Status
        has_any_in_progress = any(
            d["status"] == DomainCompleteness.IN_PROGRESS.value for d in domain_results.values()
        )
        all_complete = all(
            d["status"] == DomainCompleteness.COMPLETE.value for d in domain_results.values()
        ) and len(all_missing_required) == 0

        if all_complete and len(active_goals) > 0:
            overall_status = DomainCompleteness.COMPLETE
            is_plan_ready = True
        elif has_any_in_progress or any(d["status"] == DomainCompleteness.COMPLETE.value for d in domain_results.values()):
            overall_status = DomainCompleteness.IN_PROGRESS
            is_plan_ready = False
        else:
            overall_status = DomainCompleteness.NOT_STARTED
            is_plan_ready = False

        return {
            "overall_status": overall_status.value,
            "is_plan_ready": is_plan_ready,
            "missing_required_fields": all_missing_required,
            "domains": domain_results,
        }
