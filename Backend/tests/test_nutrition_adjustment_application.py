import pytest
import uuid
import jwt
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.db.session import SessionLocal, init_db
from app.models.user import User
from app.models.nutrition_adjustment_proposal import NutritionAdjustmentProposalRecord
from app.models.nutrition_state_revision import NutritionStateRevisionRecord
from app.models.nutrition_adjustment_application import NutritionAdjustmentApplicationRecord
from app.nutrition_adjustment_application.constants import (
    ApplicationStatus,
    ApplicationReasonCode,
    ApplicationPolicy,
)
from app.nutrition_adjustment_application.models import (
    ApplyNutritionAdjustmentCommand,
)
from app.nutrition_adjustment_application.validation import (
    validate_application_prerequisites,
)
from app.nutrition_adjustment_application.state_transition import (
    build_applied_state_transition,
)
from app.nutrition_adjustment_proposal.constants import (
    ProposalStatus,
    ProposalLifecycleState,
    ProposalType,
)
from app.nutrition_adjustment_proposal.models import (
    NutritionAdjustmentProposalDTO,
    EvidenceSnapshotDTO,
)
from app.services.nutrition_adjustment_application_service import (
    NutritionAdjustmentApplicationService,
)

init_db()


def create_mock_jwt(user_id: str, email: str, secret: str = settings.SUPABASE_JWT_SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _create_mock_accepted_proposal(
    db,
    owner_user_id: str,
    current_target_kcal: int = 2300,
    proposed_target_kcal: int = 2400,
    delta_kcal: int = 100,
    lifecycle_state: ProposalLifecycleState = ProposalLifecycleState.ACCEPTED,
    status: ProposalStatus = ProposalStatus.PROPOSAL_READY,
    created_at_dt: Optional[datetime] = None,
    expires_at_dt: Optional[datetime] = None,
) -> NutritionAdjustmentProposalRecord:
    now_dt = datetime.now(timezone.utc)
    c_dt = created_at_dt or now_dt
    e_dt = expires_at_dt or (now_dt + timedelta(hours=48))

    prop_id = f"prop_{uuid.uuid4().hex[:16]}"
    record = NutritionAdjustmentProposalRecord(
        id=prop_id,
        owner_user_id=owner_user_id,
        proposal_domain="ENERGY_TARGET",
        evaluation_id=f"eval_{uuid.uuid4().hex[:12]}",
        status=status.value,
        lifecycle_state=lifecycle_state.value,
        proposal_type=ProposalType.ENERGY_TARGET_INCREASE.value,
        current_target_kcal=current_target_kcal,
        proposed_target_kcal=proposed_target_kcal,
        delta_kcal=delta_kcal,
        confidence="HIGH",
        fingerprint="mock_fingerprint_hash",
        evidence_snapshot={
            "evaluation_id": "eval_mock",
            "decision": "CONSIDER_ADJUSTMENT",
            "review_domain": "ENERGY_TARGET_REVIEW",
            "evaluation_confidence": "HIGH",
            "weight_trend_direction": "STABLE",
            "weight_trend_confidence": "HIGH",
            "usable_days": 14,
            "weight_measurements_count": 6,
            "adherence_category": "HIGH_CONFIDENCE_ADHERENCE",
        },
        risk_flags=[],
        reason_codes=["ENERGY_TARGET_REVIEW_RECOMMENDED"],
        explanations=["Stable weight with high adherence."],
        policy_versions={"proposal_policy": "NUTRITION_ADJUSTMENT_PROPOSAL_V01"},
        created_at=c_dt,
        expires_at=e_dt,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def test_pure_validation_success():
    """
    Pure validation succeeds on valid prerequisite parameters.
    """
    prop = NutritionAdjustmentProposalDTO(
        proposal_id="prop_1",
        proposal_domain="ENERGY_TARGET",
        status=ProposalStatus.PROPOSAL_READY,
        lifecycle_state=ProposalLifecycleState.ACCEPTED,
        proposal_type=ProposalType.ENERGY_TARGET_INCREASE,
        current_target_kcal=2300,
        proposed_target_kcal=2400,
        delta_kcal=100,
        confidence="HIGH",
        evidence_summary=EvidenceSnapshotDTO(
            evaluation_id="eval_1",
            decision="CONSIDER_ADJUSTMENT",
            review_domain="ENERGY_TARGET_REVIEW",
            evaluation_confidence="HIGH",
            weight_trend_direction="STABLE",
            weight_trend_confidence="HIGH",
            usable_days=14,
            weight_measurements_count=6,
            adherence_category="HIGH_CONFIDENCE_ADHERENCE",
        ),
        fingerprint="fp1",
        created_at="2026-08-20T00:00:00Z",
        expires_at="2026-08-22T00:00:00Z",
    )
    cmd = ApplyNutritionAdjustmentCommand(
        proposal_id="prop_1",
        expected_current_target_kcal=2300,
        expected_state_revision=1,
        idempotency_key="key_1",
    )
    status, reasons, exps = validate_application_prerequisites(
        command=cmd,
        command_user_id="user_1",
        proposal=prop,
        proposal_owner_user_id="user_1",
        current_authoritative_target_kcal=2300,
        current_authoritative_revision=1,
        current_cumulative_adaptive_delta_kcal=0,
    )
    assert status is None
    assert len(reasons) == 0


def test_pure_state_transition_builds_revision_and_invalidation():
    """
    Pure transition builder constructs new revision increment and downstream invalidation flags.
    """
    prop = NutritionAdjustmentProposalDTO(
        proposal_id="prop_1",
        proposal_domain="ENERGY_TARGET",
        status=ProposalStatus.PROPOSAL_READY,
        lifecycle_state=ProposalLifecycleState.ACCEPTED,
        proposal_type=ProposalType.ENERGY_TARGET_INCREASE,
        current_target_kcal=2300,
        proposed_target_kcal=2400,
        delta_kcal=100,
        confidence="HIGH",
        evidence_summary=EvidenceSnapshotDTO(
            evaluation_id="eval_1",
            decision="CONSIDER_ADJUSTMENT",
            review_domain="ENERGY_TARGET_REVIEW",
            evaluation_confidence="HIGH",
            weight_trend_direction="STABLE",
            weight_trend_confidence="HIGH",
            usable_days=14,
            weight_measurements_count=6,
            adherence_category="HIGH_CONFIDENCE_ADHERENCE",
        ),
        fingerprint="fp1",
        created_at="2026-08-20T00:00:00Z",
        expires_at="2026-08-22T00:00:00Z",
    )
    cmd = ApplyNutritionAdjustmentCommand(
        proposal_id="prop_1",
        expected_current_target_kcal=2300,
        expected_state_revision=1,
        idempotency_key="key_1",
    )
    new_rev, result = build_applied_state_transition(
        command=cmd,
        proposal=prop,
        owner_user_id="user_1",
        previous_revision_number=1,
    )
    assert new_rev.revision_number == 2
    assert new_rev.target_energy_kcal == 2400
    assert result.status == ApplicationStatus.APPLIED
    assert result.applied_target_kcal == 2400
    assert result.delta_kcal == 100
    assert result.downstream_invalidation.requires_downstream_regeneration is True
    assert result.downstream_invalidation.daily_plan_invalidated is True


def test_happy_path_application_and_proposal_status_transition():
    """
    Happy path apply: proposal state becomes APPLIED, new state revision inserted, target updated.
    """
    db = SessionLocal()
    test_uid = f"user_apply_happy_{uuid.uuid4()}"
    try:
        db.add(User(id=test_uid, email=f"{test_uid}@chronos.local"))
        db.commit()

        prop_record = _create_mock_accepted_proposal(db, test_uid, current_target_kcal=2300, proposed_target_kcal=2400, delta_kcal=100)

        cmd = ApplyNutritionAdjustmentCommand(
            proposal_id=prop_record.id,
            expected_current_target_kcal=2300,
            expected_state_revision=1,
            idempotency_key=f"idemp_{uuid.uuid4()}",
        )

        result = NutritionAdjustmentApplicationService.apply_adjustment(db, test_uid, cmd)
        assert result.status == ApplicationStatus.APPLIED
        assert result.previous_target_kcal == 2300
        assert result.applied_target_kcal == 2400
        assert result.delta_kcal == 100
        assert result.previous_state_revision == 1
        assert result.new_state_revision == 2
        assert result.downstream_invalidation.requires_downstream_regeneration is True

        # Verify proposal row in DB is now APPLIED
        db.refresh(prop_record)
        assert prop_record.lifecycle_state == ProposalLifecycleState.APPLIED.value

        # Verify state revision in DB
        revisions = NutritionAdjustmentApplicationService.list_state_revisions(db, test_uid)
        assert len(revisions) == 1
        assert revisions[0]["revision_number"] == 2
        assert revisions[0]["target_energy_kcal"] == 2400
    finally:
        db.close()


def test_idempotent_retry_returns_already_applied_without_increment():
    """
    Same proposal and key returns ALREADY_APPLIED with original application details.
    """
    db = SessionLocal()
    test_uid = f"user_apply_idemp_{uuid.uuid4()}"
    try:
        db.add(User(id=test_uid, email=f"{test_uid}@chronos.local"))
        db.commit()

        prop_record = _create_mock_accepted_proposal(db, test_uid)
        idemp_key = f"idemp_{uuid.uuid4()}"
        cmd = ApplyNutritionAdjustmentCommand(
            proposal_id=prop_record.id,
            expected_current_target_kcal=2300,
            expected_state_revision=1,
            idempotency_key=idemp_key,
        )

        res1 = NutritionAdjustmentApplicationService.apply_adjustment(db, test_uid, cmd)
        assert res1.status == ApplicationStatus.APPLIED
        assert res1.new_state_revision == 2

        # Retry with same idempotency key and proposal
        res2 = NutritionAdjustmentApplicationService.apply_adjustment(db, test_uid, cmd)
        assert res2.status in (ApplicationStatus.APPLIED, ApplicationStatus.ALREADY_APPLIED)
        assert res2.application_id == res1.application_id
        assert res2.new_state_revision == 2

        # Ensure no duplicate revision was created
        revisions = NutritionAdjustmentApplicationService.list_state_revisions(db, test_uid)
        assert len(revisions) == 1
    finally:
        db.close()


def test_idempotency_conflict_on_reused_key_for_different_proposal():
    """
    Reusing an existing idempotency key for a different proposal fails with IDEMPOTENCY_CONFLICT.
    """
    db = SessionLocal()
    test_uid = f"user_apply_conflict_{uuid.uuid4()}"
    try:
        db.add(User(id=test_uid, email=f"{test_uid}@chronos.local"))
        db.commit()

        prop1 = _create_mock_accepted_proposal(db, test_uid)
        prop2 = _create_mock_accepted_proposal(db, test_uid)

        shared_key = f"shared_idemp_{uuid.uuid4()}"
        cmd1 = ApplyNutritionAdjustmentCommand(
            proposal_id=prop1.id,
            expected_current_target_kcal=2300,
            expected_state_revision=1,
            idempotency_key=shared_key,
        )
        NutritionAdjustmentApplicationService.apply_adjustment(db, test_uid, cmd1)

        cmd2 = ApplyNutritionAdjustmentCommand(
            proposal_id=prop2.id,
            expected_current_target_kcal=2300,
            expected_state_revision=2,
            idempotency_key=shared_key,
        )
        with pytest.raises(ValueError, match="Idempotency conflict"):
            NutritionAdjustmentApplicationService.apply_adjustment(db, test_uid, cmd2)
    finally:
        db.close()


def test_proposal_not_accepted_blocks_apply():
    """
    A proposal that is still PENDING or REJECTED cannot be applied.
    """
    db = SessionLocal()
    test_uid = f"user_apply_pending_{uuid.uuid4()}"
    try:
        db.add(User(id=test_uid, email=f"{test_uid}@chronos.local"))
        db.commit()

        prop_pending = _create_mock_accepted_proposal(
            db, test_uid, lifecycle_state=ProposalLifecycleState.PENDING
        )
        cmd = ApplyNutritionAdjustmentCommand(
            proposal_id=prop_pending.id,
            expected_current_target_kcal=2300,
            expected_state_revision=1,
            idempotency_key=f"idemp_{uuid.uuid4()}",
        )
        with pytest.raises(ValueError, match="PROPOSAL_NOT_ACCEPTED"):
            NutritionAdjustmentApplicationService.apply_adjustment(db, test_uid, cmd)
    finally:
        db.close()


def test_expired_proposal_blocks_apply():
    """
    A proposal that expired before apply cannot be applied.
    """
    db = SessionLocal()
    test_uid = f"user_apply_expired_{uuid.uuid4()}"
    try:
        db.add(User(id=test_uid, email=f"{test_uid}@chronos.local"))
        db.commit()

        past_exp = datetime.now(timezone.utc) - timedelta(hours=2)
        prop_expired = _create_mock_accepted_proposal(
            db, test_uid, expires_at_dt=past_exp
        )
        cmd = ApplyNutritionAdjustmentCommand(
            proposal_id=prop_expired.id,
            expected_current_target_kcal=2300,
            expected_state_revision=1,
            idempotency_key=f"idemp_{uuid.uuid4()}",
        )
        with pytest.raises(ValueError, match="PROPOSAL_EXPIRED"):
            NutritionAdjustmentApplicationService.apply_adjustment(db, test_uid, cmd)
    finally:
        db.close()


def test_target_mismatch_blocks_apply():
    """
    If expected target does not match authoritative proposal source target, apply is rejected.
    """
    db = SessionLocal()
    test_uid = f"user_apply_tgt_mismatch_{uuid.uuid4()}"
    try:
        db.add(User(id=test_uid, email=f"{test_uid}@chronos.local"))
        db.commit()

        prop = _create_mock_accepted_proposal(db, test_uid, current_target_kcal=2300)
        cmd = ApplyNutritionAdjustmentCommand(
            proposal_id=prop.id,
            expected_current_target_kcal=2450,  # mismatch with 2300
            expected_state_revision=1,
            idempotency_key=f"idemp_{uuid.uuid4()}",
        )
        with pytest.raises(ValueError, match="TARGET_CONFLICT"):
            NutritionAdjustmentApplicationService.apply_adjustment(db, test_uid, cmd)
    finally:
        db.close()


def test_revision_mismatch_blocks_apply():
    """
    If expected state revision does not match current state revision, apply is rejected.
    """
    db = SessionLocal()
    test_uid = f"user_apply_rev_mismatch_{uuid.uuid4()}"
    try:
        db.add(User(id=test_uid, email=f"{test_uid}@chronos.local"))
        db.commit()

        prop = _create_mock_accepted_proposal(db, test_uid, current_target_kcal=2300)
        cmd = ApplyNutritionAdjustmentCommand(
            proposal_id=prop.id,
            expected_current_target_kcal=2300,
            expected_state_revision=8,  # mismatch with current 1
            idempotency_key=f"idemp_{uuid.uuid4()}",
        )
        with pytest.raises(ValueError, match="REVISION_CONFLICT"):
            NutritionAdjustmentApplicationService.apply_adjustment(db, test_uid, cmd)
    finally:
        db.close()


def test_clinical_safety_eligibility_change_blocks_apply():
    """
    If user status changed to OUT_OF_SCOPE before apply, apply is rejected.
    """
    db = SessionLocal()
    test_uid = f"user_apply_safety_{uuid.uuid4()}"
    try:
        db.add(User(id=test_uid, email=f"{test_uid}@chronos.local"))
        db.commit()

        prop = _create_mock_accepted_proposal(db, test_uid)
        cmd = ApplyNutritionAdjustmentCommand(
            proposal_id=prop.id,
            expected_current_target_kcal=2300,
            expected_state_revision=1,
            idempotency_key=f"idemp_{uuid.uuid4()}",
        )
        with pytest.raises(ValueError, match="ELIGIBILITY_CHANGED"):
            NutritionAdjustmentApplicationService.apply_adjustment(
                db, test_uid, cmd, current_eligibility_status="OUT_OF_SCOPE"
            )
    finally:
        db.close()


def test_new_evidence_watermark_blocks_apply():
    """
    If new check-in or weight arrived after proposal creation, apply is rejected.
    """
    db = SessionLocal()
    test_uid = f"user_apply_evid_wm_{uuid.uuid4()}"
    try:
        db.add(User(id=test_uid, email=f"{test_uid}@chronos.local"))
        db.commit()

        created_dt = datetime.now(timezone.utc) - timedelta(hours=2)
        prop = _create_mock_accepted_proposal(db, test_uid, created_at_dt=created_dt)

        cmd = ApplyNutritionAdjustmentCommand(
            proposal_id=prop.id,
            expected_current_target_kcal=2300,
            expected_state_revision=1,
            idempotency_key=f"idemp_{uuid.uuid4()}",
        )
        newer_evidence_time = datetime.now(timezone.utc).isoformat()
        with pytest.raises(ValueError, match="EVIDENCE_CHANGED"):
            NutritionAdjustmentApplicationService.apply_adjustment(
                db, test_uid, cmd, last_evidence_updated_at=newer_evidence_time
            )
    finally:
        db.close()


def test_cumulative_adaptive_ceiling_guardrail():
    """
    If cumulative applied adjustment already reached +400 kcal, apply is blocked with ADAPTIVE_LIMIT_REACHED.
    """
    db = SessionLocal()
    test_uid = f"user_apply_ceiling_{uuid.uuid4()}"
    try:
        db.add(User(id=test_uid, email=f"{test_uid}@chronos.local"))
        db.commit()

        # Seed 4 prior applications of +100 kcal = 400 kcal total
        now_dt = datetime.now(timezone.utc)
        for i in range(1, 5):
            prior_app = NutritionAdjustmentApplicationRecord(
                id=f"prior_app_{i}_{uuid.uuid4().hex[:8]}",
                owner_user_id=test_uid,
                proposal_id=f"prior_prop_{i}_{uuid.uuid4().hex[:8]}",
                idempotency_key=f"prior_key_{i}_{uuid.uuid4().hex[:8]}",
                previous_state_revision=i,
                new_state_revision=i + 1,
                previous_target_kcal=2300 + (i - 1) * 100,
                applied_target_kcal=2300 + i * 100,
                delta_kcal=100,
                application_status=ApplicationStatus.APPLIED.value,
                downstream_invalidation={},
                applied_at=now_dt,
                created_at=now_dt,
            )
            db.add(prior_app)
            rev_rec = NutritionStateRevisionRecord(
                id=f"prior_rev_{i}_{uuid.uuid4().hex[:8]}",
                owner_user_id=test_uid,
                revision_number=i + 1,
                target_energy_kcal=2300 + i * 100,
                effective_from=now_dt,
                created_at=now_dt,
            )
            db.add(rev_rec)
        db.commit()

        prop = _create_mock_accepted_proposal(
            db, test_uid, current_target_kcal=2700, proposed_target_kcal=2800, delta_kcal=100
        )
        cmd = ApplyNutritionAdjustmentCommand(
            proposal_id=prop.id,
            expected_current_target_kcal=2700,
            expected_state_revision=5,
            idempotency_key=f"idemp_{uuid.uuid4()}",
        )
        with pytest.raises(ValueError, match="ADAPTIVE_LIMIT_REACHED"):
            NutritionAdjustmentApplicationService.apply_adjustment(db, test_uid, cmd)
    finally:
        db.close()


@pytest.mark.asyncio
async def test_api_apply_adjustment_endpoint():
    """
    REST API test: full lifecycle from create proposal -> accept proposal -> apply adjustment -> read application & state revisions.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        test_uid = str(uuid.uuid4())
        token = create_mock_jwt(test_uid, f"user_{test_uid[:8]}@chronos.local")
        headers = {"Authorization": f"Bearer {token}"}

        db = SessionLocal()
        try:
            db.add(User(id=test_uid, email=f"user_{test_uid[:8]}@chronos.local"))
            db.commit()
        finally:
            db.close()

        eval_mock = {
            "evaluation_id": "eval_mock_api_apply",
            "evaluated_at": "2026-08-20T00:00:00Z",
            "decision": "CONSIDER_ADJUSTMENT",
            "review_domain": "ENERGY_TARGET_REVIEW",
            "confidence": "HIGH",
            "evidence_window": {
                "start_date": "2026-08-01",
                "end_date": "2026-08-15",
                "total_days": 14,
                "usable_adherence_days": 14,
                "weight_measurement_count": 6,
            },
            "data_sufficiency": {
                "status": "SUFFICIENT",
                "usable_days_count": 14,
                "weight_count": 6,
                "is_sufficient": True,
                "reasons": [],
            },
            "adherence_summary": {
                "category": "HIGH_CONFIDENCE_ADHERENCE",
                "reporting_coverage_ratio": 1.0,
                "full_completion_ratio": 0.9,
                "confidence": "HIGH",
            },
            "weight_trend": {
                "measurement_count": 6,
                "start_weight_kg": 60.0,
                "end_weight_kg": 60.0,
                "slope_kg_per_day": 0.0,
                "direction": "STABLE",
                "confidence": "HIGH",
                "is_interpretable": True,
                "outlier_count": 0,
            },
            "reason_patterns": {
                "reason_counts": {},
                "dominant_reasons": [],
                "pattern_confidence": "HIGH",
            },
            "reason_codes": ["WEIGHT_TREND_STABLE", "HIGH_ADHERENCE"],
            "explanations": ["Weight trend is stable while adherence is high."],
            "policy_version": "NUTRITION_ADAPTATION_EVALUATION_V01",
        }

        prop_create_payload = {
            "evaluation": eval_mock,
            "current_target_energy_kcal": 2300,
            "cumulative_adaptive_adjustment_kcal": 0,
            "nutrition_goal_type": "NUTRITION_WEIGHT_GAIN",
            "current_eligibility_status": "ELIGIBLE",
            "reference_time": "2026-08-20T00:00:00Z",
        }

        # 1. Create proposal
        create_res = await client.post(
            "/api/v1/nutrition-adjustments/proposals",
            json=prop_create_payload,
            headers=headers,
        )
        assert create_res.status_code == 200, f"Error creating prop: {create_res.text}"
        prop_id = create_res.json()["proposal_id"]

        # 2. Accept proposal
        accept_res = await client.post(
            f"/api/v1/nutrition-adjustments/proposals/{prop_id}/accept",
            headers=headers,
        )
        assert accept_res.status_code == 200, f"Error accepting prop: {accept_res.text}"
        assert accept_res.json()["lifecycle_state"] == "ACCEPTED"

        # 3. Apply proposal
        apply_payload = {
            "expected_current_target_kcal": 2300,
            "expected_state_revision": 1,
            "idempotency_key": f"api_key_{uuid.uuid4()}",
            "reference_time": "2026-08-20T00:00:00Z",
        }
        apply_res = await client.post(
            f"/api/v1/nutrition-adjustments/proposals/{prop_id}/apply",
            json=apply_payload,
            headers=headers,
        )
        assert apply_res.status_code == 200, f"Error applying prop: {apply_res.text}"
        data = apply_res.json()
        assert data["status"] == "APPLIED"
        assert data["applied_target_kcal"] == 2400
        assert data["delta_kcal"] == 100
        assert data["new_state_revision"] == 2
        assert data["downstream_invalidation"]["requires_downstream_regeneration"] is True

        app_id = data["application_id"]

        # 4. Read application record by ID
        get_app = await client.get(
            f"/api/v1/nutrition-adjustments/applications/{app_id}",
            headers=headers,
        )
        assert get_app.status_code == 200
        assert get_app.json()["application_id"] == app_id

        # 5. Read state revisions
        get_revs = await client.get(
            "/api/v1/nutrition-adjustments/state/revisions",
            headers=headers,
        )
        assert get_revs.status_code == 200
        revs_data = get_revs.json()
        assert len(revs_data) == 1
        assert revs_data[0]["revision_number"] == 2
        assert revs_data[0]["target_energy_kcal"] == 2400
