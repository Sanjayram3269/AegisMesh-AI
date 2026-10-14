"""CyberForge Cryptographic Execution Ticket.

Issues single-use, time-bound, cryptographically signed execution tickets
from the Runtime Enforcement Gateway to protected tool executors.
Executors verify ticket signature, action digest binding, and consumption status
to prevent bypass, replay, and argument alteration attacks.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import os
from typing import Optional, Tuple

GATEWAY_SIGNING_KEY = os.getenv("CYBERFORGE_GATEWAY_KEY", "cyberforge-gateway-ticket-key-2026").encode("utf-8")


@dataclass
class ExecutionTicket:
    ticket_id: str
    action_digest: str
    tool_name: str
    created_at: str
    ttl_seconds: int = 30
    consumed: bool = False
    signature: str = ""

    def __post_init__(self):
        if not self.signature:
            self.signature = self.compute_signature()

    def compute_signature(self) -> str:
        msg = f"{self.ticket_id}|{self.action_digest}|{self.tool_name}|{self.created_at}|{self.ttl_seconds}"
        return hmac.new(GATEWAY_SIGNING_KEY, msg.encode("utf-8"), hashlib.sha256).hexdigest()

    def is_expired(self) -> bool:
        try:
            created = datetime.fromisoformat(self.created_at)
            return (datetime.now(timezone.utc) - created).total_seconds() > self.ttl_seconds
        except Exception:
            return True

    def verify(self, tool_name: Optional[str] = None, expected_digest: Optional[str] = None) -> Tuple[bool, str]:
        if self.consumed:
            return False, "Ticket has already been consumed (single-use enforcement)"
        if self.is_expired():
            return False, "Ticket has expired"
        if tool_name and self.tool_name != tool_name:
            return False, f"Ticket bound to tool '{self.tool_name}', not '{tool_name}'"
        if expected_digest and self.action_digest != expected_digest:
            return False, f"Ticket bound to digest '{self.action_digest}', not '{expected_digest}'"
        expected_sig = self.compute_signature()
        if not hmac.compare_digest(self.signature, expected_sig):
            return False, "Cryptographic ticket signature verification failed"
        return True, "Valid"
