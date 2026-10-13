"""CyberForge Approval State Machine & Cryptographic Action Binding.

Binds approval decisions directly to a cryptographic digest of the canonical action,
preventing argument mutation, replay attacks, policy version mismatch, and expired approvals.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import hashlib
import hmac
import os
import uuid
from typing import Any, Dict, Optional
from agents.enforcement.canonical_action import CanonicalAction


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CONSUMED = "CONSUMED"


class ApprovalError(Exception):
    """Base error for approval validation failures."""
    pass


class ApprovalNotFoundError(ApprovalError):
    pass


class ApprovalExpiredError(ApprovalError):
    pass


class ApprovalAlreadyConsumedError(ApprovalError):
    pass


class ApprovalDigestMismatchError(ApprovalError):
    """Raised when the action has been modified after approval was granted."""
    pass


class ApprovalPolicyVersionMismatchError(ApprovalError):
    """Raised when policy changed between approval creation and execution."""
    pass


class ApprovalInvalidSignatureError(ApprovalError):
    pass


class ApprovalUnauthorizedReviewerError(ApprovalError):
    pass


APPROVAL_SIGNING_KEY = os.getenv("CYBERFORGE_APPROVAL_KEY", "cyberforge-secure-hmac-key-2026").encode("utf-8")


@dataclass
class ApprovalRequest:
    approval_id: str
    action_digest: str
    action_payload: Dict[str, Any]
    principal_user_id: str
    principal_role: str
    required_role: str
    policy_version: int
    created_at: str
    expires_at: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    reviewer_id: Optional[str] = None
    reviewer_comments: Optional[str] = None
    reviewed_at: Optional[str] = None
    signature: str = ""
    consumed_at: Optional[str] = None
    execution_ticket_id: Optional[str] = None

    def compute_signature(self) -> str:
        """Computes HMAC-SHA256 signature binding the approval state."""
        msg = f"{self.approval_id}|{self.action_digest}|{self.principal_user_id}|{self.policy_version}|{self.expires_at}|{self.status.value}"
        return hmac.new(APPROVAL_SIGNING_KEY, msg.encode("utf-8"), hashlib.sha256).hexdigest()

    def is_expired(self) -> bool:
        exp = datetime.fromisoformat(self.expires_at)
        return datetime.now(timezone.utc) > exp


class ApprovalManager:
    """Manages creation, review, verification, and consumption of action approvals."""

    def __init__(self):
        self._approvals: Dict[str, ApprovalRequest] = {}

    def create_approval_request(
        self,
        action: CanonicalAction,
        required_role: str = "SECURITY_ADMIN",
        ttl_minutes: int = 15,
    ) -> ApprovalRequest:
        """Creates and stores a cryptographic approval request for a canonical action."""
        approval_id = f"APP-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(minutes=ttl_minutes)).isoformat()
        digest = action.compute_digest()

        req = ApprovalRequest(
            approval_id=approval_id,
            action_digest=digest,
            action_payload=action.to_canonical_dict(),
            principal_user_id=action.principal.user_id,
            principal_role=action.principal.role,
            required_role=required_role,
            policy_version=action.policy_version,
            created_at=now.isoformat(),
            expires_at=expires_at,
            status=ApprovalStatus.PENDING,
        )
        req.signature = req.compute_signature()
        self._approvals[approval_id] = req
        return req

    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        return self._approvals.get(approval_id)

    def review_approval(
        self,
        approval_id: str,
        reviewer_id: str,
        reviewer_role: str,
        decision: str,  # "APPROVED" or "REJECTED"
        comments: str = "",
    ) -> ApprovalRequest:
        """Processes reviewer decision with authorization and expiration checks."""
        req = self._approvals.get(approval_id)
        if not req:
            raise ApprovalNotFoundError(f"Approval request '{approval_id}' not found.")

        # Check expiration
        if req.is_expired():
            req.status = ApprovalStatus.EXPIRED
            req.signature = req.compute_signature()
            raise ApprovalExpiredError(f"Approval request '{approval_id}' has expired.")

        if req.status != ApprovalStatus.PENDING:
            raise ApprovalError(f"Approval '{approval_id}' cannot be reviewed in status {req.status.value}")

        # Reviewer role clearance verification
        if req.required_role in ["SECURITY_ADMIN", "CISO", "MANAGER"]:
            if reviewer_role not in ["SECURITY_ADMIN", "CISO", "MANAGER", "ADMIN"]:
                raise ApprovalUnauthorizedReviewerError(
                    f"Reviewer '{reviewer_id}' with role '{reviewer_role}' lacks required clearance '{req.required_role}'"
                )

        now_str = datetime.now(timezone.utc).isoformat()
        req.reviewer_id = reviewer_id
        req.reviewer_comments = comments
        req.reviewed_at = now_str

        if decision.upper() == "APPROVED":
            req.status = ApprovalStatus.APPROVED
        else:
            req.status = ApprovalStatus.REJECTED

        req.signature = req.compute_signature()
        return req

    def verify_and_consume(
        self,
        approval_id: str,
        current_action: CanonicalAction,
        execution_ticket_id: str,
    ) -> ApprovalRequest:
        """Verifies that an approval is valid, unmodified, unexpired, and consumes it single-use."""
        req = self._approvals.get(approval_id)
        if not req:
            raise ApprovalNotFoundError(f"Approval reference '{approval_id}' not found.")

        # 1. Replay check
        if req.status == ApprovalStatus.CONSUMED:
            raise ApprovalAlreadyConsumedError(
                f"REPLAY ATTACK PREVENTED: Approval '{approval_id}' was already consumed at {req.consumed_at}."
            )

        # 2. Expiration check
        if req.is_expired() or req.status == ApprovalStatus.EXPIRED:
            req.status = ApprovalStatus.EXPIRED
            raise ApprovalExpiredError(f"Approval '{approval_id}' expired at {req.expires_at}.")

        # 3. Status check
        if req.status != ApprovalStatus.APPROVED:
            raise ApprovalError(f"Approval '{approval_id}' is in status '{req.status.value}', expected 'APPROVED'.")

        # 4. Canonical digest verification (detects argument mutation, tool substitution, scope changes)
        current_digest = current_action.compute_digest()
        if current_digest != req.action_digest:
            raise ApprovalDigestMismatchError(
                f"TAMPERING DETECTED: Proposed action digest ({current_digest}) does not match approved digest ({req.action_digest}). "
                f"Action was modified after authorization!"
            )

        # 5. Policy version consistency
        if current_action.policy_version != req.policy_version:
            raise ApprovalPolicyVersionMismatchError(
                f"POLICY DRIFT: Action policy version ({current_action.policy_version}) differs from approved policy version ({req.policy_version}). "
                f"Action must be re-evaluated against the active policy."
            )

        # 6. Consume approval (atomic single-use)
        req.status = ApprovalStatus.CONSUMED
        req.consumed_at = datetime.now(timezone.utc).isoformat()
        req.execution_ticket_id = execution_ticket_id
        req.signature = req.compute_signature()
        return req

    def list_approvals(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for a in self._approvals.values():
            if status and a.status.value != status.upper():
                continue
            # Auto-update expired items
            if a.status == ApprovalStatus.PENDING and a.is_expired():
                a.status = ApprovalStatus.EXPIRED
                a.signature = a.compute_signature()

            results.append({
                "approval_id": a.approval_id,
                "action_digest": a.action_digest,
                "principal_user_id": a.principal_user_id,
                "principal_role": a.principal_role,
                "required_role": a.required_role,
                "policy_version": a.policy_version,
                "created_at": a.created_at,
                "expires_at": a.expires_at,
                "status": a.status.value,
                "reviewer_id": a.reviewer_id,
                "reviewer_comments": a.reviewer_comments,
                "reviewed_at": a.reviewed_at,
                "consumed_at": a.consumed_at,
                "is_expired": a.is_expired(),
            })
        return sorted(results, key=lambda x: x["created_at"], reverse=True)


# Global approval manager
APPROVAL_MANAGER = ApprovalManager()
