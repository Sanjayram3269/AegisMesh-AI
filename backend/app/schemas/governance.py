"""
AegisMesh AI — Governance Schemas

Core Pydantic models for the governance pipeline.
All agent results, API contracts, and shared types are defined here.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ==============================================================================
# Enums
# ==============================================================================

class GovernanceDecision(str, Enum):
    """Final governance decision for a proposed AI action."""
    APPROVE = "APPROVE"
    MODIFY = "MODIFY"
    ESCALATE = "ESCALATE"
    REJECT = "REJECT"


class RiskLevel(str, Enum):
    """Risk classification levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ComplianceStatus(str, Enum):
    """Compliance evaluation status."""
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    UNCERTAIN = "UNCERTAIN"


class ReviewStatus(str, Enum):
    """Reviewer validation status."""
    CONFIRMED = "CONFIRMED"
    OVERRIDDEN = "OVERRIDDEN"
    ESCALATED = "ESCALATED"
    PENDING = "PENDING"


class HumanReviewAction(str, Enum):
    """Actions a human reviewer can take."""
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_MODIFICATION = "request_modification"


class AgentStatus(str, Enum):
    """Status of an individual agent execution."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


# ==============================================================================
# Request Models
# ==============================================================================

class GovernRequest(BaseModel):
    """
    Input model for POST /api/govern.
    
    Represents a proposed AI action submitted for governance evaluation.
    """
    request_id: str = Field(
        default_factory=lambda: f"REQ-{uuid.uuid4().hex[:8].upper()}",
        description="Unique identifier for this governance request"
    )
    user_id: str = Field(
        ...,
        description="Identifier of the user or AI agent requesting the action",
        examples=["U001"]
    )
    role: str = Field(
        ...,
        description="Role of the requester within the enterprise",
        examples=["Marketing Analyst"]
    )
    action: str = Field(
        ...,
        description="Description of the proposed AI action",
        examples=["Export customer database to external analytics API"]
    )
    target: str = Field(
        ...,
        description="Target system, endpoint, or resource for the action",
        examples=["external-analytics-api"]
    )
    data_classification: str = Field(
        default="Internal",
        description="Data classification level (Public, Internal, Confidential, Restricted, PII / Sensitive)",
        examples=["Confidential"]
    )
    business_purpose: str = Field(
        default="Business operations",
        description="Business justification or purpose for the action",
        examples=["External analytics / customer insights"]
    )
    authorization_status: str = Field(
        default="Verified",
        description="Verification status of the requester (Verified, Not Verified, Pending)",
        examples=["Verified"]
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context or metadata for the request"
    )


class HumanReviewRequest(BaseModel):
    """Input model for POST /api/review/{request_id}."""
    action: HumanReviewAction = Field(
        ...,
        description="The human reviewer's decision"
    )
    reviewer_id: str = Field(
        default="HUMAN-001",
        description="Identifier of the human reviewer"
    )
    comments: str = Field(
        default="",
        description="Optional reviewer comments"
    )


# ==============================================================================
# Agent Result Models
# ==============================================================================

class PlanStep(BaseModel):
    """A single step in the governance execution plan."""
    step: int = Field(..., description="Step number")
    agent: str = Field(..., description="Agent responsible for this step")
    action: str = Field(..., description="What this step does")
    status: AgentStatus = Field(default=AgentStatus.PENDING)


class PlannerResult(BaseModel):
    """Output from the Planner Agent."""
    steps: list[PlanStep] = Field(
        default_factory=list,
        description="Ordered list of governance checks to perform"
    )
    reasoning: str = Field(
        default="",
        description="Why this plan was chosen"
    )


class IntentResult(BaseModel):
    """Output from the Intent Agent."""
    primary_intent: str = Field(
        ...,
        description="The primary intent of the proposed action"
    )
    action_type: str = Field(
        default="",
        description="Classification of the action type (e.g., data_export, api_call)"
    )
    data_involved: list[str] = Field(
        default_factory=list,
        description="Types of data involved (e.g., customer_pii, financial)"
    )
    sensitivity_indicators: list[str] = Field(
        default_factory=list,
        description="Detected sensitivity indicators"
    )
    external_exposure: bool = Field(
        default=False,
        description="Whether the action involves external data exposure"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Confidence score for the intent classification"
    )


class PermissionDetail(BaseModel):
    """Details about a specific permission check."""
    permission: str = Field(..., description="Permission name")
    granted: bool = Field(..., description="Whether this permission is held")
    required: bool = Field(default=True, description="Whether this permission is required")


class IdentityResult(BaseModel):
    """Output from the Identity Agent."""
    user_id: str = Field(..., description="Verified user identifier")
    name: str = Field(default="", description="User display name")
    role: str = Field(default="", description="User's enterprise role")
    department: str = Field(default="", description="User's department")
    clearance_level: str = Field(
        default="low",
        description="Security clearance level (low/medium/high/admin)"
    )
    permissions: list[str] = Field(
        default_factory=list,
        description="List of permissions held by the user"
    )
    permission_checks: list[PermissionDetail] = Field(
        default_factory=list,
        description="Detailed permission check results"
    )
    authorized: bool = Field(
        default=False,
        description="Whether the user is authorized for the requested action"
    )
    authorization_reason: str = Field(
        default="",
        description="Reason for the authorization decision"
    )


class PolicyEvidence(BaseModel):
    """A single piece of policy evidence retrieved via RAG."""
    policy_id: str = Field(..., description="Policy document identifier")
    policy_name: str = Field(..., description="Human-readable policy name")
    section: str = Field(default="", description="Relevant section within the policy")
    text: str = Field(..., description="Relevant policy text excerpt")
    relevance_score: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="How relevant this evidence is to the request"
    )
    source_file: str = Field(default="", description="Source file path")
    decision_action: str = Field(default="", description="Associated policy decision action")
    priority: str = Field(default="", description="Associated policy priority")


class ComplianceResult(BaseModel):
    """Output from the Compliance Agent."""
    status: ComplianceStatus = Field(
        ...,
        description="Overall compliance status"
    )
    violated_policies: list[str] = Field(
        default_factory=list,
        description="List of violated policy identifiers"
    )
    evidence: list[PolicyEvidence] = Field(
        default_factory=list,
        description="Supporting policy evidence"
    )
    explanation: str = Field(
        default="",
        description="Explanation of the compliance assessment"
    )
    recommended_remediation: str = Field(
        default="",
        description="Suggested remediation if non-compliant"
    )


class RiskFactor(BaseModel):
    """An individual risk factor contributing to the overall risk score."""
    factor: str = Field(..., description="Name of the risk factor")
    score: float = Field(..., ge=0.0, le=100.0, description="Risk contribution (0-100)")
    weight: float = Field(default=1.0, description="Weight of this factor")
    description: str = Field(default="", description="Why this factor is relevant")


class RiskResult(BaseModel):
    """Output from the Risk Agent (Structured 3-Stage Risk Assessment)."""
    risk_score: int = Field(
        ...,
        ge=0, le=100,
        description="Effective risk score after mitigations (0-100)"
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Classified risk level"
    )
    inherent_risk_score: int = Field(
        default=0, ge=0, le=100,
        description="Raw inherent risk score of action before mitigations"
    )
    risk_reduction: int = Field(
        default=0,
        description="Total risk points reduced by mitigations and transformations"
    )
    effective_risk: int = Field(
        default=0, ge=0, le=100,
        description="Final effective risk score"
    )
    risk_factors: list[RiskFactor] = Field(
        default_factory=list,
        description="Aggravating factors contributing to inherent risk score"
    )
    mitigating_factors: list[str] = Field(
        default_factory=list,
        description="Verified risk reducing controls and policy mitigations"
    )
    matched_policy_ids: list[str] = Field(
        default_factory=list,
        description="IDs of matched policies"
    )
    rationale: str = Field(
        default="",
        description="Human-readable risk rationale"
    )


class ExplainabilityResult(BaseModel):
    """Output from the Explainability Agent."""
    summary: str = Field(
        ...,
        description="Concise summary of the governance evaluation"
    )
    request_description: str = Field(
        default="",
        description="What was requested"
    )
    evidence_summary: str = Field(
        default="",
        description="What evidence was used"
    )
    risk_explanation: str = Field(
        default="",
        description="Why risk exists"
    )
    decision_reasoning: str = Field(
        default="",
        description="Why the final decision was reached"
    )


def get_standard_risk_level(score: int) -> RiskLevel:
    """
    Single centralized 4-tier risk level mapping across the entire system:
    0 - 24   = LOW
    25 - 49  = MEDIUM
    50 - 74  = HIGH
    75 - 100 = CRITICAL
    """
    if score < 25:
        return RiskLevel.LOW
    elif score < 50:
        return RiskLevel.MEDIUM
    elif score < 75:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL


class RiskAssessment(BaseModel):
    """Authoritative single-stage risk assessment object (Inherent or Effective/Final)."""
    score: int = Field(..., ge=0, le=100, description="Risk score (0-100)")
    level: RiskLevel = Field(..., description="Standardized 4-tier risk level")
    confidence: int = Field(default=85, ge=0, le=100, description="Confidence score percentage (0-100)")
    signals: dict[str, float] = Field(default_factory=dict, description="Dynamic signal scores")
    rationale: list[str] = Field(default_factory=list, description="Calculation factors & reasons")


class TransformationChange(BaseModel):
    """A single attribute change applied by the Transformation Agent."""
    field: str = Field(..., description="Modified request field")
    before: str = Field(..., description="Field value before transformation")
    after: str = Field(..., description="Field value after transformation")
    reason: str = Field(..., description="Policy rule or safety justification")


class TransformationDetail(BaseModel):
    """Output from the Transformation Agent detailing modified request & diffs."""
    transformation_applied: bool = Field(default=False)
    original_request: dict[str, Any] = Field(default_factory=dict)
    modified_request: dict[str, Any] = Field(default_factory=dict)
    changes: list[TransformationChange] = Field(default_factory=list)
    transformation_summary: str = Field(default="")
    risk_reduction_rationale: str = Field(default="")
    original_action: str = Field(default="")
    transformed_action: str = Field(default="")
    transformations_applied: list[str] = Field(default_factory=list)
    business_intent_preserved: bool = Field(default=True)
    transformation_blocked: bool = Field(default=False, description="True if transformation was blocked due to prohibited/dangerous action")
    block_reason: Optional[str] = Field(default=None, description="Reason transformation was blocked")


class ExecutionStageItem(BaseModel):
    """Tracks a stage in the execution lifecycle history."""
    stage: str = Field(..., description="Lifecycle stage (INHERENT_RISK, POLICY_DECISION, TRANSFORMATION, FINAL_RISK, FINAL_DECISION)")
    details: dict[str, Any] = Field(default_factory=dict, description="Stage metadata")


class ReviewResult(BaseModel):
    """Output from the Reviewer Agent."""
    status: ReviewStatus = Field(
        ...,
        description="Reviewer's validation status"
    )
    evidence_sufficient: bool = Field(
        default=True,
        description="Whether sufficient evidence supports the decision"
    )
    checks_performed: bool = Field(
        default=True,
        description="Whether all required checks were completed"
    )
    reasoning_consistent: bool = Field(
        default=True,
        description="Whether the reasoning is internally consistent"
    )
    confidence_sufficient: bool = Field(
        default=True,
        description="Whether confidence levels are adequate"
    )
    original_decision: GovernanceDecision | None = Field(
        default=None,
        description="The decision before review"
    )
    final_decision: GovernanceDecision | None = Field(
        default=None,
        description="The decision after review"
    )
    comments: str = Field(
        default="",
        description="Reviewer comments"
    )
    requires_human_review: bool = Field(
        default=False,
        description="Whether human escalation is recommended"
    )


class TransformationResult(TransformationDetail):
    """Backward compatible alias for TransformationDetail."""
    pass


# ==============================================================================
# Agent Execution Tracking
# ==============================================================================

class AgentExecution(BaseModel):
    """Tracks the execution of a single agent in the pipeline."""
    agent_name: str = Field(..., description="Name of the agent")
    status: AgentStatus = Field(default=AgentStatus.PENDING)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    duration_ms: float | None = Field(default=None)
    error: str | None = Field(default=None)


# ==============================================================================
# Audit Models
# ==============================================================================

class AuditRecord(BaseModel):
    """Complete audit trail for a governance request."""
    audit_id: str = Field(
        default_factory=lambda: f"AUD-{uuid.uuid4().hex[:8].upper()}",
        description="Unique audit record identifier"
    )
    request_id: str = Field(..., description="Associated request ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the audit record was created"
    )

    # Request details
    user_id: str = Field(default="")
    role: str = Field(default="")
    action: str = Field(default="")
    target: str = Field(default="")

    # Agent results
    intent: IntentResult | None = Field(default=None)
    identity: IdentityResult | None = Field(default=None)
    compliance: ComplianceResult | None = Field(default=None)
    risk: RiskResult | None = Field(default=None)
    explainability: ExplainabilityResult | None = Field(default=None)
    review: ReviewResult | None = Field(default=None)
    transformation: TransformationResult | None = Field(default=None)

    # Decision
    decision: GovernanceDecision | None = Field(default=None)
    risk_score: int = Field(default=0)
    risk_level: RiskLevel | None = Field(default=None)

    # Evidence
    policy_evidence: list[PolicyEvidence] = Field(default_factory=list)

    # Pipeline execution
    agents_executed: list[AgentExecution] = Field(default_factory=list)
    pipeline_duration_ms: float | None = Field(default=None)

    # Human review
    human_review_required: bool = Field(default=False)
    human_review_status: str | None = Field(default=None)
    human_reviewer_id: str | None = Field(default=None)
    human_review_comments: str | None = Field(default=None)

    # Provider
    llm_provider: str = Field(default="mock", description="LLM provider used")


# ==============================================================================
# API Response Models
# ==============================================================================

class GovernResponse(BaseModel):
    """
    Output model for POST /api/govern.
    
    Contains the complete two-stage governance decision with supporting evidence.
    """
    request_id: str = Field(..., description="Request identifier")
    execution_id: str = Field(default="", description="Unique execution lifecycle identifier")
    decision: GovernanceDecision = Field(..., description="Effective final governance decision")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score (0-100)")
    risk_level: RiskLevel = Field(..., description="Risk classification")

    # Canonical 3-Stage Risk Models
    inherent_risk: RiskAssessment | None = Field(default=None, description="Authoritative inherent risk assessment before modification")
    final_risk: RiskAssessment | None = Field(default=None, description="Final effective risk assessment after modification")
    effective_risk: int = Field(default=0, ge=0, le=100, description="Effective final risk score (0-100)")
    risk_reduction: int | None = Field(default=None, description="Numeric risk score points reduced by mitigations & transformation")
    mitigating_factors: list[str] = Field(default_factory=list, description="Verified risk reducing controls and policy mitigations")
    matched_policy_ids: list[str] = Field(default_factory=list, description="IDs of matched policies")

    # Separate Policy & Final Decisions
    policy_decision: GovernanceDecision = Field(default=GovernanceDecision.APPROVE, description="Policy decision before transformation")
    final_decision: str = Field(default="APPROVE", description="Final effective decision (e.g. APPROVE, APPROVED AFTER MODIFICATION)")

    # Execution Lifecycle History
    lifecycle_history: list[ExecutionStageItem] = Field(default_factory=list, description="Stage-by-stage execution history")

    # Agent results
    intent: IntentResult | None = Field(default=None)
    identity: IdentityResult | None = Field(default=None)
    compliance: ComplianceResult | None = Field(default=None)
    risk: RiskResult | None = Field(default=None)
    review: ReviewResult | None = Field(default=None)

    # Evidence and explanation
    evidence: list[PolicyEvidence] = Field(default_factory=list)
    explanation: str = Field(default="", description="Human-readable explanation")

    # Transformation (only for MODIFY decisions)
    transformation: TransformationDetail | None = Field(default=None)
    recommended_action: str = Field(
        default="",
        description="Recommended next step"
    )

    # Pipeline metadata
    agents_executed: list[AgentExecution] = Field(default_factory=list)
    pipeline_duration_ms: float | None = Field(default=None)
    llm_provider: str = Field(default="mock")
    provider_status: str = Field(default="active", description="LLM provider status ('active', 'fallback', 'mock')")

    # Audit reference
    audit_id: str = Field(default="", description="Reference to the audit record")

    # Human review & rationale
    human_review_required: bool = Field(default=False)
    confidence: float = Field(default=0.88, ge=0.0, le=1.0)
    decision_rationale: list[str] = Field(default_factory=list)
    decision_source: str = Field(default="explicit_policy", description="Source of decision ('explicit_policy', 'conflict_resolution', 'fallback_risk_engine', 'mock_fallback')")
    debug_info: dict[str, Any] = Field(default_factory=dict, description="Structured debug & audit metadata")
    data_classification: str = Field(default="Internal")
    business_purpose: str = Field(default="")
    authorization_status: str = Field(default="Verified")


class HealthResponse(BaseModel):
    """Output model for GET /api/health."""
    status: str = Field(default="healthy")
    version: str = Field(default="0.1.0")
    provider: Any = Field(default="mock", description="Active LLM provider info")
    demo_mode: bool = Field(default=True)
    database: str = Field(default="connected")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AuditListResponse(BaseModel):
    """Output model for GET /api/audit."""
    total: int = Field(default=0)
    records: list[AuditRecord] = Field(default_factory=list)


class HumanReviewResponse(BaseModel):
    """Output model for POST /api/review/{request_id}."""
    request_id: str = Field(...)
    review_action: HumanReviewAction = Field(...)
    reviewer_id: str = Field(default="")
    previous_decision: GovernanceDecision | None = Field(default=None)
    updated_decision: GovernanceDecision | None = Field(default=None)
    comments: str = Field(default="")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    request_id: str | None = Field(default=None)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
