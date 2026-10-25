"""Zero-Expertise Cyber Defense prototype API.

The seeded records and response actions in this module are explicitly simulated.
They demonstrate the workflow; they do not ingest live telemetry or modify real
accounts, endpoints, email, or network controls.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/defense", tags=["Zero-Expertise Cyber Defense"])
_lock = RLock()


def _seed_incidents() -> dict[str, dict]:
    now = datetime.now(timezone.utc)
    records = [
        {
            "id": "INC-1001", "title": "Unusual sign-in to a staff account",
            "category": "Account access", "severity": "high", "confidence": "medium",
            "status": "needs_attention", "source": "Identity alert (simulated)",
            "asset": "Front-desk staff account", "organization": "Community clinic demo",
            "occurred_at": (now - timedelta(minutes=8)).isoformat(),
            "event_count": 7, "group_key": "login-failures-frontdesk",
            "what_happened": "Several unsuccessful sign-ins were followed by a successful sign-in from a new location.",
            "why_it_matters": "If the sign-in was not made by the staff member, someone else may be able to access organization information.",
            "evidence": ["7 failed sign-ins in 4 minutes", "A successful sign-in followed", "The location is new for this account"],
            "recommended_action": "Confirm the activity with the staff member using a trusted contact method. If they do not recognize it, request account containment.",
            "action_label": "Request account containment", "action_kind": "account_containment",
            "requires_approval": True, "last_action": None,
            "limitations": "Demo evidence only; no identity provider is connected."
        },
        {
            "id": "INC-1002", "title": "Email may be trying to steal a password",
            "category": "Suspicious email", "severity": "medium", "confidence": "high",
            "status": "needs_attention", "source": "Email security alert (simulated)",
            "asset": "Shared reception mailbox", "organization": "Community clinic demo",
            "occurred_at": (now - timedelta(minutes=23)).isoformat(),
            "event_count": 3, "group_key": "phishing-shared-mailbox",
            "what_happened": "A message asks the recipient to sign in through a link that does not match the claimed sender's organization.",
            "why_it_matters": "The link could lead to a fake sign-in page designed to collect a password.",
            "evidence": ["Sender and link domains do not match", "Message uses urgent account language", "No click is confirmed in this demo"],
            "recommended_action": "Do not open the link or reply. Report the message to the person responsible for IT or security.",
            "action_label": "Mark as reviewed", "action_kind": "review",
            "requires_approval": False, "last_action": None,
            "limitations": "Demo evidence only; email contents have not been fetched from a mailbox."
        },
        {
            "id": "INC-1003", "title": "A workstation may be infected",
            "category": "Device alert", "severity": "high", "confidence": "medium",
            "status": "needs_attention", "source": "Endpoint alert (simulated)",
            "asset": "Reception workstation WS-03", "organization": "Community clinic demo",
            "occurred_at": (now - timedelta(minutes=41)).isoformat(),
            "event_count": 2, "group_key": "endpoint-ws03",
            "what_happened": "A security tool reported a suspicious program starting on a reception workstation.",
            "why_it_matters": "If the alert is genuine, the device could put shared files or accounts at risk.",
            "evidence": ["Suspicious process alert received", "Related alert on the same device", "No forensic scan is connected in this demo"],
            "recommended_action": "Ask the designated support person to verify the alert. Avoid using the device for sensitive work until it is checked.",
            "action_label": "Request support review", "action_kind": "support_review",
            "requires_approval": True, "last_action": None,
            "limitations": "Demo event; no endpoint agent is connected and no real device can be isolated."
        },
        {
            "id": "INC-1004", "title": "Repeated login failures grouped together",
            "category": "Account access", "severity": "low", "confidence": "high",
            "status": "reviewed", "source": "Identity alert (simulated)",
            "asset": "Staff portal", "organization": "Community clinic demo",
            "occurred_at": (now - timedelta(hours=2)).isoformat(),
            "event_count": 12, "group_key": "staff-portal-failures",
            "what_happened": "Twelve failed sign-ins from one short time window have been grouped into one incident.",
            "why_it_matters": "This may be a typing mistake or an attempted password guess. The available evidence does not establish which.",
            "evidence": ["12 failed attempts in 6 minutes", "No successful sign-in in this event group"],
            "recommended_action": "Check whether the staff member had trouble signing in. Escalate if the activity is unfamiliar or repeats.",
            "action_label": "Reopen incident", "action_kind": "review",
            "requires_approval": False, "last_action": "Reviewed by demo administrator",
            "limitations": "Demo event; no live identity data is available."
        },
    ]
    return {item["id"]: item for item in records}


_INCIDENTS = _seed_incidents()


class ResponseRequest(BaseModel):
    action: Literal["acknowledge", "request_approval", "simulate_containment", "support_review"]
    note: Optional[str] = Field(default=None, max_length=500)


@router.get("/summary")
def get_defense_summary():
    """Summary metrics are calculated only from the current demo incident set."""
    with _lock:
        items = list(_INCIDENTS.values())
        needs_attention = sum(i["status"] == "needs_attention" for i in items)
        high_priority = sum(i["severity"] == "high" and i["status"] != "closed" for i in items)
        grouped_events = sum(max(0, i["event_count"] - 1) for i in items)
        return {
            "mode": "SIMULATION",
            "telemetry_connected": False,
            "coverage_message": "Demo incidents only — no live security sources are connected.",
            "incident_count": len(items),
            "needs_attention": needs_attention,
            "high_priority": high_priority,
            "events_grouped": grouped_events,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/incidents")
def list_defense_incidents(
    severity: Optional[Literal["low", "medium", "high", "critical"]] = None,
    status_filter: Optional[Literal["needs_attention", "reviewed", "pending_approval", "pending_support", "contained_simulated", "closed"]] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None, max_length=100),
):
    """Return deduplicated incident groups with plain-language guidance."""
    with _lock:
        items = list(_INCIDENTS.values())
        if severity:
            items = [i for i in items if i["severity"] == severity]
        if status_filter:
            items = [i for i in items if i["status"] == status_filter]
        if search:
            needle = search.casefold()
            items = [i for i in items if needle in " ".join([
                i["title"], i["category"], i["asset"], i["what_happened"]
            ]).casefold()]
        rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        items.sort(key=lambda i: (i["status"] != "needs_attention", rank[i["severity"]], i["occurred_at"]))
        return {"mode": "SIMULATION", "total": len(items), "incidents": deepcopy(items)}


@router.post("/incidents/{incident_id}/response")
def respond_to_incident(incident_id: str, request: ResponseRequest):
    """Record a demo response; no real-world protective action is executed."""
    with _lock:
        incident = _INCIDENTS.get(incident_id)
        if incident is None:
            raise HTTPException(status_code=404, detail="Incident not found.")
        if request.action == "simulate_containment":
            if incident["action_kind"] not in ("account_containment", "device_containment"):
                raise HTTPException(status_code=400, detail="This incident does not support containment in the demo.")
            if incident["requires_approval"]:
                incident["status"] = "pending_approval"
                incident["last_action"] = "Containment requested; awaiting authorized approval"
                return {
                    "ok": True, "mode": "SIMULATION", "status": incident["status"],
                    "message": "This action is high-impact and requires an authorized reviewer. No containment was executed."
                }
            incident["status"] = "contained_simulated"
            incident["last_action"] = "Simulated containment only — no connected system was changed"
            return {
                "ok": True, "mode": "SIMULATION", "status": incident["status"],
                "message": "Demo state updated only. No real account, device, email, or network setting was changed."
            }
        if request.action == "request_approval":
            incident["status"] = "pending_approval"
            incident["last_action"] = "Approval requested; no action executed"
            return {"ok": True, "mode": "SIMULATION", "status": incident["status"],
                    "message": "Approval request recorded in the demo. No action was executed."}
        if request.action == "support_review":
            incident["status"] = "pending_support"
            incident["last_action"] = request.note or "Support review requested in demo"
            return {"ok": True, "mode": "SIMULATION", "status": incident["status"],
                    "message": "Support review request recorded. The incident remains open; the underlying threat is not marked resolved."}
        if request.action == "acknowledge":
            incident["status"] = "reviewed"
            incident["last_action"] = request.note or "Marked reviewed by demo user"
            return {"ok": True, "mode": "SIMULATION", "status": incident["status"],
                    "message": "Review recorded in the demo. This does not mean the underlying threat is resolved."}
        raise HTTPException(status_code=400, detail="Unsupported response action.")


@router.post("/demo/reset")
def reset_defense_demo():
    """Reset demo incidents to their seeded state."""
    global _INCIDENTS
    with _lock:
        _INCIDENTS = _seed_incidents()
        return {"ok": True, "mode": "SIMULATION", "message": "Demo incidents reset.", "incident_count": len(_INCIDENTS)}
