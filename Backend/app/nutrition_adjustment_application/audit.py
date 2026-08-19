import hashlib


def generate_audit_reference(
    owner_user_id: str,
    proposal_id: str,
    previous_revision: int,
    new_revision: int,
    applied_at: str,
) -> str:
    """
    Generates a deterministic cryptographic audit reference linking the proposal, state revision, and user.
    """
    raw = f"{owner_user_id}:{proposal_id}:{previous_revision}:{new_revision}:{applied_at}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
