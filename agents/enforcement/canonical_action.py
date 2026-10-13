"""CyberForge Canonical Action Representation & Validation Layer.

Guarantees that the exact action evaluated by the governance policy engine
is mathematically identical to the action that reaches the tool executor.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PrincipalIdentity:
    user_id: str
    role: str
    tenant_id: str = "default"
    clearance_level: str = "STANDARD"  # STANDARD, PRIVILEGED, ADMIN, CISO
    authorization_token: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "role": self.role,
            "tenant_id": self.tenant_id,
            "clearance_level": self.clearance_level,
        }


@dataclass(frozen=True)
class ResourceScope:
    target: str
    environment: str = "GENERAL"  # PRODUCTION, STAGING, TEST, INTERNAL, GENERAL
    trust_level: str = "MEDIUM"   # HIGH, MEDIUM, LOW, UNTRUSTED
    data_classification: str = "INTERNAL"  # PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    is_external: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "environment": self.environment,
            "trust_level": self.trust_level,
            "data_classification": self.data_classification,
            "is_external": self.is_external,
        }


def canonicalize_arguments(args: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sort and normalize arguments to ensure deterministic JSON representation."""
    if not isinstance(args, dict):
        return args
    normalized = {}
    for key in sorted(args.keys()):
        val = args[key]
        if isinstance(val, dict):
            normalized[key] = canonicalize_arguments(val)
        elif isinstance(val, list):
            normalized[key] = [
                canonicalize_arguments(item) if isinstance(item, dict) else item
                for item in val
            ]
        elif isinstance(val, float):
            # Normalize float representation
            normalized[key] = round(val, 6)
        else:
            normalized[key] = val
    return normalized


@dataclass
class CanonicalAction:
    action_id: str
    principal: PrincipalIdentity
    tool_name: str
    tool_version: str
    operation: str  # READ, WRITE, EXECUTE, DELETE, TRANSFER, DEPLOY
    resource_scope: ResourceScope
    arguments: Dict[str, Any] = field(default_factory=dict)
    policy_version: int = 1
    approval_reference: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        # Enforce canonical arguments
        object.__setattr__(
            self, "arguments", canonicalize_arguments(self.arguments)
        )

    def to_canonical_dict(self) -> Dict[str, Any]:
        """Produces canonical dictionary suitable for cryptographic hashing."""
        return {
            "principal": self.principal.to_dict(),
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "operation": self.operation.upper(),
            "resource_scope": self.resource_scope.to_dict(),
            "arguments": canonicalize_arguments(self.arguments),
            "policy_version": self.policy_version,
            "approval_reference": self.approval_reference or "",
        }

    def canonical_json(self) -> str:
        """Returns deterministic, space-minimized JSON string with sorted keys."""
        return json.dumps(
            self.to_canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

    def compute_digest(self) -> str:
        """Computes SHA-256 cryptographic digest of canonical action representation."""
        payload = self.canonical_json().encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def verify_digest(self, expected_digest: str) -> bool:
        """Verifies if the current action state matches an expected digest."""
        return self.compute_digest() == expected_digest
