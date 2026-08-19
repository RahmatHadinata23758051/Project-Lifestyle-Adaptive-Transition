import hashlib
from app.nutrition_adjustment_proposal.constants import ProposalPolicy


def generate_proposal_fingerprint(
    evaluation_id: str,
    current_target_kcal: float,
    proposed_target_kcal: float,
    delta_kcal: float,
    policy_version: str = ProposalPolicy.VERSION,
) -> str:
    """
    Generates a deterministic cryptographic fingerprint for a nutrition adjustment proposal.
    """
    raw = f"{evaluation_id}:{round(current_target_kcal, 1)}:{round(proposed_target_kcal, 1)}:{round(delta_kcal, 1)}:{policy_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
