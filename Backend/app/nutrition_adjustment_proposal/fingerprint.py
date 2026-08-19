import hashlib
from app.nutrition_adjustment_proposal.constants import ProposalPolicy


def generate_proposal_fingerprint(
    evaluation_id: str,
    current_target_kcal: int,
    proposed_target_kcal: int,
    delta_kcal: int,
    policy_version: str = ProposalPolicy.VERSION,
) -> str:
    """
    Generates a deterministic cryptographic fingerprint for a nutrition adjustment proposal.
    """
    raw = f"{evaluation_id}:{int(current_target_kcal)}:{int(proposed_target_kcal)}:{int(delta_kcal)}:{policy_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
