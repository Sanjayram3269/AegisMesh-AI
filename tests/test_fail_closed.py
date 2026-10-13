"""Comprehensive Test Suite for CyberForge Fail-Closed Security Guarantees (P0).

Verifies:
1. Policy database unavailability fails closed.
2. Policy retrieval timeout fails closed.
3. Model provider failure or timeout fails closed.
4. Anonymous / missing caller identity fails closed.
5. Mock provider fallback in production cannot authorize protected actions.
6. Error masking scrubs credentials, API keys, database URLs, and stack traces.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from agents.enforcement.canonical_action import CanonicalAction, PrincipalIdentity, ResourceScope
from agents.enforcement.fail_closed import (
    FAIL_CLOSED_GUARD, SecurityFailureMode, MissingAuthorizationContextError,
    mask_sensitive_error_details
)
from agents.enforcement.tools import get_tool, reset_all_tool_side_effects


@pytest.fixture(autouse=True)
def clean_state():
    reset_all_tool_side_effects()


def test_1_policy_db_failure_fails_closed():
    """SECURITY INVARIANT: Policy DB failure must deny protected action."""
    action = CanonicalAction(
        action_id="ACT-FAIL-01",
        principal=PrincipalIdentity(user_id="U_ADMIN", role="ADMIN"),
        tool_name="cloud_resource_deploy",
        tool_version="2.0.0",
        operation="DEPLOY",
        resource_scope=ResourceScope(target="production-api-gateway", environment="PRODUCTION"),
        arguments={"resource_name": "gateway", "environment": "production", "config": {}},
    )

    decision = FAIL_CLOSED_GUARD.handle_policy_db_failure(
        action=action,
        exception=ConnectionError("SQLite database locked or corrupted")
    )
    assert decision.decision == "DENY"
    assert decision.action_blocked is True
    assert decision.unauthorized_side_effects is False
    assert decision.failure_mode == SecurityFailureMode.POLICY_DATABASE_UNAVAILABLE


def test_2_policy_timeout_fails_closed():
    """SECURITY INVARIANT: Policy retrieval timeout must abort execution."""
    action = CanonicalAction(
        action_id="ACT-FAIL-02",
        principal=PrincipalIdentity(user_id="U_ENG", role="ENGINEER"),
        tool_name="database_execute",
        tool_version="1.2.0",
        operation="EXECUTE",
        resource_scope=ResourceScope(target="internal-db"),
        arguments={"query": "SELECT 1;", "database": "internal-db", "read_only": True},
    )

    decision = FAIL_CLOSED_GUARD.handle_policy_timeout(action)
    assert decision.decision == "DENY"
    assert decision.action_blocked is True
    assert decision.failure_mode == SecurityFailureMode.POLICY_RETRIEVAL_TIMEOUT


def test_3_model_provider_error_fails_closed():
    """SECURITY INVARIANT: Upstream model failure must never permit tool execution."""
    action = CanonicalAction(
        action_id="ACT-FAIL-03",
        principal=PrincipalIdentity(user_id="U_USER", role="GENERAL_USER"),
        tool_name="payment_transfer",
        tool_version="1.0.0",
        operation="TRANSFER",
        resource_scope=ResourceScope(target="approved-treasury"),
        arguments={"recipient_account": "ACC-1", "amount": 100.0, "currency": "USD", "purpose": "Test"},
    )

    decision = FAIL_CLOSED_GUARD.handle_model_failure(
        action=action,
        error_type="504 Gateway Timeout from Hugging Face Router",
        raw_error=TimeoutError("Hugging Face API timed out after 30000ms")
    )
    assert decision.decision == "DENY"
    assert decision.action_blocked is True
    assert decision.failure_mode == SecurityFailureMode.MODEL_PROVIDER_ERROR


def test_4_anonymous_principal_fails_closed():
    """SECURITY INVARIANT: Missing caller identity is blocked before execution."""
    action = CanonicalAction(
        action_id="ACT-FAIL-04",
        principal=PrincipalIdentity(user_id="", role=""),
        tool_name="database_execute",
        tool_version="1.2.0",
        operation="EXECUTE",
        resource_scope=ResourceScope(target="internal-db"),
        arguments={"query": "SELECT 1;", "database": "internal-db", "read_only": True},
    )

    with pytest.raises(MissingAuthorizationContextError):
        FAIL_CLOSED_GUARD.validate_caller_authorization_context(action)


def test_5_mock_provider_in_production_cannot_authorize():
    """SECURITY INVARIANT: Mock provider fallback in production mode is blocked."""
    action = CanonicalAction(
        action_id="ACT-FAIL-05",
        principal=PrincipalIdentity(user_id="U_ADMIN", role="ADMIN"),
        tool_name="cloud_resource_deploy",
        tool_version="2.0.0",
        operation="DEPLOY",
        resource_scope=ResourceScope(target="production-api-gateway", environment="PRODUCTION"),
        arguments={"resource_name": "gateway", "environment": "production", "config": {}},
    )

    decision = FAIL_CLOSED_GUARD.handle_mock_provider_fallback(
        action=action,
        provider_name="Mock Demo Provider",
        is_production=True
    )
    assert decision.decision == "DENY"
    assert "Mock provider cannot authorize" in decision.safe_reason


def test_6_sensitive_error_details_masked():
    """SECURITY INVARIANT: Credentials, API keys, tokens, and stack traces are scrubbed."""
    raw_error = (
        "Database error connecting to postgres://admin:superSecretPassword123@db.prod.internal:5432/main. "
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secretKeyToken was rejected. "
        "File path: /Users/pavanaksshay/AegisMesh-AI/secret.key. api_key = hf_live_999998888877777"
    )

    masked = mask_sensitive_error_details(raw_error)
    assert "superSecretPassword123" not in masked
    assert "[REDACTED_PASSWORD]" in masked
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in masked
    assert "[REDACTED_TOKEN]" in masked
    assert "hf_live_999998888877777" not in masked
    assert "[REDACTED_API_KEY]" in masked
    assert "/Users/pavanaksshay" not in masked
