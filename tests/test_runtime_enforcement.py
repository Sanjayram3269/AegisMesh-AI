"""Comprehensive Test Suite for CyberForge Runtime Enforcement Layer (P0).

Verifies execution boundary invariants:
1. Denied actions produce ZERO side effects.
2. Direct tool invocation bypass attempts are blocked.
3. Argument schema validation prevents malformed execution.
4. Argument mutation after approval triggers digest mismatch rejection.
5. Approval replay attacks are blocked.
6. Expired approvals are rejected.
7. Cryptographic audit chain verifies integrity and detects block tampering.
8. Audit persistence failure causes fail-closed execution blockage.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import datetime, timezone, timedelta
from agents.enforcement.canonical_action import CanonicalAction, PrincipalIdentity, ResourceScope
from agents.enforcement.tools import (
    TOOL_REGISTRY, DirectExecutionBypassError, reset_all_tool_side_effects,
    get_tool, ToolSchemaValidationError
)
from agents.enforcement.approvals import (
    APPROVAL_MANAGER, ApprovalExpiredError, ApprovalAlreadyConsumedError,
    ApprovalDigestMismatchError, ApprovalPolicyVersionMismatchError
)
from agents.enforcement.tamper_audit import AUDIT_LEDGER, AuditPersistenceError
from agents.enforcement.gateway import ENFORCEMENT_GATEWAY


@pytest.fixture(autouse=True)
def clean_enforcement_state():
    """Resets tool side effects, approval manager, and audit ledger between tests."""
    reset_all_tool_side_effects()
    APPROVAL_MANAGER._approvals.clear()
    AUDIT_LEDGER.clear()
    AUDIT_LEDGER.set_simulate_failure(False)


def test_1_direct_tool_invocation_raises_bypass_error():
    """SECURITY INVARIANT: Tools cannot be called directly; must route through Gateway."""
    db_tool = get_tool("database_execute")
    assert db_tool is not None

    with pytest.raises(DirectExecutionBypassError) as exc_info:
        db_tool.execute(query="DROP TABLE users;", database="internal-db")
    
    assert "cannot be invoked directly" in str(exc_info.value)
    assert db_tool.side_effect_count == 0


def test_2_unauthorized_action_denied_zero_side_effects():
    """SECURITY INVARIANT: Unauthorized requests are denied with zero side effects produced."""
    db_tool = get_tool("database_execute")
    assert db_tool.side_effect_count == 0

    action = CanonicalAction(
        action_id="ACT-001",
        principal=PrincipalIdentity(user_id="U_INTERN", role="INTERN"),
        tool_name="database_execute",
        tool_version="1.2.0",
        operation="EXECUTE",
        resource_scope=ResourceScope(target="unauthorized-endpoint", environment="PRODUCTION"),
        arguments={"query": "DELETE FROM customers;", "database": "internal-db", "read_only": False},
    )

    res = ENFORCEMENT_GATEWAY.enforce_and_execute(action)
    assert res.decision == "DENY"
    assert res.executed is False
    assert res.side_effects_occurred is False
    # CRITICAL: Underlying tool was NEVER reached
    assert db_tool.side_effect_count == 0


def test_3_schema_validation_blocks_invalid_arguments():
    """SECURITY INVARIANT: Argument schema validation rejects malformed payload prior to execution."""
    payment_tool = get_tool("payment_transfer")
    assert payment_tool.side_effect_count == 0

    # Missing required 'recipient_account' and non-numeric amount
    action = CanonicalAction(
        action_id="ACT-002",
        principal=PrincipalIdentity(user_id="U_FIN", role="FINANCE_MANAGER", clearance_level="PRIVILEGED"),
        tool_name="payment_transfer",
        tool_version="1.0.0",
        operation="TRANSFER",
        resource_scope=ResourceScope(target="approved-treasury", trust_level="HIGH"),
        arguments={"amount": "NOT_A_NUMBER", "currency": "USD", "purpose": "Test"},
    )

    res = ENFORCEMENT_GATEWAY.enforce_and_execute(action)
    assert res.decision == "DENY"
    assert res.executed is False
    assert "schema validation failed" in res.decision_reason.lower()
    assert payment_tool.side_effect_count == 0


def test_4_require_approval_blocks_execution_until_approved():
    """SECURITY INVARIANT: High-risk actions require approval and do not execute while pending."""
    export_tool = get_tool("customer_data_export")
    assert export_tool.side_effect_count == 0

    action = CanonicalAction(
        action_id="ACT-003",
        principal=PrincipalIdentity(user_id="U_ANALYST", role="ANALYST"),
        tool_name="customer_data_export",
        tool_version="1.1.0",
        operation="TRANSFER",
        resource_scope=ResourceScope(
            target="approved-analytics-service",
            trust_level="MEDIUM",
            data_classification="RESTRICTED"
        ),
        arguments={
            "dataset": "full_customer_profiles",
            "destination": "approved-analytics-service",
            "format": "JSON",
            "anonymize_pii": False
        },
    )

    # Initial call without approval reference
    res = ENFORCEMENT_GATEWAY.enforce_and_execute(action)
    assert res.decision == "REQUIRE_APPROVAL"
    assert res.executed is False
    assert res.approval_request is not None
    approval_id = res.approval_request["approval_id"]
    assert export_tool.side_effect_count == 0

    # Human reviewer approves the request
    APPROVAL_MANAGER.review_approval(
        approval_id=approval_id,
        reviewer_id="CISO_01",
        reviewer_role="CISO",
        decision="APPROVED",
        comments="Approved for Q3 vendor analysis."
    )

    # Subsequent execution with approved token succeeds
    res_exec = ENFORCEMENT_GATEWAY.enforce_and_execute(action, approval_id=approval_id)
    assert res_exec.decision == "ALLOW"
    assert res_exec.executed is True
    assert res_exec.side_effects_occurred is True
    assert export_tool.side_effect_count == 1


def test_5_argument_mutation_after_approval_rejected():
    """SECURITY INVARIANT: Tampering with arguments after approval invalidates digest and blocks execution."""
    payment_tool = get_tool("payment_transfer")
    assert payment_tool.side_effect_count == 0

    action = CanonicalAction(
        action_id="ACT-004",
        principal=PrincipalIdentity(user_id="U_FIN", role="FINANCE_MANAGER"),
        tool_name="payment_transfer",
        tool_version="1.0.0",
        operation="TRANSFER",
        resource_scope=ResourceScope(target="approved-treasury", trust_level="HIGH", data_classification="RESTRICTED"),
        arguments={"recipient_account": "ACC-12345", "amount": 5000.0, "currency": "USD", "purpose": "Vendor fee"},
    )

    # Request approval for $5,000
    app_req = APPROVAL_MANAGER.create_approval_request(action, required_role="CISO")
    APPROVAL_MANAGER.review_approval(
        approval_id=app_req.approval_id,
        reviewer_id="CISO_01",
        reviewer_role="CISO",
        decision="APPROVED"
    )

    # Attacker mutates amount to $500,000 using the same approval ID
    tampered_action = CanonicalAction(
        action_id="ACT-004",
        principal=PrincipalIdentity(user_id="U_FIN", role="FINANCE_MANAGER"),
        tool_name="payment_transfer",
        tool_version="1.0.0",
        operation="TRANSFER",
        resource_scope=ResourceScope(target="approved-treasury", trust_level="HIGH", data_classification="RESTRICTED"),
        arguments={"recipient_account": "ACC-12345", "amount": 500000.0, "currency": "USD", "purpose": "Vendor fee"},
    )

    res = ENFORCEMENT_GATEWAY.enforce_and_execute(tampered_action, approval_id=app_req.approval_id)
    assert res.decision == "DENY"
    assert res.executed is False
    assert "digest" in res.decision_reason.lower() or "tampering" in res.decision_reason.lower()
    # Side effects remain 0
    assert payment_tool.side_effect_count == 0


def test_6_approval_replay_rejected():
    """SECURITY INVARIANT: An approval cannot be reused once consumed."""
    action = CanonicalAction(
        action_id="ACT-005",
        principal=PrincipalIdentity(user_id="U_FIN", role="FINANCE_MANAGER", clearance_level="PRIVILEGED"),
        tool_name="payment_transfer",
        tool_version="1.0.0",
        operation="TRANSFER",
        resource_scope=ResourceScope(target="approved-treasury", trust_level="HIGH", data_classification="RESTRICTED"),
        arguments={"recipient_account": "ACC-55555", "amount": 1000.0, "currency": "USD", "purpose": "Stipend"},
    )

    app_req = APPROVAL_MANAGER.create_approval_request(action, required_role="MANAGER")
    APPROVAL_MANAGER.review_approval(
        approval_id=app_req.approval_id,
        reviewer_id="MGR_01",
        reviewer_role="MANAGER",
        decision="APPROVED"
    )

    # First execution succeeds
    res1 = ENFORCEMENT_GATEWAY.enforce_and_execute(action, approval_id=app_req.approval_id)
    assert res1.decision == "ALLOW"
    assert res1.executed is True

    # Replay execution with same approval ID fails
    res2 = ENFORCEMENT_GATEWAY.enforce_and_execute(action, approval_id=app_req.approval_id)
    assert res2.decision == "DENY"
    assert res2.executed is False
    assert "replay" in res2.decision_reason.lower() or "consumed" in res2.decision_reason.lower()


def test_7_expired_approval_rejected():
    """SECURITY INVARIANT: Expired approvals are rejected."""
    action = CanonicalAction(
        action_id="ACT-006",
        principal=PrincipalIdentity(user_id="U_ANALYST", role="ANALYST"),
        tool_name="customer_data_export",
        tool_version="1.1.0",
        operation="TRANSFER",
        resource_scope=ResourceScope(target="approved-analytics-service", data_classification="RESTRICTED"),
        arguments={"dataset": "users", "destination": "approved-analytics-service", "format": "CSV"},
    )

    # Create request with already expired timestamp
    app_req = APPROVAL_MANAGER.create_approval_request(action, ttl_minutes=-10)
    app_req.status = app_req.status  # Pending
    
    with pytest.raises(ApprovalExpiredError):
        APPROVAL_MANAGER.review_approval(
            approval_id=app_req.approval_id,
            reviewer_id="MGR_01",
            reviewer_role="MANAGER",
            decision="APPROVED"
        )


def test_8_cryptographic_audit_ledger_chain_integrity():
    """SECURITY INVARIANT: Audit ledger maintains verifiable SHA-256 hash chaining."""
    action = CanonicalAction(
        action_id="ACT-007",
        principal=PrincipalIdentity(user_id="U_ENG", role="ENGINEER", clearance_level="PRIVILEGED"),
        tool_name="database_execute",
        tool_version="1.2.0",
        operation="QUERY",
        resource_scope=ResourceScope(target="internal-db", trust_level="HIGH"),
        arguments={"query": "SELECT * FROM customers;", "database": "internal-db", "read_only": True},
    )

    res1 = ENFORCEMENT_GATEWAY.enforce_and_execute(action)
    res2 = ENFORCEMENT_GATEWAY.enforce_and_execute(action)
    assert res1.executed is True
    assert res2.executed is True

    # Verify chain integrity
    is_valid, msg, broken_idx = AUDIT_LEDGER.verify_chain_integrity()
    assert is_valid is True
    assert broken_idx is None

    # Simulate tampering with block 0 content
    AUDIT_LEDGER._chain[0].decision = "TAMPERED_DECISION"
    is_valid_after_tamper, msg_tamper, broken_idx_tamper = AUDIT_LEDGER.verify_chain_integrity()
    assert is_valid_after_tamper is False
    assert broken_idx_tamper == 0
    assert "tampering detected" in msg_tamper.lower()


def test_9_fail_closed_audit_guarantee():
    """SECURITY INVARIANT: If audit persistence fails, critical operations are blocked."""
    AUDIT_LEDGER.set_simulate_failure(True)
    deploy_tool = get_tool("cloud_resource_deploy")

    action = CanonicalAction(
        action_id="ACT-008",
        principal=PrincipalIdentity(user_id="U_ADMIN", role="ADMIN", clearance_level="ADMIN"),
        tool_name="cloud_resource_deploy",
        tool_version="2.0.0",
        operation="DEPLOY",
        resource_scope=ResourceScope(target="production-api-gateway", environment="PRODUCTION", trust_level="HIGH"),
        arguments={"resource_name": "gateway-v2", "environment": "production", "config": {"replicas": 3}},
    )

    # With audit failure, gateway cannot guarantee compliance
    with pytest.raises(AuditPersistenceError):
        ENFORCEMENT_GATEWAY.enforce_and_execute(action)
    
    assert deploy_tool.side_effect_count == 0


def test_10_soc_active_response_tools_protection():
    """SECURITY INVARIANT: ResponseGuard SOC active response tools (isolate_host, disable_account, block_ip) are strictly protected."""
    iso_tool = get_tool("isolate_host")
    acct_tool = get_tool("disable_account")
    ip_tool = get_tool("block_ip")

    assert iso_tool is not None and acct_tool is not None and ip_tool is not None

    # Direct invocation raises DirectExecutionBypassError
    with pytest.raises(DirectExecutionBypassError):
        iso_tool.execute(hostname="srv-domain-controller-01", isolation_mode="FULL")

    with pytest.raises(DirectExecutionBypassError):
        acct_tool.execute(username="ceo_executive", reason="Suspicious login")

    with pytest.raises(DirectExecutionBypassError):
        ip_tool.execute(ip_address="198.51.100.1")

    assert iso_tool.side_effect_count == 0
    assert acct_tool.side_effect_count == 0
    assert ip_tool.side_effect_count == 0

    # Authorized gateway execution works with single-use ticket
    action = CanonicalAction(
        action_id="ACT-SOC-001",
        principal=PrincipalIdentity(user_id="U_SOC_ANALYST", role="ANALYST", clearance_level="PRIVILEGED"),
        tool_name="isolate_host",
        tool_version="1.0.0",
        operation="EXECUTE",
        resource_scope=ResourceScope(target="host-workstation-42", environment="PRODUCTION", trust_level="HIGH"),
        arguments={"hostname": "host-workstation-42", "isolation_mode": "FULL", "allow_dns": False},
    )

    res = ENFORCEMENT_GATEWAY.enforce_and_execute(action)
    assert res.decision == "ALLOW"
    assert res.executed is True
    assert res.side_effects_occurred is True
    assert iso_tool.side_effect_count == 1

