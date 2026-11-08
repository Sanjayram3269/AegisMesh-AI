"""Authoritative operations gateway. The model is always outside this boundary."""

import csv
import hashlib
import hmac
import io
import json
import secrets
import time
import uuid
from agents.enforcement.canonical_action import (
    CanonicalAction,
    PrincipalIdentity,
    ResourceScope,
)
from .models import Action, SAFE_FIELDS, evaluate, evidence
from .store import Store, compact, now


POLICY_VERSION = 1


class Operations:
    def __init__(self, store=None):
        self.store = store or Store()

    def canonical(self, user, action):
        return CanonicalAction(
            action_id="OPS",
            principal=PrincipalIdentity(user_id=user["username"], role=user["role"]),
            tool_name=action.tool,
            tool_version="1",
            operation="READ" if action.tool == "tickets.list" else "WRITE",
            resource_scope=ResourceScope(
                target=action.destination, environment="CONTROLLED_LAB"
            ),
            arguments=action.model_dump(),
            policy_version=POLICY_VERSION,
        )

    def propose(self, user, action, explanation, provider):
        proposal_id = "PROP-" + uuid.uuid4().hex[:16]
        decision, risk, reason = evaluate(action, user["role"])
        with self.store.transaction() as db:
            db.execute(
                "INSERT INTO proposals VALUES(?,?,?,?,?,?,?)",
                (
                    proposal_id,
                    user["username"],
                    compact(action.model_dump()),
                    explanation,
                    compact(provider),
                    now(),
                    time.time() + 900,
                ),
            )
        alternative = (
            Action(tool="reports.export", fields=SAFE_FIELDS).model_dump()
            if action.tool == "reports.export" and decision != "ALLOW"
            else None
        )
        return {
            "id": proposal_id,
            "action": action.model_dump(),
            "decision": decision,
            "risk": risk,
            "reason": reason,
            "evidence": evidence(action),
            "canonical_digest": self.canonical(user, action).compute_digest(),
            "alternative": alternative,
            "expires_in": 900,
        }

    def record(self, db, user, result):
        result["id"] = "RUN-" + uuid.uuid4().hex[:16]
        result["created_at"] = now()
        result["audit_hash"] = self.store.append_audit(
            db, {k: v for k, v in result.items() if k != "output"}
        )
        db.execute(
            "INSERT INTO receipts VALUES(?,?,?,?)",
            (result["id"], user["username"], compact(result), result["created_at"]),
        )
        return result

    def execute(self, user, proposal_id, override=None, approval_id=None):
        start = time.perf_counter()
        with self.store.transaction() as db:
            integrity = self.store.verify_audit(db)
            if not integrity["valid"]:
                raise ValueError(
                    "Audit integrity failed. Execution is disabled until the local ledger is investigated."
                )
            row = db.execute(
                "SELECT * FROM proposals WHERE id=?", (proposal_id,)
            ).fetchone()
            if not row:
                raise LookupError("Proposal not found.")
            if row["owner"] != user["username"]:
                raise PermissionError(
                    "Only the requesting account may execute its proposal."
                )
            if row["expires"] < time.time():
                raise ValueError("Proposal expired. Submit the request again.")
            original = Action.model_validate_json(row["payload"])
            action = override or original
            canonical = self.canonical(user, action)
            action_digest = canonical.compute_digest()
            decision, risk, reason = evaluate(action, user["role"])
            result = {
                "proposal_id": proposal_id,
                "requester": user["username"],
                "action": action.model_dump(),
                "decision": decision,
                "risk": risk,
                "reason": reason,
                "canonical_digest": action_digest,
                "policy_version": POLICY_VERSION,
                "evidence": evidence(action),
                "executed": False,
                "verified": False,
                "side_effects": False,
                "output": None,
                "approval_id": approval_id,
                "provider": json.loads(row["provider"]),
            }
            # Even changes to a less-sensitive operation must not reuse an old approval.
            if action.model_dump() != original.model_dump():
                decision, reason = (
                    "DENY",
                    "The submitted arguments differ from this proposal. Create a fresh proposal; an approval cannot authorize altered arguments.",
                )
            if db.execute(
                "SELECT 1 FROM metadata WHERE key=?", ("DONE-" + proposal_id,)
            ).fetchone():
                decision, reason = (
                    "DENY",
                    "This proposal already executed. Replays are blocked; submit a new request for new work.",
                )
            if approval_id:
                approval = db.execute(
                    "SELECT * FROM approvals WHERE id=?", (approval_id,)
                ).fetchone()
                if not approval or approval["owner"] != user["username"]:
                    decision, reason = (
                        "DENY",
                        "Approval does not belong to this requester.",
                    )
                elif (
                    approval["action_digest"] != action_digest
                    or approval["policy_version"] != POLICY_VERSION
                ):
                    decision, reason = (
                        "DENY",
                        "Approval digest or policy version mismatch. The exact approved action has changed.",
                    )
                elif (
                    approval["status"] != "APPROVED"
                    or approval["expires"] < time.time()
                ):
                    decision, reason = (
                        "DENY",
                        f"Approval is {approval['status'].lower()} or expired; it cannot be used.",
                    )
                elif decision != "DENY":
                    db.execute(
                        "UPDATE approvals SET status='CONSUMED' WHERE id=? AND status='APPROVED'",
                        (approval_id,),
                    )
                    decision, reason = (
                        "ALLOW",
                        "Exact-action approval verified and consumed once.",
                    )
            if decision == "REQUIRE_APPROVAL" and not approval_id:
                approval_id = "APP-" + uuid.uuid4().hex[:16]
                db.execute(
                    "INSERT INTO approvals VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        approval_id,
                        user["username"],
                        action_digest,
                        compact(action.model_dump()),
                        POLICY_VERSION,
                        "PENDING",
                        time.time() + 900,
                        None,
                        "",
                        now(),
                    ),
                )
                result["approval_id"] = approval_id
            if decision == "ALLOW":
                # A single-use ticket is consumed in the same SQLite transaction as the tool.
                ticket_id = "TKT-" + secrets.token_hex(12)
                ticket = {
                    "id": ticket_id,
                    "digest": action_digest,
                    "expires": time.time() + 30,
                }
                signature = hmac.new(
                    self.store.key, compact(ticket).encode(), hashlib.sha256
                ).hexdigest()
                output, verified, side_effects = self._execute_tool(
                    db, user, action, canonical, ticket, signature
                )
                if not verified:
                    raise ValueError(
                        "Result verification failed. The transaction was rolled back without committing business changes."
                    )
                db.execute(
                    "INSERT INTO metadata VALUES(?,?)", ("DONE-" + proposal_id, now())
                )
                result.update(
                    executed=True,
                    verified=verified,
                    side_effects=side_effects,
                    output=output,
                    ticket_id=ticket_id,
                    status="verified" if verified else "verification_failed",
                )
            else:
                result["status"] = (
                    "pending_approval" if decision == "REQUIRE_APPROVAL" else "blocked"
                )
            result.update(
                decision=decision,
                reason=reason,
                gateway_latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )
            return self.record(db, user, result)

    def _execute_tool(self, db, user, action, canonical, ticket, signature):
        expected = hmac.new(
            self.store.key, compact(ticket).encode(), hashlib.sha256
        ).hexdigest()
        # Reconstruct from the actual executor inputs, never trust a caller-provided digest.
        actual_digest = self.canonical(user, action).compute_digest()
        if (
            not hmac.compare_digest(signature, expected)
            or ticket["expires"] < time.time()
            or ticket["digest"] != actual_digest
            or canonical.compute_digest() != actual_digest
        ):
            raise PermissionError("Execution ticket does not match the actual action.")
        if db.execute("SELECT 1 FROM metadata WHERE key=?", (ticket["id"],)).fetchone():
            raise PermissionError("Execution ticket already consumed.")
        db.execute("INSERT INTO metadata VALUES(?,?)", (ticket["id"], now()))
        if action.tool == "tickets.list":
            rows = [
                dict(r)
                for r in db.execute(
                    "SELECT ticket_id,category,status,resolution_hours FROM tickets ORDER BY ticket_id"
                )
            ]
            counts = {
                state: sum(r["status"] == state for r in rows)
                for state in ["open", "in_progress", "resolved"]
            }
            return (
                {
                    "tickets": rows,
                    "summary": counts,
                    "verification": "Read directly from the support database.",
                },
                True,
                False,
            )
        if action.tool == "tickets.update":
            before = db.execute(
                "SELECT status FROM tickets WHERE ticket_id=?", (action.ticket_id,)
            ).fetchone()
            if not before:
                raise LookupError("Ticket not found.")
            db.execute(
                "UPDATE tickets SET status=? WHERE ticket_id=?",
                (action.status, action.ticket_id),
            )
            after = db.execute(
                "SELECT status FROM tickets WHERE ticket_id=?", (action.ticket_id,)
            ).fetchone()[0]
            return (
                {
                    "ticket_id": action.ticket_id,
                    "before": before[0],
                    "after": after,
                    "verification": "Independent SELECT after the UPDATE.",
                },
                after == action.status,
                before[0] != after,
            )
        # Column names are selected only after the fixed allowlist policy check.
        rows = [
            dict(r)
            for r in db.execute(
                "SELECT " + ",".join(action.fields) + " FROM tickets ORDER BY ticket_id"
            )
        ]
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=action.fields)
        writer.writeheader()
        # Preserve literal contact values when a CSV is opened in spreadsheet apps.
        writer.writerows(
            {
                key: (
                    "'" + value
                    if isinstance(value, str)
                    and value.startswith(("=", "+", "-", "@", "\t", "\r"))
                    else value
                )
                for key, value in row.items()
            }
            for row in rows
        )
        content = buffer.getvalue()
        sha = hashlib.sha256(content.encode()).hexdigest()
        export_id = "REPORT-" + uuid.uuid4().hex[:16]
        db.execute(
            "INSERT INTO exports VALUES(?,?,?,?,?,?)",
            (export_id, user["username"], content, compact(action.fields), sha, now()),
        )
        saved = db.execute(
            "SELECT content FROM exports WHERE id=?", (export_id,)
        ).fetchone()[0]
        parsed = list(csv.DictReader(io.StringIO(saved)))
        verified = (
            hashlib.sha256(saved.encode()).hexdigest() == sha
            and len(parsed) == len(rows)
            and list(next(iter(parsed), {}).keys()) == action.fields
        )
        return (
            {
                "export_id": export_id,
                "rows": len(rows),
                "fields": action.fields,
                "sha256": sha,
                "download_url": f"/api/ops/exports/{export_id}",
                "verification": "Re-read stored CSV; checked SHA-256, columns and row count.",
            },
            verified,
            True,
        )

    def review(self, user, approval_id, decision, comment):
        if user["role"] != "manager":
            raise PermissionError("Only an authenticated manager may review approvals.")
        with self.store.transaction() as db:
            row = db.execute(
                "SELECT * FROM approvals WHERE id=?", (approval_id,)
            ).fetchone()
            if not row:
                raise LookupError("Approval not found.")
            if row["owner"] == user["username"]:
                raise PermissionError("A different manager must review your request.")
            if row["expires"] < time.time():
                raise ValueError("Approval expired. Create a fresh request.")
            allowed = {"PENDING", "APPROVED"} if decision == "REVOKED" else {"PENDING"}
            if row["status"] not in allowed:
                raise ValueError(f"Cannot review an approval in {row['status']} state.")
            db.execute(
                "UPDATE approvals SET status=?,reviewer=?,comment=? WHERE id=?",
                (decision, user["username"], comment, approval_id),
            )
            self.store.append_audit(
                db,
                {
                    "event": "approval_review",
                    "approval_id": approval_id,
                    "decision": decision,
                    "reviewer": user["username"],
                    "action_digest": row["action_digest"],
                    "created_at": now(),
                },
            )
            return {
                "approval_id": approval_id,
                "status": decision,
                "reviewer": user["username"],
            }

    def dashboard(self, user):
        with self.store.transaction() as db:
            rows = db.execute(
                "SELECT payload FROM receipts "
                + ("WHERE owner=? " if user["role"] == "agent" else "")
                + "ORDER BY created DESC LIMIT 60",
                (user["username"],) if user["role"] == "agent" else (),
            ).fetchall()
            receipts = [json.loads(r[0]) for r in rows]
            approvals = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM approvals "
                    + ("WHERE owner=? " if user["role"] == "agent" else "")
                    + "ORDER BY created DESC LIMIT 60",
                    (user["username"],) if user["role"] == "agent" else (),
                )
            ]
            for a in approvals:
                a["action"] = json.loads(a.pop("payload"))
                if a["expires"] < time.time() and a["status"] in {
                    "PENDING",
                    "APPROVED",
                }:
                    a["status"] = "EXPIRED"
            return {
                "receipts": receipts,
                "approvals": approvals,
                "audit": self.store.verify_audit(db),
                "tickets": [
                    dict(r)
                    for r in db.execute(
                        "SELECT ticket_id,category,status,resolution_hours FROM tickets ORDER BY ticket_id"
                    )
                ],
                "metrics": {
                    "scope": "most recent 60 visible execution receipts",
                    "executed": sum(r["executed"] for r in receipts),
                    "blocked": sum(r["decision"] == "DENY" for r in receipts),
                    "verified": sum(r["verified"] for r in receipts),
                    "pending": sum(a["status"] == "PENDING" for a in approvals),
                },
            }

    def export(self, user, export_id):
        with self.store.transaction() as db:
            row = db.execute(
                "SELECT * FROM exports WHERE id=?", (export_id,)
            ).fetchone()
            if not row:
                raise LookupError("Report not found.")
            if row["owner"] != user["username"]:
                raise PermissionError("Only the requester can download this report.")
            if hashlib.sha256(row["content"].encode()).hexdigest() != row["sha256"]:
                raise ValueError("Report integrity verification failed.")
            return dict(row)
