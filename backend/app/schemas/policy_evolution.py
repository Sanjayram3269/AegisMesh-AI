"""
Pydantic Schemas for AegisMesh AI Autonomous Policy Evolution & Change Intelligence.
"""

from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PolicyChangeType(str, Enum):
    NO_CHANGE = "NO_CHANGE"
    TEXTUAL_CHANGE = "TEXTUAL_CHANGE"
    SCOPE_EXPANSION = "SCOPE_EXPANSION"
    SCOPE_REDUCTION = "SCOPE_REDUCTION"
    CONDITION_ADDED = "CONDITION_ADDED"
    CONDITION_REMOVED = "CONDITION_REMOVED"
    DECISION_CHANGED = "DECISION_CHANGED"
    PRIORITY_CHANGED = "PRIORITY_CHANGED"
    ACTIVATION_CHANGED = "ACTIVATION_CHANGED"
    CONFLICT_INTRODUCED = "CONFLICT_INTRODUCED"
    SECURITY_IMPACT_CHANGE = "SECURITY_IMPACT_CHANGE"
    DATA_SENSITIVITY_CHANGE = "DATA_SENSITIVITY_CHANGE"
    UNKNOWN_HIGH_IMPACT = "UNKNOWN_HIGH_IMPACT"


class PolicyImpactLevel(str, Enum):
    LOW = "LOW"            # 0-24
    MODERATE = "MODERATE"   # 25-49
    HIGH = "HIGH"          # 50-74
    CRITICAL = "CRITICAL"   # 75-100


class PolicySnapshot(BaseModel):
    """Canonical normalized snapshot of an enterprise policy version."""
    policy_id: str = Field(..., description="Unique policy identifier")
    name: str = Field(..., description="Policy title")
    version: int = Field(default=1, description="Version number")
    decision_action: str = Field(default="APPROVE", description="Decision action (APPROVE, MODIFY, ESCALATE, REJECT)")
    priority: str = Field(default="MEDIUM", description="Policy priority (LOW, MEDIUM, HIGH, CRITICAL)")
    status: str = Field(default="ACTIVE", description="Policy status (ACTIVE, INACTIVE, DRAFT)")
    description: str = Field(default="", description="Policy description")
    rule_definition: str = Field(..., description="Rule definition & criteria text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional policy metadata")


class HistoricalReplayItem(BaseModel):
    """Result of replaying a single historical governance action against policy versions."""
    action_id: str = Field(..., description="Audit/Action record identifier")
    request_id: str = Field(default="")
    user_id: str = Field(default="")
    action: str = Field(default="")
    target: str = Field(default="")
    old_decision: str = Field(..., description="Decision produced under old policy")
    new_decision: str = Field(..., description="Decision produced under new policy")
    changed: bool = Field(default=False, description="True if decision changed")
    is_more_restrictive: bool = Field(default=False, description="True if new decision is more restrictive")
    reason: str = Field(default="", description="Explanation of why decision changed")


class HistoricalReplaySummary(BaseModel):
    """Summary of historical governance replay simulation."""
    historical_actions_analyzed: int = Field(default=0)
    affected_actions_count: int = Field(default=0)
    unchanged_actions_count: int = Field(default=0)
    more_restrictive_count: int = Field(default=0)
    less_restrictive_count: int = Field(default=0)
    regressions_count: int = Field(default=0)
    affected_actions: List[HistoricalReplayItem] = Field(default_factory=list)
    recommendation: str = Field(default="")


class PolicyConflictItem(BaseModel):
    """Details of a policy conflict or condition overlap."""
    conflict_detected: bool = Field(default=False)
    conflict_type: str = Field(default="NONE", description="Conflict type (DECISION_CONFLICT, PRIORITY_OVERLAP, CONDITION_OVERLAP)")
    policy_ids: List[str] = Field(default_factory=list, description="Involved policy IDs")
    scenario: str = Field(default="", description="Conflict scenario description")
    resolved_by: str = Field(default="POLICY_PRIORITY", description="How precedence resolves this conflict")
    recommended_action: str = Field(default="", description="Suggested policy alignment fix")


class PolicyChangeAnalysis(BaseModel):
    """Structured analysis output from analyze_policy_change."""
    change_detected: bool = Field(default=False)
    change_type: PolicyChangeType = Field(default=PolicyChangeType.NO_CHANGE)
    semantic_summary: str = Field(default="")
    decision_impact: str = Field(default="NEUTRAL", description="NEUTRAL, MORE_RESTRICTIVE, LESS_RESTRICTIVE, MIXED")
    impact_score: int = Field(default=0, ge=0, le=100)
    impact_level: PolicyImpactLevel = Field(default=PolicyImpactLevel.LOW)
    affected_policy_ids: List[str] = Field(default_factory=list)
    affected_action_count: int = Field(default=0)
    conflicts: List[PolicyConflictItem] = Field(default_factory=list)
    regressions_detected: bool = Field(default=False)
    recommended_action: str = Field(default="AUTO_ENFORCE")
    requires_human_review: bool = Field(default=False)
    autonomous_action: str = Field(default="ENFORCED_AUTOMATICALLY")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)


class PolicyEvolutionReport(BaseModel):
    """Full Change Intelligence Report for a policy version update event."""
    event_id: str = Field(...)
    policy_id: str = Field(...)
    version: int = Field(...)
    previous_version: int = Field(...)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    old_snapshot: PolicySnapshot
    new_snapshot: PolicySnapshot
    
    analysis: PolicyChangeAnalysis
    replay_summary: Optional[HistoricalReplaySummary] = Field(default=None)
    
    requires_human_review: bool = Field(default=False)
    human_review_status: str = Field(default="AUTO_ENFORCED")  # AUTO_ENFORCED, PENDING, APPROVED, REJECTED
    human_reviewer_id: Optional[str] = Field(default=None)
    human_review_comments: Optional[str] = Field(default=None)
    approved_at: Optional[datetime] = Field(default=None)


class PolicyEnforcementApproval(BaseModel):
    """Request model for POST /api/policy-evolution/approve-enforcement."""
    event_id: str = Field(...)
    reviewer_id: str = Field(..., description="ID or role of approving administrator")
    action: str = Field(..., description="APPROVE or REJECT enforcement")
    comments: str = Field(default="")


class PolicyEvolutionKPICards(BaseModel):
    """KPI summary cards for Policy Evolution dashboard."""
    active_policies_count: int = Field(default=0)
    policy_changes_detected: int = Field(default=0)
    requires_human_review_count: int = Field(default=0)
    critical_regressions_count: int = Field(default=0)
