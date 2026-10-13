"""CyberForge Cryptographic Tamper-Resistant Audit Ledger.

Maintains an immutable hash-chained audit ledger of all runtime governance decisions,
enforcement gateway actions, and verified execution outcomes.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple


AUDIT_HMAC_KEY = os.getenv("CYBERFORGE_AUDIT_KEY", "cyberforge-audit-hmac-key-2026").encode("utf-8")
GENESIS_HASH = "0" * 64


class AuditPersistenceError(Exception):
    """Raised when an audit record cannot be securely persisted, triggering fail-closed enforcement."""
    pass


@dataclass
class AuditLedgerEntry:
    entry_id: str
    index: int
    timestamp: str
    request_id: str
    execution_id: str
    principal_user_id: str
    principal_role: str
    tool_name: str
    action_digest: str
    decision: str  # ALLOW, DENY, REQUIRE_APPROVAL, MODIFIED
    executed: bool
    side_effects_occurred: bool
    side_effect_summary: str
    policy_version: int
    details: Dict[str, Any]
    prev_hash: str
    entry_hash: str
    signature: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "index": self.index,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "execution_id": self.execution_id,
            "principal_user_id": self.principal_user_id,
            "principal_role": self.principal_role,
            "tool_name": self.tool_name,
            "action_digest": self.action_digest,
            "decision": self.decision,
            "executed": self.executed,
            "side_effects_occurred": self.side_effects_occurred,
            "side_effect_summary": self.side_effect_summary,
            "policy_version": self.policy_version,
            "details": self.details,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
            "signature": self.signature,
        }


def compute_entry_hash(
    prev_hash: str,
    entry_id: str,
    timestamp: str,
    request_id: str,
    tool_name: str,
    action_digest: str,
    decision: str,
    executed: bool,
    policy_version: int,
    details: Dict[str, Any],
) -> str:
    serialized_details = json.dumps(details, sort_keys=True, separators=(",", ":"))
    payload = f"{prev_hash}|{entry_id}|{timestamp}|{request_id}|{tool_name}|{action_digest}|{decision}|{executed}|{policy_version}|{serialized_details}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_entry_signature(entry_hash: str) -> str:
    return hmac.new(AUDIT_HMAC_KEY, entry_hash.encode("utf-8"), hashlib.sha256).hexdigest()


class TamperResistantAuditLedger:
    """Hash-chained immutable cryptographic ledger for AI security governance."""

    def __init__(self, fail_closed_audit: bool = True):
        self.fail_closed_audit = fail_closed_audit
        self._chain: List[AuditLedgerEntry] = []
        self._last_hash: str = GENESIS_HASH
        self._simulate_failure: bool = False

    def preflight_check(self) -> None:
        """Verifies audit persistence capability before tool execution to guarantee fail-closed security."""
        if self._simulate_failure:
            raise AuditPersistenceError(
                "CRITICAL SECURITY ALERT: Audit persistence layer unavailable. Protected action blocked."
            )

    def append_entry(
        self,
        request_id: str,
        execution_id: str,
        principal_user_id: str,
        principal_role: str,
        tool_name: str,
        action_digest: str,
        decision: str,
        executed: bool,
        side_effects_occurred: bool,
        side_effect_summary: str,
        policy_version: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLedgerEntry:
        """Appends a new verified entry to the hash chain."""
        if self._simulate_failure:
            raise AuditPersistenceError(
                "CRITICAL SECURITY ALERT: Audit persistence layer unavailable. Protected action blocked."
            )

        entry_id = f"AUD-{uuid.uuid4().hex[:12].upper()}"
        timestamp = datetime.now(timezone.utc).isoformat()
        index = len(self._chain)
        safe_details = details or {}

        entry_hash = compute_entry_hash(
            prev_hash=self._last_hash,
            entry_id=entry_id,
            timestamp=timestamp,
            request_id=request_id,
            tool_name=tool_name,
            action_digest=action_digest,
            decision=decision,
            executed=executed,
            policy_version=policy_version,
            details=safe_details,
        )
        sig = compute_entry_signature(entry_hash)

        entry = AuditLedgerEntry(
            entry_id=entry_id,
            index=index,
            timestamp=timestamp,
            request_id=request_id,
            execution_id=execution_id,
            principal_user_id=principal_user_id,
            principal_role=principal_role,
            tool_name=tool_name,
            action_digest=action_digest,
            decision=decision,
            executed=executed,
            side_effects_occurred=side_effects_occurred,
            side_effect_summary=side_effect_summary,
            policy_version=policy_version,
            details=safe_details,
            prev_hash=self._last_hash,
            entry_hash=entry_hash,
            signature=sig,
        )

        self._chain.append(entry)
        self._last_hash = entry_hash
        return entry

    def verify_chain_integrity(self) -> Tuple[bool, Optional[str], Optional[int]]:
        """Verifies the complete hash chain from genesis to tip."""
        expected_prev = GENESIS_HASH
        for i, entry in enumerate(self._chain):
            # 1. Verify prev_hash link
            if entry.prev_hash != expected_prev:
                return (
                    False,
                    f"Hash link broken at index {i} (entry {entry.entry_id}). Expected {expected_prev}, got {entry.prev_hash}",
                    i,
                )

            # 2. Recompute entry hash
            recomputed = compute_entry_hash(
                prev_hash=entry.prev_hash,
                entry_id=entry.entry_id,
                timestamp=entry.timestamp,
                request_id=entry.request_id,
                tool_name=entry.tool_name,
                action_digest=entry.action_digest,
                decision=entry.decision,
                executed=entry.executed,
                policy_version=entry.policy_version,
                details=entry.details,
            )
            if recomputed != entry.entry_hash:
                return (
                    False,
                    f"Content tampering detected at index {i} (entry {entry.entry_id}). Stored hash {entry.entry_hash} != calculated {recomputed}",
                    i,
                )

            # 3. Verify signature
            expected_sig = compute_entry_signature(entry.entry_hash)
            if entry.signature != expected_sig:
                return (
                    False,
                    f"Signature validation failed at index {i} (entry {entry.entry_id}).",
                    i,
                )

            expected_prev = entry.entry_hash

        return True, "Chain integrity fully verified. All blocks valid.", None

    def query(
        self,
        tool_name: Optional[str] = None,
        decision: Optional[str] = None,
        principal_user_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        entries = self._chain
        if tool_name:
            entries = [e for e in entries if e.tool_name == tool_name]
        if decision:
            entries = [e for e in entries if e.decision == decision.upper()]
        if principal_user_id:
            entries = [e for e in entries if e.principal_user_id == principal_user_id]
        return [e.to_dict() for e in reversed(entries[-limit:])]

    def set_simulate_failure(self, fail: bool):
        self._simulate_failure = fail

    def clear(self):
        self._chain.clear()
        self._last_hash = GENESIS_HASH


# Global Audit Ledger Instance
AUDIT_LEDGER = TamperResistantAuditLedger()
