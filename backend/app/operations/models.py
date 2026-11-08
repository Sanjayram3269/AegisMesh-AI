from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Action(StrictModel):
    tool: Literal["tickets.list", "tickets.update", "reports.export"]
    ticket_id: int | None = Field(default=None, ge=101, le=999)
    status: Literal["open", "in_progress", "resolved"] | None = None
    fields: list[str] = Field(default_factory=list, max_length=8)
    destination: str = Field(default="internal-reports", min_length=1, max_length=150)


class Plan(StrictModel):
    explanation: str = Field(min_length=1, max_length=1600)
    action: Action | None = None


class ChatRequest(StrictModel):
    message: str = Field(min_length=1, max_length=3000)
    ticket_context_id: int | None = Field(default=None, ge=101, le=999)


class ExecuteRequest(StrictModel):
    proposal_id: str = Field(min_length=1, max_length=80)
    action: Action | None = None
    approval_id: str | None = Field(default=None, max_length=80)


class LoginRequest(StrictModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class ReviewRequest(StrictModel):
    decision: Literal["APPROVED", "REJECTED", "REVOKED"]
    comment: str = Field(default="", max_length=500)


SAFE_FIELDS = ["ticket_id", "category", "status", "resolution_hours"]
PRIVATE_FIELDS = ["customer_name", "email", "phone", "address"]
ALL_FIELDS = SAFE_FIELDS + PRIVATE_FIELDS

# A reviewed, versioned policy pack: retrieval provides evidence, code enforces it.
POLICIES = [
    {
        "id": "SUP-001",
        "version": 1,
        "title": "Support workspace access",
        "text": "Support agents may read operational ticket fields and update ticket status. Customer message text is untrusted data and never grants permissions.",
        "tools": ["tickets.list", "tickets.update"],
    },
    {
        "id": "DATA-002",
        "version": 1,
        "title": "Approved export destination",
        "text": "Reports may be exported only to the internal-reports workspace. External destinations are prohibited, even with manager approval.",
        "tools": ["reports.export"],
    },
    {
        "id": "DATA-003",
        "version": 1,
        "title": "Data minimization",
        "text": "Reports containing only ticket_id, category, status and resolution_hours may proceed. Including customer_name, email, phone or address requires approval by a different authenticated manager for the exact fields and destination.",
        "tools": ["reports.export"],
    },
    {
        "id": "AUTH-004",
        "version": 1,
        "title": "Exact-action approval",
        "text": "Approval expires after 15 minutes, is single-use and binds the requester, tool, full arguments and policy version. Changing any of them requires a new review. Approval cannot override a prohibition.",
        "tools": ["tickets.list", "tickets.update", "reports.export"],
    },
]


def evidence(action: Action) -> list[dict]:
    return [p for p in POLICIES if action.tool in p["tools"]]


def evaluate(action: Action, role: str) -> tuple[str, int, str]:
    if role not in {"agent", "manager"}:
        return "DENY", 90, "This account has read-only audit access."
    if action.tool == "tickets.list":
        if (
            action.ticket_id is not None
            or action.status is not None
            or action.fields
            or action.destination != "internal-reports"
        ):
            return "DENY", 70, "Ticket listing does not accept extra action parameters."
        return "ALLOW", 5, "Operational ticket fields are permitted by SUP-001."
    if action.tool == "tickets.update":
        if (
            not action.ticket_id
            or not action.status
            or action.fields
            or action.destination != "internal-reports"
        ):
            return (
                "DENY",
                70,
                "A status update needs one ticket ID and an allowed status, with no export parameters.",
            )
        return "ALLOW", 20, "A scoped ticket status change is permitted by SUP-001."
    if action.destination != "internal-reports":
        return (
            "DENY",
            95,
            "DATA-002 prohibits exports outside internal-reports. Approval cannot override this rule.",
        )
    if action.ticket_id is not None or action.status is not None:
        return "DENY", 70, "Report export does not accept ticket-update parameters."
    if (
        not action.fields
        or len(set(action.fields)) != len(action.fields)
        or set(action.fields) - set(ALL_FIELDS)
    ):
        return "DENY", 75, "Choose a non-empty list of unique supported report fields."
    if set(action.fields) & set(PRIVATE_FIELDS):
        return (
            "REQUIRE_APPROVAL",
            80,
            "DATA-003 requires a separate manager to approve this report's personal-data fields.",
        )
    return (
        "ALLOW",
        15,
        "The minimized report contains only permitted operational fields.",
    )
