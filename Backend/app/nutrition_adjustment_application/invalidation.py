from app.nutrition_adjustment_application.models import DownstreamInvalidationDTO


def build_downstream_invalidation(
    source_revision: int,
    target_revision: int,
) -> DownstreamInvalidationDTO:
    """
    Constructs the downstream invalidation descriptor.
    Declares old revision artifacts stale while preserving historical records.
    Does NOT execute candidate generation or meal planning inside the apply phase.
    """
    return DownstreamInvalidationDTO(
        source_revision=int(source_revision),
        target_revision=int(target_revision),
        meal_structure_invalidated=True,
        food_candidates_invalidated=True,
        budget_selection_invalidated=True,
        daily_plan_invalidated=True,
        requires_downstream_regeneration=True,
        reason=f"Authoritative energy target updated across state revisions ({source_revision} -> {target_revision}). Downstream artifacts require regeneration.",
    )


def is_downstream_artifact_current(
    artifact_revision_number: int,
    current_authoritative_revision_number: int,
) -> bool:
    """
    Revision linkage invariant:
    An artifact (meal structure, food candidate set, budget selection, daily plan preview)
    qualifies as current IF AND ONLY IF its source nutrition revision exactly matches
    the authoritative current nutrition revision (e.g. rev 7 != rev 8 -> stale by definition).
    """
    return int(artifact_revision_number) == int(current_authoritative_revision_number)


def evaluate_artifact_freshness(
    artifact_revision_number: int,
    current_authoritative_revision_number: int,
) -> dict:
    """
    Evaluates whether an artifact is current or stale.
    Artifact qualifies as CURRENT iff its source revision matches the authoritative revision.
    """
    is_current = is_downstream_artifact_current(artifact_revision_number, current_authoritative_revision_number)
    return {
        "is_current": is_current,
        "status": "CURRENT" if is_current else "STALE",
        "artifact_revision": int(artifact_revision_number),
        "current_revision": int(current_authoritative_revision_number),
    }
