"""Reviewer Agent — Verifies pipeline consistency and determines if human review is required."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.schemas.governance import ReviewResult, ReviewStatus, GovernanceDecision, AgentStatus

async def run_reviewer(state):
    state.add_agent_execution('reviewer')
    
    evidence_sufficient = len(state.policy_evidence) > 0 if state.policy_evidence else False
    checks_performed = all([state.intent is not None, state.identity is not None, state.compliance is not None, state.risk is not None])
    
    reasoning_consistent = True
    if state.risk and state.risk.risk_score > 79 and state.compliance and state.compliance.status == 'COMPLIANT':
        reasoning_consistent = False
        
    confidence_sufficient = state.intent.confidence > 0.5 if (state.intent and getattr(state.intent, 'confidence', 0)) else True
    
    requires_human_review = False
    
    # 1. If explicit policy decision is ESCALATE, human review is required
    if state.policy_decision == GovernanceDecision.ESCALATE:
        requires_human_review = True
    # 2. If decision source is fallback_risk_engine and risk score is high, require human review
    elif state.metadata.get("decision_source") == "fallback_risk_engine" and state.risk and state.risk.risk_score >= 70:
        requires_human_review = True
    # 3. Compliance status UNCERTAIN
    elif state.compliance and state.compliance.status == 'UNCERTAIN' and state.policy_decision not in [GovernanceDecision.APPROVE, GovernanceDecision.MODIFY, GovernanceDecision.REJECT]:
        requires_human_review = True
    # 4. Reasoning inconsistency (high risk but compliant) requires human review
    elif not reasoning_consistent:
        requires_human_review = True

    final_decision = None
    if requires_human_review and state.decision != GovernanceDecision.REJECT:
        final_decision = GovernanceDecision.ESCALATE

    state.review = ReviewResult(
        status=ReviewStatus.CONFIRMED if not final_decision else ReviewStatus.ESCALATED,
        evidence_sufficient=True if (evidence_sufficient or state.metadata.get("decision_source") in ["explicit_policy", "conflict_resolution"]) else False,
        checks_performed=checks_performed,
        reasoning_consistent=reasoning_consistent,
        confidence_sufficient=confidence_sufficient,
        original_decision=state.decision,
        final_decision=final_decision,
        comments="Review completed successfully.",
        requires_human_review=requires_human_review
    )
    
    state.complete_agent_execution('reviewer', AgentStatus.COMPLETED)
    return state
