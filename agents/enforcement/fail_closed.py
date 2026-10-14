"""CyberForge Fail-Closed Security & Failure-Mode Handlers.

Guarantees that every failure path (database, model provider, policy retrieval,
audit, or mock fallback) results in a secure, fail-closed enforcement decision.
Protected actions never become permitted because a dependency fails.
"""

from dataclasses import dataclass
from enum import Enum
import logging
import re
from typing import Any, Dict, Optional, Tuple

from app.schemas.governance import GovernanceDecision
from agents.enforcement.canonical_action import CanonicalAction


logger = logging.getLogger("cyberforge.fail_closed")


class SecurityFailureMode(str, Enum):
    POLICY_DATABASE_UNAVAILABLE = "POLICY_DATABASE_UNAVAILABLE"
    POLICY_RETRIEVAL_TIMEOUT = "POLICY_RETRIEVAL_TIMEOUT"
    MALFORMED_POLICY_DEFINITION = "MALFORMED_POLICY_DEFINITION"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    MODEL_PROVIDER_ERROR = "MODEL_PROVIDER_ERROR"
    INVALID_MODEL_OUTPUT = "INVALID_MODEL_OUTPUT"
    MISSING_AUTHORIZATION_CONTEXT = "MISSING_AUTHORIZATION_CONTEXT"
    INVALID_TOOL_ARGUMENTS = "INVALID_TOOL_ARGUMENTS"
    AUDIT_PERSISTENCE_FAILURE = "AUDIT_PERSISTENCE_FAILURE"
    MOCK_PROVIDER_DOWNGRADE_ATTEMPT = "MOCK_PROVIDER_DOWNGRADE_ATTEMPT"
    PARTIAL_MULTISTEP_EXECUTION_FAILURE = "PARTIAL_MULTISTEP_EXECUTION_FAILURE"


class FailClosedSecurityError(Exception):
    """Base error for fail-closed security events."""
    pass


class MockProviderInProductionError(FailClosedSecurityError):
    """Raised when mock provider attempts to authorize actions in production mode."""
    pass


class MissingAuthorizationContextError(FailClosedSecurityError):
    """Raised when request lacks principal user_id, role, or credentials."""
    pass


def mask_sensitive_error_details(error_message: str) -> str:
    """Sanitizes error messages removing stack traces, API keys, tokens, and database passwords."""
    sanitized = str(error_message)
    # Mask API keys and bearer tokens
    sanitized = re.sub(r'(bearer\s+)[A-Za-z0-9_\-\.]{8,}', r'\1[REDACTED_TOKEN]', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'(api[_\-]?key\s*[:=]\s*)[A-Za-z0-9_\-\.]{8,}', r'\1[REDACTED_API_KEY]', sanitized, flags=re.IGNORECASE)
    # Mask database connection strings with passwords
    sanitized = re.sub(r'(postgres|mysql|sqlite|mongodb)://[^:]+:([^@]+)@', r'\1://[USER]:[REDACTED_PASSWORD]@', sanitized)
    # Mask internal file system paths
    sanitized = re.sub(r'(/Users/[^/\s]+|/home/[^/\s]+)', r'[INTERNAL_PATH]', sanitized)
    # Remove Python traceback blocks if present
    if "Traceback (most recent call last):" in sanitized:
        sanitized = "Security Gateway encountered an internal dependency failure. Request denied under fail-closed policy."
    return sanitized


@dataclass
class FailClosedDecision:
    failure_mode: SecurityFailureMode
    decision: str  # "DENY" or "REQUIRE_APPROVAL"
    safe_reason: str
    action_blocked: bool = True
    unauthorized_side_effects: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_mode": self.failure_mode.value,
            "decision": self.decision,
            "safe_reason": self.safe_reason,
            "action_blocked": self.action_blocked,
            "unauthorized_side_effects": self.unauthorized_side_effects,
        }


class FailClosedSecurityGuard:
    """Inspects and handles failure paths across all subsystem boundaries."""

    def __init__(self, environment: str = "PRODUCTION"):
        self.environment = environment

    def handle_policy_db_failure(self, action: CanonicalAction, exception: Exception) -> FailClosedDecision:
        """Invoked when policy database is unreachable. Enforces strict deny-by-default."""
        logger.error(f"[FAIL-CLOSED] Policy database unavailable during action {action.action_id}: {exception}")
        return FailClosedDecision(
            failure_mode=SecurityFailureMode.POLICY_DATABASE_UNAVAILABLE,
            decision="DENY",
            safe_reason="Policy database unavailable. Protected action denied under fail-closed security guarantee.",
        )

    def handle_policy_timeout(self, action: CanonicalAction) -> FailClosedDecision:
        """Invoked when policy retrieval exceeds latency SLA. Fails closed."""
        return FailClosedDecision(
            failure_mode=SecurityFailureMode.POLICY_RETRIEVAL_TIMEOUT,
            decision="DENY",
            safe_reason="Policy retrieval timed out. Execution aborted to prevent unvalidated access.",
        )

    def handle_model_failure(
        self,
        action: CanonicalAction,
        error_type: str,
        raw_error: Optional[Exception] = None,
    ) -> FailClosedDecision:
        """Invoked when LLM provider returns 5xx, times out, or outputs malformed response.
        
        A language model failure NEVER causes tool execution to be permitted!
        """
        safe_msg = mask_sensitive_error_details(str(raw_error) if raw_error else error_type)
        return FailClosedDecision(
            failure_mode=SecurityFailureMode.MODEL_PROVIDER_ERROR,
            decision="DENY",
            safe_reason=f"AI model provider failure ({safe_msg}). Tool execution blocked under fail-closed policy.",
        )

    def handle_mock_provider_fallback(
        self,
        action: CanonicalAction,
        provider_name: str,
        is_production: bool = True,
    ) -> FailClosedDecision:
        """Verifies that mock fallback provider CANNOT authorize protected production actions."""
        if is_production and "mock" in provider_name.lower():
            return FailClosedDecision(
                failure_mode=SecurityFailureMode.MOCK_PROVIDER_DOWNGRADE_ATTEMPT,
                decision="DENY",
                safe_reason="SECURITY ALERT: Mock provider cannot authorize operations in production environment.",
            )
        return FailClosedDecision(
            failure_mode=SecurityFailureMode.MOCK_PROVIDER_DOWNGRADE_ATTEMPT,
            decision="REQUIRE_APPROVAL",
            safe_reason="Mock provider execution active. Restricted operations require manual human review.",
        )

    def validate_caller_authorization_context(self, action: CanonicalAction) -> None:
        """Verifies caller principal identity is non-empty and authenticated."""
        if not action.principal.user_id or action.principal.user_id.strip() in ["", "anonymous", "null"]:
            raise MissingAuthorizationContextError("Request missing caller user_id identity.")
        if not action.principal.role or action.principal.role.strip() in ["", "anonymous", "none"]:
            raise MissingAuthorizationContextError("Request missing caller role authorization context.")


# Global Security Guard Instance
FAIL_CLOSED_GUARD = FailClosedSecurityGuard()
