"""Intent Agent — AegisMesh AI Governance Engine."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.schemas.governance import IntentResult, AgentStatus

async def run_intent(state):
    state.add_agent_execution('intent')
    
    action = (state.action or '').lower()
    target = (state.target or '').lower()
    cls = (state.data_classification or 'Internal').lower()
    purpose = (state.business_purpose or '').lower()
    
    # action_type
    if 'export' in action:
        action_type = 'data_export'
    elif 'send' in action or 'transfer' in action:
        action_type = 'data_transfer'
    elif 'delete' in action:
        action_type = 'data_deletion'
    else:
        action_type = 'api_call'
        
    # data_involved
    keywords = ['customer', 'pii', 'email', 'phone', 'financial', 'confidential', 'sensitive', 'anonymized', 'aggregated', 'database', 'records']
    data_involved = [kw for kw in keywords if kw in action]
    if not data_involved:
        data_involved.append(cls)
    
    # external_exposure
    external_keywords = ['external', 'public', 'vendor', 'new', 'unauthorized']
    external_exposure = any(kw in target for kw in external_keywords) and 'internal' not in target
    
    # sensitivity_indicators
    sensitive_keywords = ['email', 'phone', 'confidential', 'sensitive', 'pii', 'financial', 'restricted']
    sensitivity_indicators = [kw for kw in data_involved if kw in sensitive_keywords]
    if 'confidential' in cls or 'restricted' in cls or 'pii' in cls:
        if cls not in sensitivity_indicators:
            sensitivity_indicators.append(cls)
    
    # purpose alignment rating
    if ('public dump' in purpose or 'unauthorized' in purpose) and ('confidential' in cls or 'restricted' in cls or 'pii' in cls):
        purpose_alignment = "LOW (Suspicious / Misaligned)"
    elif external_exposure and ('internal' in purpose and 'analytics' not in purpose):
        purpose_alignment = "MEDIUM (Partial Alignment)"
    else:
        purpose_alignment = "HIGH (Aligned with Enterprise Objectives)"
    
    primary_intent = f"User intends to perform {action_type} ({cls}) to {target}. Business Purpose Alignment: {purpose_alignment}."
    
    state.intent = IntentResult(
        primary_intent=primary_intent,
        action_type=action_type,
        data_involved=data_involved,
        sensitivity_indicators=sensitivity_indicators,
        external_exposure=external_exposure,
        confidence=0.95
    )
    
    state.complete_agent_execution('intent', AgentStatus.COMPLETED)
    return state
