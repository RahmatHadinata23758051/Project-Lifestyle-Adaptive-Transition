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
