"""
Comprehensive Test Suite for AegisMesh AI Policy Evolution & Change Intelligence.
Verifies all Section 2 Test Requirements and DB Persistence Invariants.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app.database.db import SessionLocal, init_db
from app.schemas.policy import PolicyCreate, PolicyUpdate
from app.schemas.policy_evolution import (
    PolicySnapshot, PolicyChangeType, PolicyImpactLevel
)
from agents.policy_evolution import (
    create_policy_snapshot, detect_structural_change,
    calculate_policy_impact_score, determine_autonomous_action,
    detect_policy_conflicts, run_historical_replay, analyze_policy_change
)
from app.services import policy_service, policy_version_service
from app.database.models import DBPolicy, DBPolicyVersion, DBPolicyChangeEvent


# ──────────────────────────────────────────────────────────────────────────────
# TEST 1: Cosmetic / Textual Policy Change -> LOW Impact
# ──────────────────────────────────────────────────────────────────────────────
def test_1_cosmetic_textual_policy_change_low_impact():
    old_p = PolicySnapshot(
        policy_id="POL-PII-003", name="PII Protection Policy", version=1,
        decision_action="MODIFY", priority="MEDIUM", status="ACTIVE",
        description="Requires stripping PII fields.",
        rule_definition="Customer records containing email or phone numbers must be anonymized."
    )
    new_p = PolicySnapshot(
        policy_id="POL-PII-003", name="PII Protection Policy", version=2,
        decision_action="MODIFY", priority="MEDIUM", status="ACTIVE",
        description="Updated documentation text for PII stripping policy.",
        rule_definition="Customer records containing email or phone numbers must be anonymized."
    )

    change_type, summary = detect_structural_change(old_p, new_p)
    assert change_type == PolicyChangeType.TEXTUAL_CHANGE

    score, level = calculate_policy_impact_score(change_type, old_p, new_p)
    assert level == PolicyImpactLevel.LOW
    assert score < 25

    req_review, rec_act, auto_act = determine_autonomous_action(level, change_type)
    assert req_review == False
    assert auto_act == "ENFORCED_AUTOMATICALLY"


# ──────────────────────────────────────────────────────────────────────────────
# TEST 2: PII Scope Expansion -> HIGH Impact + Historical Replay
# ──────────────────────────────────────────────────────────────────────────────
def test_2_pii_scope_expansion_high_impact():
    old_p = PolicySnapshot(
        policy_id="POL-PII-003", name="PII Protection Policy", version=1,
        decision_action="MODIFY", priority="MEDIUM", status="ACTIVE",
        description="Strip email fields.",
        rule_definition="Customer records containing email must be anonymized."
    )
    new_p = PolicySnapshot(
        policy_id="POL-PII-003", name="PII Protection Policy", version=2,
        decision_action="MODIFY", priority="MEDIUM", status="ACTIVE",
        description="Strip all PII fields.",
        rule_definition="Customer records containing all PII, SSN, financial data, and restricted details must be anonymized."
    )

    change_type, summary = detect_structural_change(old_p, new_p)
    assert change_type in [PolicyChangeType.DATA_SENSITIVITY_CHANGE, PolicyChangeType.SCOPE_EXPANSION]

    score, level = calculate_policy_impact_score(change_type, old_p, new_p)
    assert level in [PolicyImpactLevel.HIGH, PolicyImpactLevel.CRITICAL]
    assert score >= 50


# ──────────────────────────────────────────────────────────────────────────────
# TEST 3: Decision Change APPROVE -> MODIFY -> Affected Actions Detected
# ──────────────────────────────────────────────────────────────────────────────
def test_3_decision_change_approve_to_modify():
    old_p = PolicySnapshot(
        policy_id="POL-ACC-006", name="Access Policy", version=1,
        decision_action="APPROVE", priority="HIGH", status="ACTIVE",
        description="Allow production deploy",
        rule_definition="IF target.environment = PRODUCTION AND action.type IN [DELETE, MODIFY, DEPLOY, CONFIGURE] AND authorization.status = VERIFIED THEN decision = APPROVE."
    )
    new_p = PolicySnapshot(
        policy_id="POL-ACC-006", name="Access Policy", version=2,
        decision_action="MODIFY", priority="HIGH", status="ACTIVE",
        description="Modify production deploy",
        rule_definition="IF target.environment = PRODUCTION AND action.type IN [DELETE, MODIFY, DEPLOY, CONFIGURE] AND authorization.status = VERIFIED THEN decision = MODIFY."
    )

    change_type, summary = detect_structural_change(old_p, new_p)
    assert change_type == PolicyChangeType.DECISION_CHANGED

    historical = [
        {"request_id": "AUD-101", "user_id": "U01", "role": "Engineer", "action": "Deploy update", "target": "production-api-gateway", "data_classification": "Internal", "authorization_status": "Verified"}
    ]

    replay = run_historical_replay(old_p, new_p, historical, [new_p])
    assert replay.affected_actions_count == 1
    assert replay.affected_actions[0].old_decision != replay.affected_actions[0].new_decision


# ──────────────────────────────────────────────────────────────────────────────
# TEST 4: Security Policy Weakened -> CRITICAL + Human Review Required
# ──────────────────────────────────────────────────────────────────────────────
def test_4_security_policy_weakened_critical_human_review():
    old_p = PolicySnapshot(
        policy_id="POL-SEC-005", name="Security Policy", version=1,
        decision_action="REJECT", priority="HIGH", status="ACTIVE",
        description="Reject unapproved external transfers",
        rule_definition="External transfers without approval are REJECTED."
    )
    new_p = PolicySnapshot(
        policy_id="POL-SEC-005", name="Security Policy", version=2,
        decision_action="APPROVE", priority="LOW", status="ACTIVE",
        description="Approve external transfers",
        rule_definition="External transfers are APPROVED."
    )

    change_type, summary = detect_structural_change(old_p, new_p)
    assert change_type == PolicyChangeType.SECURITY_IMPACT_CHANGE

    score, level = calculate_policy_impact_score(change_type, old_p, new_p)
    assert level in [PolicyImpactLevel.HIGH, PolicyImpactLevel.CRITICAL]

    req_review, rec_act, auto_act = determine_autonomous_action(level, change_type)
    assert req_review == True
    assert "PENDING" in auto_act or "BLOCKED" in auto_act


# ──────────────────────────────────────────────────────────────────────────────
# TEST 5: Policy Deactivation -> Impact Score & Review Analysis
# ──────────────────────────────────────────────────────────────────────────────
def test_5_policy_deactivation_impact():
    old_p = PolicySnapshot(
        policy_id="POL-TRN-002", name="Transfer Policy", version=1,
        decision_action="REJECT", priority="CRITICAL", status="ACTIVE",
        description="Active transfer policy", rule_definition="Prohibit unapproved transfers"
    )
    new_p = PolicySnapshot(
        policy_id="POL-TRN-002", name="Transfer Policy", version=2,
        decision_action="REJECT", priority="CRITICAL", status="INACTIVE",
        description="Deactivated policy", rule_definition="Prohibit unapproved transfers"
    )

    change_type, summary = detect_structural_change(old_p, new_p)
    assert change_type == PolicyChangeType.ACTIVATION_CHANGED

    score, level = calculate_policy_impact_score(change_type, old_p, new_p)
    assert score >= 25


# ──────────────────────────────────────────────────────────────────────────────
# TEST 6: Conflicting Policies -> Conflict Detected
# ──────────────────────────────────────────────────────────────────────────────
def test_6_conflicting_policies_detected():
    p1 = PolicySnapshot(
        policy_id="POL-ACC-006", name="Production Deploy Policy", version=1,
        decision_action="APPROVE", priority="HIGH", status="ACTIVE",
        description="Allow production deploy",
        rule_definition="IF target = PRODUCTION THEN decision = APPROVE."
    )
    p2 = PolicySnapshot(
        policy_id="POL-HUM-001", name="Production Escalate Policy", version=1,
        decision_action="ESCALATE", priority="HIGH", status="ACTIVE",
        description="Escalate production deploy",
        rule_definition="IF target = PRODUCTION THEN decision = ESCALATE."
    )

    conflicts = detect_policy_conflicts(p1, [p1, p2])
    assert len(conflicts) >= 1
    assert conflicts[0].conflict_detected == True
    assert "POL-ACC-006" in conflicts[0].policy_ids
    assert "POL-HUM-001" in conflicts[0].policy_ids


# ──────────────────────────────────────────────────────────────────────────────
# TEST 7: No Change -> No Unnecessary Impact Analysis
# ──────────────────────────────────────────────────────────────────────────────
def test_7_no_change_detected():
    old_p = PolicySnapshot(
        policy_id="POL-MIN-004", name="Minimization Policy", version=1,
        decision_action="MODIFY", priority="LOW", status="ACTIVE",
        description="Minimization", rule_definition="Use aggregated views."
    )
    new_p = PolicySnapshot(
        policy_id="POL-MIN-004", name="Minimization Policy", version=1,
        decision_action="MODIFY", priority="LOW", status="ACTIVE",
        description="Minimization", rule_definition="Use aggregated views."
    )

    change_type, summary = detect_structural_change(old_p, new_p)
    assert change_type == PolicyChangeType.NO_CHANGE

    score, level = calculate_policy_impact_score(change_type, old_p, new_p)
    assert score == 0
    assert level == PolicyImpactLevel.LOW


# ──────────────────────────────────────────────────────────────────────────────
# TEST 8: Historical Replay Does Not Mutate Historical Records
# ──────────────────────────────────────────────────────────────────────────────
def test_8_historical_replay_non_mutation():
    old_p = PolicySnapshot(
        policy_id="POL-ACC-006", name="Access Policy", version=1,
        decision_action="APPROVE", priority="MEDIUM", status="ACTIVE",
        description="", rule_definition="IF target = PRODUCTION THEN decision = APPROVE."
    )
    new_p = PolicySnapshot(
        policy_id="POL-ACC-006", name="Access Policy", version=2,
        decision_action="REJECT", priority="HIGH", status="ACTIVE",
        description="", rule_definition="IF target = PRODUCTION THEN decision = REJECT."
    )

    sample_record = {
        "audit_id": "AUD-999", "user_id": "U01", "role": "Engineer",
        "action": "Deploy", "target": "production-api-gateway",
        "data_classification": "Internal", "authorization_status": "Verified",
        "decision": "APPROVE"
    }
    original_copy = dict(sample_record)

    replay = run_historical_replay(old_p, new_p, [sample_record], [new_p])
    
    # Verify sample record was NOT mutated
    assert sample_record["decision"] == original_copy["decision"]
    assert sample_record["audit_id"] == "AUD-999"


# ──────────────────────────────────────────────────────────────────────────────
# TEST 9: SQLite Database Persistence & Version Incrementing
# ──────────────────────────────────────────────────────────────────────────────
def test_9_sqlite_persistence_and_version_control():
    init_db()
    db = SessionLocal()
    try:
        # Create test policy
        pid = "POL-TEST-EVO-01"
        existing = policy_service.get_policy_by_id(db, pid)
        if not existing:
            created = policy_service.create_policy(db, PolicyCreate(
                policy_id=pid,
                name="Test Evolution Policy",
                description="Initial test policy description",
                rule_definition="Initial rule criteria for testing",
                decision_action="APPROVE",
                priority="MEDIUM",
                status="ACTIVE"
            ))
            assert created.version == 1

        # Edit rule definition
        new_text = "TEST EVOLUTION CHANGE: All high-risk actions require mandatory CISO review and audit evidence."
        updated = policy_service.update_policy(db, pid, PolicyUpdate(
            rule_definition=new_text
        ))
        
        # Verify persistence and version increment
        assert updated.version == 2
        assert updated.rule_definition == new_text

        # Verify retrieval from DB
        fetched = policy_service.get_policy_by_id(db, pid)
        assert fetched.rule_definition == new_text
        assert fetched.version == 2

        # Verify no-op edit does NOT increment version
        no_op_res = policy_service.update_policy(db, pid, PolicyUpdate(
            rule_definition=new_text
        ))
        assert no_op_res.version == 2

        # Verify change event was created in DB
        events = policy_version_service.get_all_change_events(db)
        test_events = [e for e in events if e.policy_id == pid]
        assert len(test_events) >= 1
        assert test_events[0].version == 2
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────────────────────
# TEST 10: Section 1 Invariant Verification
# ──────────────────────────────────────────────────────────────────────────────
def test_10_section_1_risk_scoring_invariants_preserved():
    from agents.risk import compute_canonical_risk
    inh, eff, red, level, factors, mitigations, signals = compute_canonical_risk(
        data_classification="Internal",
        target="production-api-gateway",
        authorization_status="Verified",
        role="Senior Engineer",
        action="Deploy an approved configuration update to production"
    )
    assert eff < inh
    assert red > 0
    assert level.value == "LOW"
