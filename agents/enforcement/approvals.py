"""CyberForge Approval State Machine & Cryptographic Action Binding.

Binds approval decisions directly to a cryptographic digest of the canonical action,
preventing argument mutation, replay attacks, policy version mismatch, and expired approvals.
Supports thread-safe atomic single-use consumption, cryptographic HMAC signatures,
revocation, and durable database persistence across server restarts.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import hashlib
import hmac
import json
import logging
import os
import threading
import uuid
from typing import Any, Dict, List, Optional
from agents.enforcement.canonical_action import CanonicalAction

logger = logging.getLogger("cyberforge.approvals")


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CONSUMED = "CONSUMED"
    REVOKED = "REVOKED"


class ApprovalError(Exception):
    """Base error for approval validation failures."""
    pass


class ApprovalNotFoundError(ApprovalError):
    pass


class ApprovalExpiredError(ApprovalError):
    pass


class ApprovalAlreadyConsumedError(ApprovalError):
    pass


class ApprovalRevokedError(ApprovalError):
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
    """Manages creation, review, verification, and consumption of action approvals.
    
    Guarantees thread-safe atomic single-use consumption and persistent SQLite storage.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._approvals: Dict[str, ApprovalRequest] = {}
        self._load_from_db()

    def _get_db_session(self):
        try:
            from app.database.db import SessionLocal
            return SessionLocal()
        except Exception:
            return None

    def _load_from_db(self):
        """Loads historical approvals from database if available."""
        session = self._get_db_session()
        if not session:
            return
        try:
            from app.database.models import DBCyberForgeApproval
            records = session.query(DBCyberForgeApproval).all()
            for rec in records:
                try:
                    payload = json.loads(rec.action_payload_json) if rec.action_payload_json else {}
                except Exception:
                    payload = {}
                req = ApprovalRequest(
                    approval_id=rec.approval_id,
                    action_digest=rec.action_digest,
                    action_payload=payload,
                    principal_user_id=rec.principal_user_id,
                    principal_role=rec.principal_role,
                    required_role=rec.required_role,
                    policy_version=rec.policy_version,
                    created_at=rec.created_at,
                    expires_at=rec.expires_at,
                    status=ApprovalStatus(rec.status),
                    reviewer_id=rec.reviewer_id,
                    reviewer_comments=rec.reviewer_comments,
                    reviewed_at=rec.reviewed_at,
                    signature=rec.signature,
                    consumed_at=rec.consumed_at,
                    execution_ticket_id=rec.execution_ticket_id,
                )
                self._approvals[req.approval_id] = req
        except Exception as e:
            logger.warning(f"Could not load approvals from DB: {e}")
        finally:
            session.close()

    def _persist_to_db(self, req: ApprovalRequest):
        """Persists or updates approval in SQLite database."""
        session = self._get_db_session()
        if not session:
            return
        try:
            from app.database.models import DBCyberForgeApproval
            db_rec = session.query(DBCyberForgeApproval).filter_by(approval_id=req.approval_id).first()
            if not db_rec:
                db_rec = DBCyberForgeApproval(
                    approval_id=req.approval_id,
                    action_digest=req.action_digest,
                    action_payload_json=json.dumps(req.action_payload),
                    principal_user_id=req.principal_user_id,
                    principal_role=req.principal_role,
                    required_role=req.required_role,
                    policy_version=req.policy_version,
                    created_at=req.created_at,
                    expires_at=req.expires_at,
                    status=req.status.value,
                    reviewer_id=req.reviewer_id,
                    reviewer_comments=req.reviewer_comments,
                    reviewed_at=req.reviewed_at,
                    signature=req.signature,
                    consumed_at=req.consumed_at,
                    execution_ticket_id=req.execution_ticket_id,
                )
                session.add(db_rec)
            else:
                db_rec.status = req.status.value
                db_rec.reviewer_id = req.reviewer_id
                db_rec.reviewer_comments = req.reviewer_comments
                db_rec.reviewed_at = req.reviewed_at
                db_rec.signature = req.signature
                db_rec.consumed_at = req.consumed_at
                db_rec.execution_ticket_id = req.execution_ticket_id
            session.commit()
        except Exception as e:
            logger.warning(f"Could not persist approval to DB: {e}")
        finally:
            session.close()

    def create_approval_request(
        self,
        action: CanonicalAction,
        required_role: str = "SECURITY_ADMIN",
        ttl_minutes: int = 15,
    ) -> ApprovalRequest:
        """Creates and stores a cryptographic approval request for a canonical action."""
        with self._lock:
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
            self._persist_to_db(req)
            return req

    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        with self._lock:
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
        with self._lock:
            req = self._approvals.get(approval_id)
            if not req:
                raise ApprovalNotFoundError(f"Approval request '{approval_id}' not found.")

            # Check expiration
            if req.is_expired():
                req.status = ApprovalStatus.EXPIRED
                req.signature = req.compute_signature()
                self._persist_to_db(req)
                raise ApprovalExpiredError(f"Approval request '{approval_id}' has expired.")

            if req.status == ApprovalStatus.REVOKED:
                raise ApprovalRevokedError(f"Approval request '{approval_id}' has been revoked.")

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
            self._persist_to_db(req)
            return req

    def revoke_approval(
        self,
        approval_id: str,
        reviewer_id: str,
        reviewer_role: str,
        reason: str = "Administrative revocation",
    ) -> ApprovalRequest:
        """Revokes a previously issued approval request before or after review."""
        with self._lock:
            req = self._approvals.get(approval_id)
            if not req:
                raise ApprovalNotFoundError(f"Approval request '{approval_id}' not found.")

            if reviewer_role not in ["ADMIN", "CISO", "SECURITY_ADMIN"]:
                raise ApprovalUnauthorizedReviewerError(
                    f"User '{reviewer_id}' lacks authorization to revoke approvals."
                )

            if req.status == ApprovalStatus.CONSUMED:
                raise ApprovalAlreadyConsumedError(
                    f"Approval '{approval_id}' was already consumed and cannot be revoked retroactively."
                )

            req.status = ApprovalStatus.REVOKED
            req.reviewer_comments = f"REVOKED by {reviewer_id} ({reviewer_role}): {reason}"
            req.signature = req.compute_signature()
            self._persist_to_db(req)
            return req

    def verify_and_consume(
        self,
        approval_id: str,
        current_action: CanonicalAction,
        execution_ticket_id: str,
    ) -> ApprovalRequest:
        """Atomically verifies that an approval is valid, unmodified, unexpired, and consumes it single-use."""
        with self._lock:
            req = self._approvals.get(approval_id)
            if not req:
                raise ApprovalNotFoundError(f"Approval reference '{approval_id}' not found.")

            # 1. Revocation check
            if req.status == ApprovalStatus.REVOKED:
                raise ApprovalRevokedError(f"Approval '{approval_id}' has been revoked.")

            # 2. Replay check (Atomic single-use guarantee)
            if req.status == ApprovalStatus.CONSUMED:
                raise ApprovalAlreadyConsumedError(
                    f"REPLAY ATTACK PREVENTED: Approval '{approval_id}' was already consumed at {req.consumed_at}."
                )

            # 3. Expiration check
            if req.is_expired() or req.status == ApprovalStatus.EXPIRED:
                req.status = ApprovalStatus.EXPIRED
                self._persist_to_db(req)
                raise ApprovalExpiredError(f"Approval '{approval_id}' expired at {req.expires_at}.")

            # 4. Status check
            if req.status != ApprovalStatus.APPROVED:
                raise ApprovalError(f"Approval '{approval_id}' is in status '{req.status.value}', expected 'APPROVED'.")

            # 5. Canonical digest verification (detects argument mutation, tool substitution, scope changes)
            current_digest = current_action.compute_digest()
            if current_digest != req.action_digest:
                raise ApprovalDigestMismatchError(
                    f"TAMPERING DETECTED: Proposed action digest ({current_digest}) does not match approved digest ({req.action_digest}). "
                    f"Action was modified after authorization!"
                )

            # 6. Policy version consistency
            if current_action.policy_version != req.policy_version:
                raise ApprovalPolicyVersionMismatchError(
                    f"POLICY DRIFT: Action policy version ({current_action.policy_version}) differs from approved policy version ({req.policy_version}). "
                    f"Action must be re-evaluated against the active policy."
                )

            # 7. Consume approval (atomic single-use transition)
            req.status = ApprovalStatus.CONSUMED
            req.consumed_at = datetime.now(timezone.utc).isoformat()
            req.execution_ticket_id = execution_ticket_id
            req.signature = req.compute_signature()
            self._persist_to_db(req)
            return req

    def list_approvals(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
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

    def clear(self):
        """Clears in-memory approval table for test suites."""
        with self._lock:
            self._approvals.clear()


# Global approval manager
APPROVAL_MANAGER = ApprovalManager()
