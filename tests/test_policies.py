"""Comprehensive Unit & Integration Tests for P1: Dynamic Enterprise Policy Management."""
import os
import sys
import pytest
from sqlalchemy.orm import Session

# Ensure backend & root are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.db import SessionLocal, init_db
from app.database.models import DBPolicy, DBPolicyAudit
from app.schemas.policy import PolicyCreate, PolicyUpdate, PolicyStatus, PolicyPriority, PolicyDecisionAction
from app.services import policy_service
from agents.orchestrator import run_governance_pipeline
from app.schemas.governance import GovernanceDecision

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    db = SessionLocal()
    policy_service.seed_default_policies(db)
    yield db
    db.close()

def test_1_create_policy_success(setup_db: Session):
    """Test creating a new enterprise policy in persistent storage."""
    policy_id = "POL-TEST-001"
    # Cleanup if exists
    existing = setup_db.query(DBPolicy).filter(DBPolicy.policy_id == policy_id).first()
    if existing:
        setup_db.delete(existing)
        setup_db.commit()

    data = PolicyCreate(
        policy_id=policy_id,
        name="Test Security Policy",
        description="Testing policy creation",
        rule_definition="Test rule requirement",
        decision_action=PolicyDecisionAction.REJECT,
        priority=PolicyPriority.CRITICAL,
        status=PolicyStatus.ACTIVE
    )
    policy = policy_service.create_policy(setup_db, data)
    assert policy.policy_id == policy_id
    assert policy.version == 1
    assert policy.status == "ACTIVE"

    # Verify audit record created
    audit = setup_db.query(DBPolicyAudit).filter(DBPolicyAudit.policy_id == policy_id, DBPolicyAudit.event_type == "CREATED").first()
    assert audit is not None

def test_2_duplicate_policy_id_rejection(setup_db: Session):
    """Test duplicate policy ID raises ValueError."""
    data = PolicyCreate(
        policy_id="POL-HUM-001",
        name="Duplicate Human Approval Policy",
        description="Should fail",
        rule_definition="Duplicate test",
        decision_action=PolicyDecisionAction.ESCALATE
    )
    with pytest.raises(ValueError, match="already exists"):
        policy_service.create_policy(setup_db, data)

def test_3_update_policy_and_version_increment(setup_db: Session):
    """Test updating policy increments version and logs audit event."""
    policy_id = "POL-HUM-001"
    update_data = PolicyUpdate(
        name="Human Authorization & Escalation Policy",
        rule_definition="Updated rule requirement requiring CISO review."
    )
    updated = policy_service.update_policy(setup_db, policy_id, update_data)
    assert updated.name == "Human Authorization & Escalation Policy"
    assert updated.version >= 2

    # Verify audit record
    audit = setup_db.query(DBPolicyAudit).filter(DBPolicyAudit.policy_id == policy_id, DBPolicyAudit.event_type == "UPDATED").first()
    assert audit is not None

def test_4_activate_deactivate_policy(setup_db: Session):
    """Test toggling policy status between ACTIVE and INACTIVE."""
    policy_id = "POL-MIN-004"
    policy_service.update_policy_status(setup_db, policy_id, "INACTIVE")
    p = policy_service.get_policy_by_id(setup_db, policy_id)
    assert p.status == "INACTIVE"

    # Reactivate
    policy_service.update_policy_status(setup_db, policy_id, "ACTIVE")
    p_active = policy_service.get_policy_by_id(setup_db, policy_id)
    assert p_active.status == "ACTIVE"

@pytest.mark.asyncio
async def test_5_inactive_policy_not_retrieved_in_governance(setup_db: Session):
    """Test INACTIVE policy is excluded from active retrieval and does not influence governance."""
    policy_id = "POL-TRN-002"
    # Deactivate Data Transfer Policy
    policy_service.update_policy_status(setup_db, policy_id, "INACTIVE")

    active_policies = policy_service.get_active_policies(setup_db)
    active_ids = [ap.policy_id for ap in active_policies]
    assert policy_id not in active_ids

    # Reactivate for subsequent tests
    policy_service.update_policy_status(setup_db, policy_id, "ACTIVE")

@pytest.mark.asyncio
async def test_6_restrictive_conflict_precedence():
    """Test that restrictive decisions (REJECT > ESCALATE > MODIFY > APPROVE) resolve conflicts deterministically."""
    db = SessionLocal()
    try:
        # Create custom high-priority REJECT policy
        pol_id = "POL-STRICT-REJECT"
        existing = db.query(DBPolicy).filter(DBPolicy.policy_id == pol_id).first()
        if not existing:
            data = PolicyCreate(
                policy_id=pol_id,
                name="Strict Zero Trust Policy",
                description="Blocks external transfers regardless of clearance",
                rule_definition="Export anonymized customer analytics to external targets is strictly blocked.",
                decision_action=PolicyDecisionAction.REJECT,
                priority=PolicyPriority.CRITICAL,
                status=PolicyStatus.ACTIVE
            )
            policy_service.create_policy(db, data)

        res = await run_governance_pipeline(
            request_id="REQ-TEST-CONFLICT",
            user_id="U001",
            role="Senior Data Analyst",
            action="Export anonymized aggregated customer analytics to external targets",
            target="public-endpoint-unauthorized"
        )
        # Clean up custom policy
        policy_service.delete_policy(db, pol_id)
        assert res.decision == GovernanceDecision.REJECT
    finally:
        db.close()
