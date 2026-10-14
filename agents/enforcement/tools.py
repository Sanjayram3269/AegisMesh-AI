"""CyberForge Protected Tool Registry & Execution Defense.

Every protected tool contains execution boundaries that prevent direct invocation.
Tools maintain stateful side-effect logs that prove whether an action reached
the underlying executor or was blocked.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any, Callable, Dict, List, Optional, Set

from agents.enforcement.tickets import ExecutionTicket
from agents.enforcement.infrastructure_state import INFRASTRUCTURE_STORE


class DirectExecutionBypassError(PermissionError):
    """Raised when an attempt is made to invoke a protected tool without a valid gateway ticket."""
    pass


class ToolSchemaValidationError(ValueError):
    """Raised when tool arguments fail strict schema validation."""
    pass


@dataclass
class ToolExecutionResult:
    success: bool
    output: Any
    side_effects_occurred: bool
    side_effect_summary: str
    tool_name: str
    execution_id: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error: Optional[str] = None


@dataclass
class SideEffectLogEntry:
    tool_name: str
    operation: str
    target: str
    details: Dict[str, Any]
    execution_id: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ProtectedToolBase:
    """Base class for all protected tools with execution boundary enforcement."""

    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        required_role: str = "STANDARD",
        data_sensitivity: str = "INTERNAL",
        allowed_targets: Optional[List[str]] = None,
        schema: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.description = description
        self.version = version
        self.required_role = required_role
        self.data_sensitivity = data_sensitivity
        self.allowed_targets = allowed_targets or []
        self.schema = schema or {}
        self.side_effects: List[SideEffectLogEntry] = []
        self._execution_count: int = 0

    @property
    def side_effect_count(self) -> int:
        return len(self.side_effects)

    def validate_schema(self, arguments: Dict[str, Any]) -> None:
        """Strict server-side validation of tool arguments against schema."""
        if not self.schema:
            return

        required_fields: List[str] = self.schema.get("required", [])
        for field in required_fields:
            if field not in arguments:
                raise ToolSchemaValidationError(
                    f"Tool '{self.name}' missing required argument: '{field}'"
                )

        properties: Dict[str, Any] = self.schema.get("properties", {})
        for key, val in arguments.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type == "string" and not isinstance(val, str):
                    raise ToolSchemaValidationError(
                        f"Argument '{key}' must be string, got {type(val).__name__}"
                    )
                elif expected_type == "number" and not isinstance(val, (int, float)):
                    raise ToolSchemaValidationError(
                        f"Argument '{key}' must be numeric, got {type(val).__name__}"
                    )
                elif expected_type == "integer" and not isinstance(val, int):
                    raise ToolSchemaValidationError(
                        f"Argument '{key}' must be int, got {type(val).__name__}"
                    )
                elif expected_type == "boolean" and not isinstance(val, bool):
                    raise ToolSchemaValidationError(
                        f"Argument '{key}' must be bool, got {type(val).__name__}"
                    )
                elif expected_type == "array" and not isinstance(val, list):
                    raise ToolSchemaValidationError(
                        f"Argument '{key}' must be list, got {type(val).__name__}"
                    )
                elif expected_type == "object" and not isinstance(val, dict):
                    raise ToolSchemaValidationError(
                        f"Argument '{key}' must be dict, got {type(val).__name__}"
                    )

    def execute_protected(
        self,
        arguments: Dict[str, Any],
        ticket: Any,
        resource_scope: Any,
    ) -> ToolExecutionResult:
        """Internal execution method called ONLY by the gateway after validation."""
        if ticket is None:
            raise DirectExecutionBypassError(
                f"SECURITY VIOLATION: Tool '{self.name}' invocation rejected. "
                f"Direct execution bypass prevented: Missing authoritative ExecutionTicket."
            )
        if not hasattr(ticket, "verify"):
            raise DirectExecutionBypassError(
                f"SECURITY VIOLATION: Tool '{self.name}' invocation rejected. "
                f"Forged or invalid execution ticket type."
            )
        is_valid, reason = ticket.verify(tool_name=self.name)
        if not is_valid:
            raise DirectExecutionBypassError(
                f"SECURITY VIOLATION: Execution ticket verification failed ({reason}). Action blocked."
            )
        ticket.consumed = True
        self.validate_schema(arguments)
        self._execution_count += 1
        return self._do_execute(arguments, ticket, resource_scope)

    def execute(self, *args, **kwargs):
        """Direct invocation attempts are strictly blocked."""
        raise DirectExecutionBypassError(
            f"SECURITY VIOLATION: Tool '{self.name}' cannot be invoked directly. "
            f"All protected tools must be routed through RuntimeEnforcementGateway."
        )

    def _do_execute(
        self,
        arguments: Dict[str, Any],
        ticket: Any,
        resource_scope: Any,
    ) -> ToolExecutionResult:
        """Subclasses implement actual tool execution and side effects."""
        raise NotImplementedError

    def reset_state(self):
        """Clears side-effect logs for testing and evaluation."""
        self.side_effects.clear()
        self._execution_count = 0


# ──────────────────────────────────────────────────────────────────────────────
# Concrete Protected Tools
# ──────────────────────────────────────────────────────────────────────────────

class DatabaseTool(ProtectedToolBase):
    """Executes database queries and mutations with table-level tracking."""

    def __init__(self):
        super().__init__(
            name="database_execute",
            description="Execute SQL operations against enterprise relational database",
            version="1.2.0",
            required_role="ENGINEER",
            data_sensitivity="CONFIDENTIAL",
            allowed_targets=["internal-db", "analytics-warehouse", "staging-db"],
            schema={
                "type": "object",
                "required": ["query", "database"],
                "properties": {
                    "query": {"type": "string"},
                    "database": {"type": "string"},
                    "read_only": {"type": "boolean"},
                },
            },
        )
        self.simulated_tables: Dict[str, List[Dict[str, Any]]] = {
            "customers": [{"id": 1, "name": "Acme Corp", "tier": "Enterprise"}],
            "audit_logs": [{"id": 1, "action": "LOGIN", "status": "OK"}],
            "transactions": [{"id": 101, "amount": 500.0, "currency": "USD"}],
        }

    def _do_execute(
        self,
        arguments: Dict[str, Any],
        ticket: Any,
        resource_scope: Any,
    ) -> ToolExecutionResult:
        query = arguments.get("query", "")
        db_name = arguments.get("database", "internal-db")
        read_only = arguments.get("read_only", False)

        q_lower = query.lower().strip()
        is_mutation = any(
            q_lower.startswith(op)
            for op in ["insert", "update", "delete", "drop", "truncate", "alter"]
        )

        log_entry = SideEffectLogEntry(
            tool_name=self.name,
            operation="MUTATION" if is_mutation else "QUERY",
            target=db_name,
            details={"query": query, "is_mutation": is_mutation, "read_only": read_only},
            execution_id=getattr(ticket, "ticket_id", str(uuid.uuid4())),
        )
        self.side_effects.append(log_entry)

        summary = (
            f"Executed mutation query on database '{db_name}'"
            if is_mutation
            else f"Executed read query on database '{db_name}'"
        )

        return ToolExecutionResult(
            success=True,
            output={"rows_affected": 1 if is_mutation else 5, "database": db_name},
            side_effects_occurred=is_mutation,
            side_effect_summary=summary,
            tool_name=self.name,
            execution_id=getattr(ticket, "ticket_id", ""),
        )


class CustomerDataExportTool(ProtectedToolBase):
    """Exports customer datasets to specified internal or external destinations."""

    def __init__(self):
        super().__init__(
            name="customer_data_export",
            description="Export customer records or analytics datasets to target endpoint",
            version="1.1.0",
            required_role="ANALYST",
            data_sensitivity="RESTRICTED",
            allowed_targets=["approved-internal-analytics", "approved-analytics-service"],
            schema={
                "type": "object",
                "required": ["dataset", "destination", "format"],
                "properties": {
                    "dataset": {"type": "string"},
                    "destination": {"type": "string"},
                    "format": {"type": "string"},
                    "anonymize_pii": {"type": "boolean"},
                },
            },
        )

    def _do_execute(
        self,
        arguments: Dict[str, Any],
        ticket: Any,
        resource_scope: Any,
    ) -> ToolExecutionResult:
        dataset = arguments["dataset"]
        dest = arguments["destination"]
        fmt = arguments["format"]
        anonymize = arguments.get("anonymize_pii", False)

        log_entry = SideEffectLogEntry(
            tool_name=self.name,
            operation="DATA_EXPORT",
            target=dest,
            details={
                "dataset": dataset,
                "destination": dest,
                "format": fmt,
                "anonymize_pii": anonymize,
                "records_exported": 1500,
            },
            execution_id=getattr(ticket, "ticket_id", str(uuid.uuid4())),
        )
        self.side_effects.append(log_entry)

        summary = f"Exported {dataset} (1500 records) to {dest} in {fmt} format (anonymized={anonymize})"
        return ToolExecutionResult(
            success=True,
            output={"records_exported": 1500, "destination": dest, "anonymized": anonymize},
            side_effects_occurred=True,
            side_effect_summary=summary,
            tool_name=self.name,
            execution_id=getattr(ticket, "ticket_id", ""),
        )


class CloudResourceDeployTool(ProtectedToolBase):
    """Provisions or updates cloud infrastructure resources."""

    def __init__(self):
        super().__init__(
            name="cloud_resource_deploy",
            description="Deploy or configure cloud services, API gateways, and serverless infrastructure",
            version="2.0.0",
            required_role="ENGINEER",
            data_sensitivity="CONFIDENTIAL",
            allowed_targets=["staging-api-gateway", "test-cluster", "production-api-gateway"],
            schema={
                "type": "object",
                "required": ["resource_name", "environment", "config"],
                "properties": {
                    "resource_name": {"type": "string"},
                    "environment": {"type": "string"},
                    "config": {"type": "object"},
                },
            },
        )

    def _do_execute(
        self,
        arguments: Dict[str, Any],
        ticket: Any,
        resource_scope: Any,
    ) -> ToolExecutionResult:
        res_name = arguments["resource_name"]
        env = arguments["environment"]

        log_entry = SideEffectLogEntry(
            tool_name=self.name,
            operation="INFRASTRUCTURE_DEPLOY",
            target=env,
            details={"resource_name": res_name, "environment": env, "config": arguments["config"]},
            execution_id=getattr(ticket, "ticket_id", str(uuid.uuid4())),
        )
        self.side_effects.append(log_entry)

        summary = f"Successfully deployed resource '{res_name}' to environment '{env}'"
        return ToolExecutionResult(
            success=True,
            output={"resource_id": f"res-{uuid.uuid4().hex[:8]}", "status": "DEPLOYED", "environment": env},
            side_effects_occurred=True,
            side_effect_summary=summary,
            tool_name=self.name,
            execution_id=getattr(ticket, "ticket_id", ""),
        )


class PaymentTransferTool(ProtectedToolBase):
    """Executes high-value financial transfers and payouts."""

    def __init__(self):
        super().__init__(
            name="payment_transfer",
            description="Initiate electronic funds transfer or customer financial payout",
            version="1.0.0",
            required_role="FINANCE_MANAGER",
            data_sensitivity="RESTRICTED",
            allowed_targets=["approved-treasury", "payroll-gateway"],
            schema={
                "type": "object",
                "required": ["recipient_account", "amount", "currency", "purpose"],
                "properties": {
                    "recipient_account": {"type": "string"},
                    "amount": {"type": "number"},
                    "currency": {"type": "string"},
                    "purpose": {"type": "string"},
                },
            },
        )

    def _do_execute(
        self,
        arguments: Dict[str, Any],
        ticket: Any,
        resource_scope: Any,
    ) -> ToolExecutionResult:
        recipient = arguments["recipient_account"]
        amount = arguments["amount"]
        currency = arguments["currency"]
        purpose = arguments["purpose"]

        log_entry = SideEffectLogEntry(
            tool_name=self.name,
            operation="FUNDS_TRANSFER",
            target=recipient,
            details={"recipient": recipient, "amount": amount, "currency": currency, "purpose": purpose},
            execution_id=getattr(ticket, "ticket_id", str(uuid.uuid4())),
        )
        self.side_effects.append(log_entry)

        summary = f"Transferred {amount} {currency} to account '{recipient}' for purpose: {purpose}"
        return ToolExecutionResult(
            success=True,
            output={"transaction_id": f"TX-{uuid.uuid4().hex[:10].upper()}", "amount": amount, "currency": currency},
            side_effects_occurred=True,
            side_effect_summary=summary,
            tool_name=self.name,
            execution_id=getattr(ticket, "ticket_id", ""),
        )


class SystemConfigUpdateTool(ProtectedToolBase):
    """Modifies access control, authentication, or network security rules."""

    def __init__(self):
        super().__init__(
            name="system_config_update",
            description="Update core security, authorization, or firewall configuration parameters",
            version="1.3.0",
            required_role="ADMIN",
            data_sensitivity="RESTRICTED",
            allowed_targets=["security-policy-engine", "identity-service", "firewall-rules"],
            schema={
                "type": "object",
                "required": ["parameter", "new_value", "subsystem"],
                "properties": {
                    "parameter": {"type": "string"},
                    "new_value": {"type": "string"},
                    "subsystem": {"type": "string"},
                },
            },
        )

    def _do_execute(
        self,
        arguments: Dict[str, Any],
        ticket: Any,
        resource_scope: Any,
    ) -> ToolExecutionResult:
        param = arguments["parameter"]
        val = arguments["new_value"]
        sub = arguments["subsystem"]

        log_entry = SideEffectLogEntry(
            tool_name=self.name,
            operation="CONFIG_UPDATE",
            target=sub,
            details={"parameter": param, "new_value": val, "subsystem": sub},
            execution_id=getattr(ticket, "ticket_id", str(uuid.uuid4())),
        )
        self.side_effects.append(log_entry)

        summary = f"Updated parameter '{param}' in subsystem '{sub}' to '{val}'"
        return ToolExecutionResult(
            success=True,
            output={"parameter": param, "subsystem": sub, "updated": True},
            side_effects_occurred=True,
            side_effect_summary=summary,
            tool_name=self.name,
            execution_id=getattr(ticket, "ticket_id", ""),
        )


class ExternalWebhookTool(ProtectedToolBase):
    """Sends outbound HTTP webhook notifications or data payloads."""

    def __init__(self):
        super().__init__(
            name="external_webhook_call",
            description="Send outbound HTTP webhook notification to registered partner endpoints",
            version="1.0.0",
            required_role="ANALYST",
            data_sensitivity="INTERNAL",
            allowed_targets=["https://api.partner.example.com/webhook", "https://hooks.slack.com/services/internal"],
            schema={
                "type": "object",
                "required": ["url", "payload"],
                "properties": {
                    "url": {"type": "string"},
                    "payload": {"type": "object"},
                    "headers": {"type": "object"},
                },
            },
        )

    def _do_execute(
        self,
        arguments: Dict[str, Any],
        ticket: Any,
        resource_scope: Any,
    ) -> ToolExecutionResult:
        url = arguments["url"]
        payload = arguments["payload"]

        log_entry = SideEffectLogEntry(
            tool_name=self.name,
            operation="WEBHOOK_POST",
            target=url,
            details={"url": url, "payload_keys": list(payload.keys())},
            execution_id=getattr(ticket, "ticket_id", str(uuid.uuid4())),
        )
        self.side_effects.append(log_entry)

        summary = f"Dispatched webhook notification to '{url}' with {len(payload)} payload keys"
        return ToolExecutionResult(
            success=True,
            output={"status_code": 200, "url": url, "delivered": True},
            side_effects_occurred=True,
            side_effect_summary=summary,
            tool_name=self.name,
            execution_id=getattr(ticket, "ticket_id", ""),
        )


class IsolateHostTool(ProtectedToolBase):
    """Network-isolates a compromised endpoint or server (SOC Active Response)."""

    def __init__(self):
        super().__init__(
            name="isolate_host",
            description="Network-isolate compromised endpoint or server (SOC Active Response)",
            version="1.0.0",
            required_role="ANALYST",
            data_sensitivity="INTERNAL",
            allowed_targets=["host-workstation-42", "srv-linux-app-02", "endpoint-dmz-01", "srv-domain-controller-01"],
            schema={
                "type": "object",
                "required": ["hostname", "isolation_mode"],
                "properties": {
                    "hostname": {"type": "string"},
                    "isolation_mode": {"type": "string", "enum": ["FULL", "SELECTIVE", "FORENSIC_ONLY"]},
                    "allow_dns": {"type": "boolean"},
                },
            },
        )
        self.is_reversible = True

    def _do_execute(
        self,
        arguments: Dict[str, Any],
        ticket: Any,
        resource_scope: Any,
    ) -> ToolExecutionResult:
        hostname = arguments["hostname"]
        mode = arguments.get("isolation_mode", "FULL")

        infra_res = INFRASTRUCTURE_STORE.isolate_host(hostname=hostname, isolation_mode=mode)
        log_entry = SideEffectLogEntry(
            tool_name=self.name,
            operation="ISOLATE_HOST",
            target=hostname,
            details={"hostname": hostname, "isolation_mode": mode, "is_reversible": True, "infra_state": infra_res},
            execution_id=getattr(ticket, "ticket_id", str(uuid.uuid4())),
        )
        self.side_effects.append(log_entry)

        summary = f"Network isolated host '{hostname}' with mode '{mode}' (Reversible)"
        return ToolExecutionResult(
            success=True,
            output={"hostname": hostname, "isolated": True, "mode": mode, "reversible": True, "infra_result": infra_res},
            side_effects_occurred=True,
            side_effect_summary=summary,
            tool_name=self.name,
            execution_id=getattr(ticket, "ticket_id", ""),
        )


class DisableAccountTool(ProtectedToolBase):
    """Disables a compromised user or service account in Identity Directory (SOC Active Response)."""

    def __init__(self):
        super().__init__(
            name="disable_account",
            description="Disable compromised user or service account (SOC Active Response)",
            version="1.0.0",
            required_role="ANALYST",
            data_sensitivity="INTERNAL",
            allowed_targets=["corp-directory", "identity-provider-main", "azure-ad-prod", "user_john_doe", "john_doe"],
            schema={
                "type": "object",
                "required": ["username", "reason"],
                "properties": {
                    "username": {"type": "string"},
                    "reason": {"type": "string"},
                    "revoke_sessions": {"type": "boolean"},
                },
            },
        )
        self.is_reversible = True

    def _do_execute(
        self,
        arguments: Dict[str, Any],
        ticket: Any,
        resource_scope: Any,
    ) -> ToolExecutionResult:
        username = arguments["username"]
        reason = arguments["reason"]

        infra_res = INFRASTRUCTURE_STORE.disable_user_account(username=username, reason=reason)
        log_entry = SideEffectLogEntry(
            tool_name=self.name,
            operation="DISABLE_ACCOUNT",
            target=username,
            details={"username": username, "reason": reason, "is_reversible": True, "infra_state": infra_res},
            execution_id=getattr(ticket, "ticket_id", str(uuid.uuid4())),
        )
        self.side_effects.append(log_entry)

        summary = f"Disabled identity account '{username}' (Reason: {reason}) (Reversible)"
        return ToolExecutionResult(
            success=True,
            output={"username": username, "account_disabled": True, "reversible": True, "infra_result": infra_res},
            side_effects_occurred=True,
            side_effect_summary=summary,
            tool_name=self.name,
            execution_id=getattr(ticket, "ticket_id", ""),
        )


class BlockIPTool(ProtectedToolBase):
    """Applies firewall/gateway rule to drop traffic from adversarial IP (SOC Active Response)."""

    def __init__(self):
        super().__init__(
            name="block_ip",
            description="Block malicious IP at perimeter edge firewall (SOC Active Response)",
            version="1.0.0",
            required_role="ANALYST",
            data_sensitivity="INTERNAL",
            allowed_targets=["edge-firewall", "cloud-waf-cluster", "perimeter-security-group"],
            schema={
                "type": "object",
                "required": ["ip_address"],
                "properties": {
                    "ip_address": {"type": "string"},
                    "direction": {"type": "string", "enum": ["INBOUND", "OUTBOUND", "BOTH"]},
                    "duration_minutes": {"type": "integer"},
                },
            },
        )
        self.is_reversible = True

    def _do_execute(
        self,
        arguments: Dict[str, Any],
        ticket: Any,
        resource_scope: Any,
    ) -> ToolExecutionResult:
        ip_addr = arguments["ip_address"]
        direction = arguments.get("direction", "BOTH")

        infra_res = INFRASTRUCTURE_STORE.block_network_destination(destination=ip_addr, direction=direction)
        log_entry = SideEffectLogEntry(
            tool_name=self.name,
            operation="BLOCK_IP",
            target=ip_addr,
            details={"ip_address": ip_addr, "direction": direction, "is_reversible": True, "infra_state": infra_res},
            execution_id=getattr(ticket, "ticket_id", str(uuid.uuid4())),
        )
        self.side_effects.append(log_entry)

        summary = f"Blocked IP address '{ip_addr}' in perimeter firewall (Direction: {direction})"
        return ToolExecutionResult(
            success=True,
            output={"ip_address": ip_addr, "traffic_blocked": True, "direction": direction, "infra_result": infra_res},
            side_effects_occurred=True,
            side_effect_summary=summary,
            tool_name=self.name,
            execution_id=getattr(ticket, "ticket_id", ""),
        )


class RestartServiceTool(ProtectedToolBase):
    """Restarts a high-impact infrastructure service on a designated server."""

    def __init__(self):
        super().__init__(
            name="restart_service",
            description="Restart high-impact infrastructure service on server",
            version="1.0.0",
            required_role="ENGINEER",
            data_sensitivity="RESTRICTED",
            allowed_targets=["srv-domain-controller-01", "srv-linux-app-02", "staging-api-gateway"],
            schema={
                "type": "object",
                "required": ["service_name", "server_id"],
                "properties": {
                    "service_name": {"type": "string"},
                    "server_id": {"type": "string"},
                },
            },
        )

    def _do_execute(
        self,
        arguments: Dict[str, Any],
        ticket: Any,
        resource_scope: Any,
    ) -> ToolExecutionResult:
        svc = arguments["service_name"]
        srv = arguments["server_id"]

        infra_res = INFRASTRUCTURE_STORE.restart_service(service_name=svc, server_id=srv)
        log_entry = SideEffectLogEntry(
            tool_name=self.name,
            operation="RESTART_SERVICE",
            target=srv,
            details={"service_name": svc, "server_id": srv, "infra_state": infra_res},
            execution_id=getattr(ticket, "ticket_id", str(uuid.uuid4())),
        )
        self.side_effects.append(log_entry)

        summary = f"Restarted service '{svc}' on server '{srv}'"
        return ToolExecutionResult(
            success=True,
            output={"service": svc, "server": srv, "status": "RESTARTED", "infra_result": infra_res},
            side_effects_occurred=True,
            side_effect_summary=summary,
            tool_name=self.name,
            execution_id=getattr(ticket, "ticket_id", ""),
        )


class DisableServerTool(ProtectedToolBase):
    """DESTRUCTIVE: Decommissions or powers off a server."""

    def __init__(self):
        super().__init__(
            name="disable_server",
            description="Decommission or disable server infrastructure (Destructive)",
            version="1.0.0",
            required_role="CISO",
            data_sensitivity="RESTRICTED",
            allowed_targets=["srv-linux-app-02", "staging-api-gateway"],
            schema={
                "type": "object",
                "required": ["server_id", "reason"],
                "properties": {
                    "server_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        )

    def _do_execute(
        self,
        arguments: Dict[str, Any],
        ticket: Any,
        resource_scope: Any,
    ) -> ToolExecutionResult:
        srv = arguments["server_id"]
        reason = arguments.get("reason", "")

        infra_res = INFRASTRUCTURE_STORE.disable_critical_server(server_id=srv, reason=reason)
        log_entry = SideEffectLogEntry(
            tool_name=self.name,
            operation="DISABLE_SERVER",
            target=srv,
            details={"server_id": srv, "reason": reason, "infra_state": infra_res},
            execution_id=getattr(ticket, "ticket_id", str(uuid.uuid4())),
        )
        self.side_effects.append(log_entry)

        summary = f"Disabled server '{srv}' (Reason: {reason})"
        return ToolExecutionResult(
            success=True,
            output={"server_id": srv, "status": "OFFLINE", "infra_result": infra_res},
            side_effects_occurred=True,
            side_effect_summary=summary,
            tool_name=self.name,
            execution_id=getattr(ticket, "ticket_id", ""),
        )


# Global Tool Registry
TOOL_REGISTRY: Dict[str, ProtectedToolBase] = {
    "database_execute": DatabaseTool(),
    "customer_data_export": CustomerDataExportTool(),
    "cloud_resource_deploy": CloudResourceDeployTool(),
    "payment_transfer": PaymentTransferTool(),
    "system_config_update": SystemConfigUpdateTool(),
    "external_webhook_call": ExternalWebhookTool(),
    "isolate_host": IsolateHostTool(),
    "disable_account": DisableAccountTool(),
    "block_ip": BlockIPTool(),
    "restart_service": RestartServiceTool(),
    "disable_server": DisableServerTool(),
}


def get_tool(name: str) -> Optional[ProtectedToolBase]:
    return TOOL_REGISTRY.get(name)


def reset_all_tool_side_effects():
    for tool in TOOL_REGISTRY.values():
        tool.reset_state()
    INFRASTRUCTURE_STORE.reset()


def get_total_side_effect_count() -> int:
    return sum(tool.side_effect_count for tool in TOOL_REGISTRY.values())

