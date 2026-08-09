"""Explainability Agent — Generates human-readable explanations for governance decisions."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.schemas.governance import ExplainabilityResult, AgentStatus

async def run_explainability(state):
    state.add_agent_execution('explainability')
    
    # Handle decision string or enum gracefully
    if hasattr(state, 'final_decision') and state.final_decision:
        dec_val = state.final_decision
    elif hasattr(state, 'decision') and state.decision:
        dec_val = state.decision.value if hasattr(state.decision, 'value') else str(state.decision)
    else:
        dec_val = "APPROVE"

    summary = f"Governance decision: {dec_val} for action."
    request_description = f"User {state.user_id} requested to {state.action} to {state.target}."
    
    if state.policy_evidence:
        evidence_summary = f"Found {len(state.policy_evidence)} relevant policies."
    else:
        evidence_summary = "No specific policies retrieved."
        
    risk_score = state.risk.risk_score if state.risk else 0
    risk_level = state.risk.risk_level.value if state.risk and hasattr(state.risk.risk_level, 'value') else (state.risk.risk_level if state.risk else 'UNKNOWN')
    risk_explanation = f"Calculated risk is {risk_level} ({risk_score}/100)."
    
    decision_reasoning = f"Based on {risk_level} risk and compliance evaluation, the action was {dec_val}."
    
    state.explainability = ExplainabilityResult(
        summary=summary,
        request_description=request_description,
        evidence_summary=evidence_summary,
        risk_explanation=risk_explanation,
        decision_reasoning=decision_reasoning
    )
    
    state.complete_agent_execution('explainability', AgentStatus.COMPLETED)
    return state
