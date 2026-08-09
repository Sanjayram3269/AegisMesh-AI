"""Compliance Agent — Evaluates intake signals against active enterprise policies."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.schemas.governance import ComplianceResult, ComplianceStatus, AgentStatus

async def run_compliance(state):
    state.add_agent_execution('compliance')
    
    action = (state.action or '').lower()
    target = (state.target or '').lower()
    cls = (state.data_classification or '').lower()
    auth = (state.authorization_status or '').lower()
    
    intent = state.intent
    identity = state.identity
    
    violations = []
    
    # 1. Evaluate intake signal rules
    if (any(kw in action for kw in ['email', 'phone', 'records', 'pii']) or 'pii' in cls) and \
       ('approved-analytics' in target or 'vendor' in target or 'external' in target or 'public' in target):
        violations.append("POL-PII-003")
        violations.append("PII Protection Policy")
        
    if ('confidential' in cls or 'restricted' in cls or 'pii' in cls) and ('public' in target or 'unauthorized' in target):
        violations.append("POL-TRN-002")
        violations.append("Data Transfer Policy")
        
    if ('vendor' in target or 'new' in target or 'external' in target or 'pending' in auth or 'unverified' in auth) and \
       ('restricted' in cls or 'confidential' in cls or 'pending' in auth):
        violations.append("POL-HUM-001")
        violations.append("Human Approval Policy")
        
    if 'database' in action and 'export' in action and 'anonymized' not in action:
        violations.append("POL-MIN-004")
        violations.append("Data Minimization Policy")
        
    if not (identity and getattr(identity, 'authorized', True)):
        violations.append("POL-HUM-001")
        violations.append("Human Approval Policy")

    # 2. Evaluate dynamic retrieved active policy evidence from RAG
    if state.policy_evidence:
        for ev in state.policy_evidence:
            ev_action = (getattr(ev, 'decision_action', None) or '').upper()
            rel_score = float(getattr(ev, 'relevance_score', 0.0))
            pid = getattr(ev, 'policy_id', '')
            pname = (getattr(ev, 'policy_name', '') or '').lower()
            
            # POL-TRN-002 (Data Transfer Policy) specifically targets public/unauthorized endpoints
            if pid == "POL-TRN-002" or "data transfer policy" in pname:
                if ('public' in target or 'unauthorized' in target) and ('confidential' in cls or 'restricted' in cls or 'pii' in cls):
                    violations.append(ev.policy_id)
                    violations.append(ev.policy_name)
            # POL-MIN-004 (Data Minimization Policy) does not apply if action is already anonymized
            elif "POL-MIN-004" in pid or "data minimization" in pname:
                if 'database' in action and 'export' in action and 'anonymized' not in action:
                    violations.append(ev.policy_id)
                    violations.append(ev.policy_name)
            elif ev_action in ["REJECT", "ESCALATE", "MODIFY"] and rel_score >= 0.50:
                violations.append(ev.policy_id)
                violations.append(ev.policy_name)

    if len(violations) == 0:
        if intent and intent.external_exposure:
            status = ComplianceStatus.UNCERTAIN
        else:
            status = ComplianceStatus.COMPLIANT
    else:
        status = ComplianceStatus.NON_COMPLIANT

    # Remove duplicates
    unique_violations = list(dict.fromkeys(violations))

    state.compliance = ComplianceResult(
        status=status,
        violated_policies=unique_violations,
        explanation=f"Compliance check result: {status.value}. Evaluated {len(unique_violations)} active policy clauses."
    )
    
    state.complete_agent_execution('compliance', AgentStatus.COMPLETED)
    return state
