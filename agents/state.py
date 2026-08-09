"""
AegisMesh AI — Governance State
"""

from __future__ import annotations

import os, sys, uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

# Ensure backend directory is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.schemas.governance import (
    GovernanceDecision,
    RiskLevel,
    ComplianceStatus,
    ReviewStatus,
    AgentStatus,
    PlannerResult,
    IntentResult,
    IdentityResult,
    ComplianceResult,
    RiskResult,
    ExplainabilityResult,
    ReviewResult,
    TransformationResult,
    PolicyEvidence,
    AgentExecution,
    AuditRecord,
)


class GovernanceState(BaseModel):
    # ── Request ──────────────────────────────────────────────────────────
    request_id: str = Field(
        default_factory=lambda: f"REQ-{uuid.uuid4().hex[:8].upper()}",
        description="Unique governance request ID"
    )
    user_id: str = Field(default="", description="User or AI agent ID")
    role: str = Field(default="", description="Enterprise role of requester")
    action: str = Field(default="", description="Proposed AI action")
    target: str = Field(default="", description="Target system/endpoint")
    data_classification: str = Field(default="Internal", description="Data classification level")
    business_purpose: str = Field(default="", description="Business justification")
    authorization_status: str = Field(default="Verified", description="Requester verification status")
    confidence: float = Field(default=0.88)
    decision_rationale: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provider_status: str = Field(default="active")

    # ── Planning ─────────────────────────────────────────────────────────
    plan: PlannerResult | None = Field(default=None)

    # ── Analysis ─────────────────────────────────────────────────────────
    intent: IntentResult | None = Field(default=None)
    identity: IdentityResult | None = Field(default=None)
    data_context: dict[str, Any] = Field(default_factory=dict)

    # ── RAG / Evidence ───────────────────────────────────────────────────
    retrieved_context: list[dict[str, Any]] = Field(default_factory=list)
    policy_evidence: list[PolicyEvidence] = Field(default_factory=list)

    # ── Governance Assessment ────────────────────────────────────────────
    execution_id: str = Field(default="")
    inherent_risk: Any | None = Field(default=None)
    final_risk: Any | None = Field(default=None)
    risk_reduction: int | None = Field(default=None)
    policy_decision: GovernanceDecision | None = Field(default=None)
    final_decision: str = Field(default="APPROVE")
    transformation: Any | None = Field(default=None)
    lifecycle_history: list[Any] = Field(default_factory=list)
    human_review_required: bool = Field(default=False)

    compliance: ComplianceResult | None = Field(default=None)
    risk: RiskResult | None = Field(default=None)
    explainability: ExplainabilityResult | None = Field(default=None)

    # ── Review ───────────────────────────────────────────────────────────
    review: ReviewResult | None = Field(default=None)

    # ── Decision ─────────────────────────────────────────────────────────
    decision: GovernanceDecision | None = Field(default=None)
    transformed_action: TransformationResult | None = Field(default=None)

    # ── Pipeline Tracking ────────────────────────────────────────────────
    agents_executed: list[AgentExecution] = Field(default_factory=list)
    pipeline_started_at: datetime | None = Field(default=None)
    pipeline_completed_at: datetime | None = Field(default=None)

    # ── Audit ────────────────────────────────────────────────────────────
    audit: AuditRecord | None = Field(default=None)

    # ── Error Handling ───────────────────────────────────────────────────
    errors: list[str] = Field(default_factory=list)

    # ── Iteration Control ────────────────────────────────────────────────
    iteration: int = Field(default=0)
    max_iterations: int = Field(default=3)

    # ── Provider ─────────────────────────────────────────────────────────
    llm_provider: str = Field(default="mock")

    # ── Helper Methods ───────────────────────────────────────────────────

    def add_agent_execution(self, agent_name: str) -> AgentExecution:
        execution = AgentExecution(
            agent_name=agent_name,
            status=AgentStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        self.agents_executed.append(execution)
        return execution

    def complete_agent_execution(
        self, agent_name: str, status: AgentStatus = AgentStatus.COMPLETED, error: str | None = None
    ) -> None:
        for execution in reversed(self.agents_executed):
            if execution.agent_name == agent_name and execution.status == AgentStatus.RUNNING:
                execution.status = status
                execution.completed_at = datetime.now(timezone.utc)
                if execution.started_at:
                    delta = execution.completed_at - execution.started_at
                    execution.duration_ms = delta.total_seconds() * 1000
                if error:
                    execution.error = error
                return

    def get_pipeline_duration_ms(self) -> float | None:
        if self.pipeline_started_at and self.pipeline_completed_at:
            delta = self.pipeline_completed_at - self.pipeline_started_at
            return delta.total_seconds() * 1000
        return None

    def has_critical_errors(self) -> bool:
        return len(self.errors) > 0

    def should_escalate(self) -> bool:
        if self.risk and self.risk.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return True
        if self.compliance and self.compliance.status == ComplianceStatus.UNCERTAIN:
            return True
        if self.review and self.review.requires_human_review:
            return True
        if self.has_critical_errors():
            return True
        return False

    @classmethod
    def from_request(cls, request_id: str, user_id: str, role: str, action: str,
                     target: str, data_classification: str = "Internal",
                     business_purpose: str = "", authorization_status: str = "Verified",
                     metadata: dict | None = None) -> "GovernanceState":
        return cls(
            request_id=request_id,
            user_id=user_id,
            role=role,
            action=action,
            target=target,
            data_classification=data_classification,
            business_purpose=business_purpose,
            authorization_status=authorization_status,
            metadata=metadata or {},
            pipeline_started_at=datetime.now(timezone.utc),
        )
