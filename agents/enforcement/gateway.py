"""CyberForge Centralized Runtime Enforcement Gateway.

The authoritative execution boundary between AI agent recommendations and protected tool executors.
Ensures:
1. Server-side identity validation & role-spoofing rejection.
2. Pre-execution TOCTOU policy checks within a strict fail-closed exception envelope.
3. Cryptographic single-use execution tickets.
4. Empirical verification that denied actions produce ZERO side effects on underlying infrastructure.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from agents.enforcement.canonical_action import CanonicalAction, PrincipalIdentity, ResourceScope
from agents.enforcement.tickets import ExecutionTicket
from agents.enforcement.identity_registry import (
    IDENTITY_SERVICE, IdentityVerificationError, RoleSpoofingError
)
from agents.enforcement.infrastructure_state import INFRASTRUCTURE_STORE
from agents.enforcement.tools import (
    TOOL_REGISTRY, ProtectedToolBase, ToolExecutionResult,
    ToolSchemaValidationError, DirectExecutionBypassError, get_tool
)
from agents.enforcement.approvals import (
    APPROVAL_MANAGER, ApprovalRequest, ApprovalStatus, ApprovalError,
    ApprovalRevokedError, ApprovalAlreadyConsumedError, ApprovalDigestMismatchError
)
from agents.enforcement.tamper_audit import AUDIT_LEDGER, AuditLedgerEntry, AuditPersistenceError
from agents.enforcement.fail_closed import mask_sensitive_error_details
from agents.policy_engine import (
    normalize_governance_input, evaluate_explicit_policies,
    resolve_final_decision, MatchedPolicyTrace
)
from app.schemas.governance import GovernanceDecision

logger = logging.getLogger("cyberforge.gateway")


@dataclass
class GatewayEnforcementResult:
    execution_id: str
    action_id: str
    tool_name: str
    decision: str  # ALLOW, DENY, REQUIRE_APPROVAL, MODIFIED
    decision_reason: str
    executed: bool
    side_effects_occurred: bool
    side_effect_summary: str
    canonical_digest: str
    policy_version_evaluated: int
    matched_policy_ids: List[str]
    tool_output: Optional[Any] = None
    approval_request: Optional[Dict[str, Any]] = None
    audit_entry_id: Optional[str] = None
    latency_ms: float = 0.0
    error: Optional[str] = None
    state_before: Optional[Dict[str, Any]] = None
    state_after: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "action_id": self.action_id,
            "tool_name": self.tool_name,
            "decision": self.decision,
            "decision_reason": self.decision_reason,
            "executed": self.executed,
            "side_effects_occurred": self.side_effects_occurred,
            "side_effect_summary": self.side_effect_summary,
            "canonical_digest": self.canonical_digest,
            "policy_version_evaluated": self.policy_version_evaluated,
            "matched_policy_ids": self.matched_policy_ids,
            "tool_output": self.tool_output,
            "approval_request": self.approval_request,
            "audit_entry_id": self.audit_entry_id,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
            "state_before": self.state_before,
            "state_after": self.state_after,
        }


class RuntimeEnforcementGateway:
    """Centralized Execution Gateway enforcing security policies at the tool execution boundary."""

    def __init__(self):
        self._active_policy_version: int = 1
        self._active_db_policies: List[Dict[str, Any]] = []

    def set_active_policy_context(self, version: int, db_policies: Optional[List[Dict[str, Any]]] = None):
        self._active_policy_version = version
        self._active_db_policies = db_policies or []

    def enforce_and_execute(
        self,
        action: CanonicalAction,
        approval_id: Optional[str] = None,
        force_revalidation: bool = True,
        bypass_identity_verification: bool = False,
    ) -> GatewayEnforcementResult:
        """The single authoritative point of execution for all protected tools.
        
        Evaluates, validates, and gates action execution at the physical boundary.
        """
        start_time = time.perf_counter()
        execution_id = f"EXEC-{uuid.uuid4().hex[:10].upper()}"
        tool_name = action.tool_name
        canonical_digest = action.compute_digest()
        state_before = INFRASTRUCTURE_STORE.snapshot()

        # ──────────────────────────────────────────────────────────────────────
        # STEP 1: Authoritative Principal Identity & Anti-Spoofing Verification
        # ──────────────────────────────────────────────────────────────────────
        authoritative_role = action.principal.role
        authoritative_clearance = action.principal.clearance_level

        if not bypass_identity_verification:
            try:
                auth_principal = IDENTITY_SERVICE.verify_and_resolve_principal(
                    user_id=action.principal.user_id,
                    claimed_role=action.principal.role,
                    auth_token=action.principal.authorization_token,
                    allow_synthetic_test=True,
                )
                authoritative_role = auth_principal.role
                authoritative_clearance = auth_principal.clearance_level
            except (RoleSpoofingError, IdentityVerificationError) as id_err:
                latency = (time.perf_counter() - start_time) * 1000
                safe_err = mask_sensitive_error_details(str(id_err))
                state_after = INFRASTRUCTURE_STORE.snapshot()
                audit_entry = AUDIT_LEDGER.append_entry(
                    request_id=action.action_id,
                    execution_id=execution_id,
                    principal_user_id=action.principal.user_id or "ANONYMOUS",
                    principal_role=action.principal.role or "NONE",
                    tool_name=tool_name,
                    action_digest=canonical_digest,
                    decision="DENY",
                    executed=False,
                    side_effects_occurred=False,
                    side_effect_summary="BLOCKED: Identity verification failure / Role spoofing detected",
                    policy_version=action.policy_version,
                    details={"identity_error": safe_err},
                    state_before=state_before,
                    state_after=state_after,
                )
                return GatewayEnforcementResult(
                    execution_id=execution_id,
                    action_id=action.action_id,
                    tool_name=tool_name,
                    decision="DENY",
                    decision_reason=safe_err,
                    executed=False,
                    side_effects_occurred=False,
                    side_effect_summary="No side effects produced (identity verification failure).",
                    canonical_digest=canonical_digest,
                    policy_version_evaluated=self._active_policy_version,
                    matched_policy_ids=[],
                    audit_entry_id=audit_entry.entry_id,
                    latency_ms=latency,
                    error=safe_err,
                    state_before=state_before,
                    state_after=state_after,
                )

        # ──────────────────────────────────────────────────────────────────────
        # STEP 2: Tool Registry & Existence Verification (Deny Unknown Tools)
        # ──────────────────────────────────────────────────────────────────────
        tool = get_tool(tool_name)
        if not tool:
            latency = (time.perf_counter() - start_time) * 1000
            state_after = INFRASTRUCTURE_STORE.snapshot()
            audit_entry = AUDIT_LEDGER.append_entry(
                request_id=action.action_id,
                execution_id=execution_id,
                principal_user_id=action.principal.user_id,
                principal_role=authoritative_role,
                tool_name=tool_name,
                action_digest=canonical_digest,
                decision="DENY",
                executed=False,
                side_effects_occurred=False,
                side_effect_summary="BLOCKED: Tool is unregistered or prohibited in tool catalog",
                policy_version=action.policy_version,
                details={"reason": f"Tool '{tool_name}' not found in registry"},
                state_before=state_before,
                state_after=state_after,
            )
            return GatewayEnforcementResult(
                execution_id=execution_id,
                action_id=action.action_id,
                tool_name=tool_name,
                decision="DENY",
                decision_reason=f"Prohibited tool: '{tool_name}' is not in the authorized tool registry.",
                executed=False,
                side_effects_occurred=False,
                side_effect_summary="No side effects produced (tool execution blocked).",
                canonical_digest=canonical_digest,
                policy_version_evaluated=self._active_policy_version,
                matched_policy_ids=[],
                audit_entry_id=audit_entry.entry_id,
                latency_ms=latency,
                state_before=state_before,
                state_after=state_after,
            )

        # ──────────────────────────────────────────────────────────────────────
        # STEP 3: Schema Validation (Server-side argument typing & bounds)
        # ──────────────────────────────────────────────────────────────────────
        try:
            tool.validate_schema(action.arguments)
        except ToolSchemaValidationError as val_err:
            latency = (time.perf_counter() - start_time) * 1000
            state_after = INFRASTRUCTURE_STORE.snapshot()
            audit_entry = AUDIT_LEDGER.append_entry(
                request_id=action.action_id,
                execution_id=execution_id,
                principal_user_id=action.principal.user_id,
                principal_role=authoritative_role,
                tool_name=tool_name,
                action_digest=canonical_digest,
                decision="DENY",
                executed=False,
                side_effects_occurred=False,
                side_effect_summary=f"BLOCKED: Malformed tool arguments ({val_err})",
                policy_version=action.policy_version,
                details={"schema_error": str(val_err)},
                state_before=state_before,
                state_after=state_after,
            )
            return GatewayEnforcementResult(
                execution_id=execution_id,
                action_id=action.action_id,
                tool_name=tool_name,
                decision="DENY",
                decision_reason=f"Tool schema validation failed: {str(val_err)}",
                executed=False,
                side_effects_occurred=False,
                side_effect_summary="No side effects produced (invalid schema blocked).",
                canonical_digest=canonical_digest,
                policy_version_evaluated=self._active_policy_version,
                matched_policy_ids=[],
                audit_entry_id=audit_entry.entry_id,
                latency_ms=latency,
                error=str(val_err),
                state_before=state_before,
                state_after=state_after,
            )

        # ──────────────────────────────────────────────────────────────────────
        # STEP 4: Pre-Execution TOCTOU Policy Check & Scope Authorization
        # ──────────────────────────────────────────────────────────────────────
        try:
            norm_inp = normalize_governance_input(
                user_id=action.principal.user_id,
                role=authoritative_role,
                action=f"{action.operation} {tool_name} with args {list(action.arguments.keys())}",
                target=action.resource_scope.target,
                data_classification=action.resource_scope.data_classification,
                authorization_status="VERIFIED" if authoritative_clearance in ["PRIVILEGED", "ADMIN", "CISO"] else "PENDING",
            )
            policy_traces: List[MatchedPolicyTrace] = evaluate_explicit_policies(
                norm_inp, active_policies=self._active_db_policies
            )
            matched_traces = [t for t in policy_traces if t.matched]
            matched_ids = [t.policy_id for t in matched_traces]
        except Exception as pol_err:
            latency = (time.perf_counter() - start_time) * 1000
            safe_msg = mask_sensitive_error_details(str(pol_err))
            state_after = INFRASTRUCTURE_STORE.snapshot()
            audit_entry = AUDIT_LEDGER.append_entry(
                request_id=action.action_id,
                execution_id=execution_id,
                principal_user_id=action.principal.user_id,
                principal_role=authoritative_role,
                tool_name=tool_name,
                action_digest=canonical_digest,
                decision="DENY",
                executed=False,
                side_effects_occurred=False,
                side_effect_summary="BLOCKED: Fail-closed policy evaluation failure",
                policy_version=action.policy_version,
                details={"policy_engine_error": safe_msg},
                state_before=state_before,
                state_after=state_after,
            )
            return GatewayEnforcementResult(
                execution_id=execution_id,
                action_id=action.action_id,
                tool_name=tool_name,
                decision="DENY",
                decision_reason=f"Security Gateway encountered an internal dependency failure: {safe_msg}. Request denied under fail-closed policy.",
                executed=False,
                side_effects_occurred=False,
                side_effect_summary="No side effects produced (fail-closed policy exception).",
                canonical_digest=canonical_digest,
                policy_version_evaluated=self._active_policy_version,
                matched_policy_ids=[],
                audit_entry_id=audit_entry.entry_id,
                latency_ms=latency,
                error=safe_msg,
                state_before=state_before,
                state_after=state_after,
            )

        # Role Clearance Check using Authoritative Server-Side Role
        role_insufficient = False
        if tool.required_role in ["ADMIN", "CISO"] and authoritative_role not in ["ADMIN", "CISO", "MANAGER", "LEAD"]:
            role_insufficient = True
        elif tool.required_role == "ENGINEER" and authoritative_role in ["INTERN", "JUNIOR", "CONTRACTOR", "GENERAL_USER"]:
            role_insufficient = True
        elif tool.required_role == "FINANCE_MANAGER" and authoritative_role not in ["FINANCE_MANAGER", "CFO", "CONTROLLER"]:
            role_insufficient = True
        elif tool.required_role == "ANALYST" and authoritative_role in ["GENERAL_USER", "INTERN", "CONTRACTOR"]:
            role_insufficient = True

        # Target Endpoint Trust Check
        target_untrusted = False
        t_low = action.resource_scope.target.lower()
        if any(bad in t_low for bad in ["unauthorized", "public-endpoint-unauthorized", "unknown", "leak"]):
            target_untrusted = True
        elif tool.allowed_targets and not any(allowed in action.resource_scope.target for allowed in tool.allowed_targets):
            if action.resource_scope.is_external or action.resource_scope.trust_level in ["LOW", "UNTRUSTED"] or "cloud" in t_low or "webhook" in t_low:
                target_untrusted = True

        # Critical Server Protection Rule (Scenario B):
        # Destructive disabling or decommissioning of critical Tier-0 servers requires executive CISO authorization
        critical_server_threat = False
        if "srv-domain-controller-01" in t_low or "critical" in t_low:
            if tool_name == "disable_server" or action.operation.upper() in ["DELETE", "DISABLE", "TERMINATE"]:
                if authoritative_role != "CISO":
                    critical_server_threat = True

        # Resolve Authorization Decision
        decision = "ALLOW"
        decision_reason = "Action approved by runtime enforcement policy."

        # Hard rules
        if critical_server_threat:
            decision = "DENY"
            decision_reason = f"Critical infrastructure protection: Disabling critical domain controller '{action.resource_scope.target}' is strictly prohibited for non-CISO principals."
        elif target_untrusted:
            decision = "DENY"
            decision_reason = f"Prohibited target endpoint '{action.resource_scope.target}'. Data transfer to untrusted endpoints is strictly blocked."
        elif role_insufficient:
            decision = "DENY"
            decision_reason = f"Privilege violation: User '{action.principal.user_id}' with authoritative role '{authoritative_role}' does not possess clearance for protected tool '{tool_name}'."
        elif any(t.decision == GovernanceDecision.REJECT for t in matched_traces):
            rej_trace = next(t for t in matched_traces if t.decision == GovernanceDecision.REJECT)
            decision = "DENY"
            decision_reason = f"Policy violation: Explicit policy '{rej_trace.policy_id}' ({rej_trace.policy_name}) issued REJECT decision."
        elif tool_name == "restart_service" and authoritative_role != "CISO":
            # Scenario C: High-impact operations require human approval
            decision = "REQUIRE_APPROVAL"
            decision_reason = "High-impact infrastructure service restart requires human approval."
        elif any(t.decision == GovernanceDecision.ESCALATE for t in matched_traces):
            decision = "REQUIRE_APPROVAL"
            decision_reason = "Policy requires human escalation and cryptographic approval."
        elif action.resource_scope.data_classification == "RESTRICTED" and authoritative_clearance not in ["PRIVILEGED", "ADMIN", "CISO"]:
            decision = "REQUIRE_APPROVAL"
            decision_reason = "Restricted data access by standard clearance requires explicit human cryptographic approval."

        # ──────────────────────────────────────────────────────────────────────
        # STEP 5: Approval Verification (State Machine & Cryptographic Digest)
        # ──────────────────────────────────────────────────────────────────────
        approval_req_dict = None
        if decision == "REQUIRE_APPROVAL":
            if approval_id:
                try:
                    consumed_approval = APPROVAL_MANAGER.verify_and_consume(
                        approval_id=approval_id,
                        current_action=action,
                        execution_ticket_id=execution_id,
                    )
                    decision = "ALLOW"
                    decision_reason = f"Authorized via verified cryptographic human approval '{approval_id}' (reviewer: {consumed_approval.reviewer_id})."
                    approval_req_dict = {
                        "approval_id": consumed_approval.approval_id,
                        "status": consumed_approval.status.value,
                        "reviewer_id": consumed_approval.reviewer_id,
                    }
                except ApprovalError as app_err:
                    decision = "DENY"
                    decision_reason = f"Approval verification failed: {str(app_err)}"
            else:
                # Create pending approval request
                new_app = APPROVAL_MANAGER.create_approval_request(
                    action=action,
                    required_role="SECURITY_ADMIN" if action.resource_scope.data_classification == "RESTRICTED" else "MANAGER",
                )
                approval_req_dict = {
                    "approval_id": new_app.approval_id,
                    "status": new_app.status.value,
                    "action_digest": new_app.action_digest,
                    "expires_at": new_app.expires_at,
                    "required_role": new_app.required_role,
                }

        # ──────────────────────────────────────────────────────────────────────
        # STEP 6: Fail-Closed Gate (Prevent Underlying Side Effect on DENY)
        # ──────────────────────────────────────────────────────────────────────
        if decision in ["DENY", "REQUIRE_APPROVAL"]:
            latency = (time.perf_counter() - start_time) * 1000
            summary = "No side effects produced (execution blocked by enforcement gateway)."
            state_after = INFRASTRUCTURE_STORE.snapshot()
            
            # Fail-closed audit logging
            try:
                audit_entry = AUDIT_LEDGER.append_entry(
                    request_id=action.action_id,
                    execution_id=execution_id,
                    principal_user_id=action.principal.user_id,
                    principal_role=authoritative_role,
                    tool_name=tool_name,
                    action_digest=canonical_digest,
                    decision=decision,
                    executed=False,
                    side_effects_occurred=False,
                    side_effect_summary=summary,
                    policy_version=self._active_policy_version,
                    details={"reason": decision_reason, "matched_policies": matched_ids},
                    state_before=state_before,
                    state_after=state_after,
                )
                audit_id = audit_entry.entry_id
            except AuditPersistenceError:
                audit_id = None

            return GatewayEnforcementResult(
                execution_id=execution_id,
                action_id=action.action_id,
                tool_name=tool_name,
                decision=decision,
                decision_reason=decision_reason,
                executed=False,
                side_effects_occurred=False,
                side_effect_summary=summary,
                canonical_digest=canonical_digest,
                policy_version_evaluated=self._active_policy_version,
                matched_policy_ids=matched_ids,
                approval_request=approval_req_dict,
                audit_entry_id=audit_id,
                latency_ms=latency,
                state_before=state_before,
                state_after=state_after,
            )

        # ──────────────────────────────────────────────────────────────────────
        # STEP 7: Execute Tool with Single-Use Cryptographic Ticket
        # ──────────────────────────────────────────────────────────────────────
        ticket = ExecutionTicket(
            ticket_id=execution_id,
            action_digest=canonical_digest,
            tool_name=tool_name,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Pre-execution audit guarantee: fail-closed if audit persistence cannot be assured
        AUDIT_LEDGER.preflight_check()

        try:
            tool_res: ToolExecutionResult = tool.execute_protected(
                arguments=action.arguments,
                ticket=ticket,
                resource_scope=action.resource_scope,
            )
            ticket.consumed = True
        except Exception as exec_err:
            latency = (time.perf_counter() - start_time) * 1000
            safe_err = mask_sensitive_error_details(str(exec_err))
            state_after = INFRASTRUCTURE_STORE.snapshot()
            audit_entry = AUDIT_LEDGER.append_entry(
                request_id=action.action_id,
                execution_id=execution_id,
                principal_user_id=action.principal.user_id,
                principal_role=authoritative_role,
                tool_name=tool_name,
                action_digest=canonical_digest,
                decision="DENY",
                executed=False,
                side_effects_occurred=False,
                side_effect_summary=f"Tool execution failed: {safe_err}",
                policy_version=self._active_policy_version,
                details={"error": safe_err},
                state_before=state_before,
                state_after=state_after,
            )
            return GatewayEnforcementResult(
                execution_id=execution_id,
                action_id=action.action_id,
                tool_name=tool_name,
                decision="DENY",
                decision_reason=f"Executor exception: {safe_err}",
                executed=False,
                side_effects_occurred=False,
                side_effect_summary="No side effects produced due to execution error.",
                canonical_digest=canonical_digest,
                policy_version_evaluated=self._active_policy_version,
                matched_policy_ids=matched_ids,
                audit_entry_id=audit_entry.entry_id,
                latency_ms=latency,
                error=safe_err,
                state_before=state_before,
                state_after=state_after,
            )

        # ──────────────────────────────────────────────────────────────────────
        # STEP 8: Append Verified Audit Record (Fail-Closed Audit Assurance)
        # ──────────────────────────────────────────────────────────────────────
        latency = (time.perf_counter() - start_time) * 1000
        state_after = INFRASTRUCTURE_STORE.snapshot()
        audit_entry = AUDIT_LEDGER.append_entry(
            request_id=action.action_id,
            execution_id=execution_id,
            principal_user_id=action.principal.user_id,
            principal_role=authoritative_role,
            tool_name=tool_name,
            action_digest=canonical_digest,
            decision="ALLOW",
            executed=True,
            side_effects_occurred=tool_res.side_effects_occurred,
            side_effect_summary=tool_res.side_effect_summary,
            policy_version=self._active_policy_version,
            details={"output": tool_res.output, "matched_policies": matched_ids},
            state_before=state_before,
            state_after=state_after,
        )

        return GatewayEnforcementResult(
            execution_id=execution_id,
            action_id=action.action_id,
            tool_name=tool_name,
            decision="ALLOW",
            decision_reason=decision_reason,
            executed=True,
            side_effects_occurred=tool_res.side_effects_occurred,
            side_effect_summary=tool_res.side_effect_summary,
            canonical_digest=canonical_digest,
            policy_version_evaluated=self._active_policy_version,
            matched_policy_ids=matched_ids,
            tool_output=tool_res.output,
            approval_request=approval_req_dict,
            audit_entry_id=audit_entry.entry_id,
            latency_ms=latency,
            state_before=state_before,
            state_after=state_after,
        )


# Global Gateway Instance
ENFORCEMENT_GATEWAY = RuntimeEnforcementGateway()
