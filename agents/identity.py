"""Identity Agent — AegisMesh AI Governance Engine."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.schemas.governance import IdentityResult, PermissionDetail, AgentStatus

DEMO_USERS = {
    'U001': {'name': 'Alice', 'role': 'Senior Data Analyst', 'department': 'Analytics', 'clearance_level': 'Medium-High', 'permissions': ['read_customer_summary', 'export_anonymized_report', 'internal_analytics']},
    'U002': {'name': 'Bob', 'role': 'Marketing Analyst', 'department': 'Marketing', 'clearance_level': 'Medium', 'permissions': ['read_customer_summary', 'export_anonymized_report', 'send_internal_report']},
    'U003': {'name': 'Charlie', 'role': 'Procurement Manager', 'department': 'Procurement', 'clearance_level': 'High', 'permissions': ['read_customer_summary', 'export_anonymized_report', 'send_internal_report', 'request_external_transfer']},
    'U004': {'name': 'Dave', 'role': 'Junior Analyst', 'department': 'Contractor', 'clearance_level': 'Low', 'permissions': []}
}

async def run_identity(state):
    state.add_agent_execution('identity')
    
    user_id = state.user_id
    user = DEMO_USERS.get(user_id, DEMO_USERS['U004'])
    
    action = (state.action or '').lower()
    target = (state.target or '').lower()
    classification = (state.data_classification or 'Internal').lower()
    auth_status = (state.authorization_status or 'Verified').lower()
    submitted_role = (state.role or '').lower()

    # Identity / Role mismatch check
    profile_role = user['role'].lower()
    mismatch_detected = False
    if submitted_role and profile_role:
        if ('junior' in profile_role and 'senior' in submitted_role) or ('contractor' in profile_role and 'admin' in submitted_role):
            mismatch_detected = True

    required_perms = []
    if 'export' in action or 'send' in action:
        if any(kw in classification for kw in ['confidential', 'restricted', 'pii', 'sensitive']) or any(kw in action for kw in ['pii', 'confidential', 'sensitive', 'email', 'phone']):
            required_perms.append('request_external_transfer')
        else:
            required_perms.append('export_anonymized_report')
            
    if any(kw in target for kw in ['external', 'public', 'vendor', 'new']) and 'internal' not in target:
        if 'request_external_transfer' not in required_perms:
            required_perms.append('request_external_transfer')
            
    permission_checks = []
    for perm in required_perms:
        granted = perm in user['permissions']
        permission_checks.append(PermissionDetail(permission=perm, granted=granted, required=True))
        
    authorized = (auth_status == 'verified') and all(check.granted for check in permission_checks) if permission_checks else (auth_status == 'verified')
    
    if mismatch_detected:
        authorized = False
        authorization_reason = f"Identity / Role mismatch: Profile ({user['role']}) contradicts submitted role ({state.role})."
    elif auth_status != 'verified':
        authorized = False
        authorization_reason = f"Authorization Status is '{state.authorization_status}'."
    elif not authorized:
        authorization_reason = "Missing required permissions or clearance for specified data classification."
    else:
        authorization_reason = "User identity verified and clearance approved for request."

    state.identity = IdentityResult(
        user_id=user_id,
        name=user['name'],
        role=state.role or user['role'],
        department=user['department'],
        clearance_level=user['clearance_level'],
        permissions=user['permissions'],
        permission_checks=permission_checks,
        authorized=authorized,
        authorization_reason=authorization_reason
    )
    
    state.complete_agent_execution('identity', AgentStatus.COMPLETED)
    return state
