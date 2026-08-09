"""AegisMesh AI — Policy Schemas for Dynamic Policy Management."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class PolicyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DRAFT = "DRAFT"


class PolicyPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PolicyDecisionAction(str, Enum):
    APPROVE = "APPROVE"
    MODIFY = "MODIFY"
    ESCALATE = "ESCALATE"
    REJECT = "REJECT"


class PolicyCreate(BaseModel):
    policy_id: str = Field(..., description="Unique policy identifier, e.g., POL-HUM-001", examples=["POL-CUSTOM-001"])
    name: str = Field(..., description="Human-readable policy name", examples=["Custom Vendor Access Policy"])
    description: str = Field(default="", description="Detailed summary of policy objective")
    rule_definition: str = Field(..., description="Actionable rule text or criteria for RAG retrieval")
    decision_action: PolicyDecisionAction = Field(default=PolicyDecisionAction.APPROVE)
    priority: PolicyPriority = Field(default=PolicyPriority.MEDIUM)
    status: PolicyStatus = Field(default=PolicyStatus.ACTIVE)
    created_by: str = Field(default="system")


class PolicyUpdate(BaseModel):
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    rule_definition: Optional[str] = Field(default=None)
    decision_action: Optional[PolicyDecisionAction] = Field(default=None)
    priority: Optional[PolicyPriority] = Field(default=None)
    status: Optional[PolicyStatus] = Field(default=None)


class PolicyStatusUpdate(BaseModel):
    status: PolicyStatus = Field(...)


class PolicyResponse(BaseModel):
    id: int
    policy_id: str
    name: str
    description: str
    rule_definition: str
    decision_action: str
    priority: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class PolicyListResponse(BaseModel):
    total: int
    policies: list[PolicyResponse]
