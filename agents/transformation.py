"""Transformation Agent — AegisMesh AI Governance Control Plane."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.schemas.governance import (
    TransformationDetail, TransformationChange, AgentStatus
)

# Prohibited action keywords — actions containing these are inherently dangerous
# and MUST NOT be text-sanitized into something that looks safe.
PROHIBITED_ACTION_KEYWORDS = [
    'delete', 'drop', 'truncate', 'purge', 'wipe', 'destroy',
    'disable authentication', 'remove access', 'erase', 'kill',
    'shutdown', 'format disk', 'remove all', 'delete logs',
    'disable security', 'bypass', 'exfiltrate'
]


def is_action_prohibited(action: str) -> bool:
    """Check if an action contains prohibited/dangerous keywords that should not be transformed."""
    act_lower = (action or '').lower()
    return any(kw in act_lower for kw in PROHIBITED_ACTION_KEYWORDS)


async def run_transformation(state):
    """
    Transforms the proposed AI action into a safer modified request.
    SAFETY GATE: Refuses to transform actions that are inherently dangerous/prohibited.
    """
    state.add_agent_execution('transformation')
    
    orig_request = {
        'user_id': state.user_id,
        'role': state.role,
        'action': state.action,
        'target': state.target,
        'data_classification': state.data_classification,
        'business_purpose': state.business_purpose,
        'authorization_status': state.authorization_status
    }
    
    # SAFETY GATE: Check if action is prohibited before attempting transformation
    if is_action_prohibited(state.action):
        detail = TransformationDetail(
            transformation_applied=False,
            transformation_blocked=True,
            block_reason=f"Action contains prohibited/dangerous operations that cannot be safely transformed: '{state.action}'",
            original_request=orig_request,
            modified_request=orig_request,  # No modifications
            changes=[],
            transformation_summary="Transformation BLOCKED: Action is inherently dangerous and cannot be safely modified.",
            risk_reduction_rationale="No risk reduction possible — action is prohibited.",
            original_action=state.action,
            transformed_action=state.action,  # Unchanged
            transformations_applied=[],
            business_intent_preserved=False
        )
        state.transformation = detail
        state.complete_agent_execution('transformation', AgentStatus.COMPLETED)
        return state
    
    mod_request = dict(orig_request)
    changes = []
    transforms_list = []

    # 1. Transform Data Classification if PII, Sensitive, Confidential or Restricted (unless already anonymized)
    cls = (state.data_classification or '').lower()
    if ('pii' in cls or 'sensitive' in cls or 'restricted' in cls or 'confidential' in cls) and 'anonymized' not in cls:
        mod_request['data_classification'] = 'Internal (Anonymized)'
        changes.append(TransformationChange(
            field='data_classification',
            before=state.data_classification,
            after='Internal (Anonymized)',
            reason='PII Protection & Sensitivity Minimization Policy (POL-PII-003)'
        ))
        transforms_list.append('Anonymized PII and sensitive data classification')

    # 2. Transform Action Text (Strip PII fields or restrict raw database export scope)
    act = (state.action or '').lower()
    if any(kw in act for kw in ['email', 'phone', 'records', 'pii']) and not ('anonymized' in act or 'stripped' in act):
        new_act = 'Export anonymized customer records (email and phone fields stripped)'
        mod_request['action'] = new_act
        changes.append(TransformationChange(
            field='action',
            before=state.action,
            after=new_act,
            reason='Automated PII stripping rule'
        ))
        transforms_list.append('Stripped email and phone fields from export payload')
    elif ('database' in act or 'full' in act or 'export' in act) and not ('anonymized' in act or 'aggregated' in act or 'filtered' in act or 'metrics' in act):
        new_act = 'Filtered aggregated analytics metrics view'
        mod_request['action'] = new_act
        changes.append(TransformationChange(
            field='action',
            before=state.action,
            after=new_act,
            reason='Data Minimization Policy (POL-MIN-004)'
        ))
        transforms_list.append('Converted raw database export to aggregated analytics view')

    # 3. Transform Target Endpoint (Route unapproved external flows through approved internal proxy)
    tgt = (state.target or '').lower()
    if ('external' in tgt or 'vendor' in tgt or 'public' in tgt or 'unapproved' in tgt) and 'internal' not in tgt:
        new_tgt = 'approved-internal-analytics'
        mod_request['target'] = new_tgt
        changes.append(TransformationChange(
            field='target',
            before=state.target,
            after=new_tgt,
            reason='Route external data flows through approved internal proxy'
        ))
        transforms_list.append('Restricted target endpoint to approved internal proxy')

    summary = "Transformation applied: " + "; ".join(transforms_list) if transforms_list else "No transformation required."

    detail = TransformationDetail(
        transformation_applied=len(changes) > 0,
        transformation_blocked=False,
        block_reason=None,
        original_request=orig_request,
        modified_request=mod_request,
        changes=changes,
        transformation_summary=summary,
        risk_reduction_rationale="Transformations reduce data sensitivity, eliminate external exposure, and scope action to minimal required payload.",
        original_action=state.action,
        transformed_action=mod_request['action'],
        transformations_applied=transforms_list,
        business_intent_preserved=True
    )
    
    state.transformation = detail
    state.complete_agent_execution('transformation', AgentStatus.COMPLETED)
    return state
