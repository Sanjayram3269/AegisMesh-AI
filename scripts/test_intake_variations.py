"""Test script for 7-field dynamic intake governance evaluation."""
import httpx

base_req = {
    'request_id': 'REQ-TEST-VARIATIONS',
    'user_id': 'U001',
    'role': 'Senior Data Analyst',
    'action': 'Export anonymized aggregated customer analytics',
    'target': 'approved-internal-analytics',
    'data_classification': 'Internal',
    'business_purpose': 'Internal executive reporting and analytics',
    'authorization_status': 'Verified'
}

print("============================================================")
print("  TEST A: Baseline (Internal, Verified, Senior Analyst, Approved Target)")
print("============================================================")
rA = httpx.post('http://localhost:8000/api/govern', json=base_req).json()
print(f"Decision: {rA.get('decision')} | Risk: {rA.get('risk_score')} ({rA.get('risk_level')})")

print("\n============================================================")
print("  TEST B: Change ONLY Data Classification -> Confidential")
print("============================================================")
reqB = dict(base_req)
reqB['data_classification'] = 'Confidential'
rB = httpx.post('http://localhost:8000/api/govern', json=reqB).json()
print(f"Decision: {rB.get('decision')} | Risk: {rB.get('risk_score')} ({rB.get('risk_level')})")

print("\n============================================================")
print("  TEST C: Change ONLY Authorization Status -> Not Verified")
print("============================================================")
reqC = dict(base_req)
reqC['authorization_status'] = 'Not Verified'
rC = httpx.post('http://localhost:8000/api/govern', json=reqC).json()
print(f"Decision: {rC.get('decision')} | Risk: {rC.get('risk_score')} ({rC.get('risk_level')})")

print("\n============================================================")
print("  TEST D: Change ONLY Target -> new-external-vendor")
print("============================================================")
reqD = dict(base_req)
reqD['target'] = 'new-external-vendor'
rD = httpx.post('http://localhost:8000/api/govern', json=reqD).json()
print(f"Decision: {rD.get('decision')} | Risk: {rD.get('risk_score')} ({rD.get('risk_level')})")

print("\n============================================================")
print("  TEST E: Change ONLY Role -> Junior Analyst")
print("============================================================")
reqE = dict(base_req)
reqE['role'] = 'Junior Analyst'
reqE['user_id'] = 'U004'
rE = httpx.post('http://localhost:8000/api/govern', json=reqE).json()
print(f"Decision: {rE.get('decision')} | Risk: {rE.get('risk_score')} ({rE.get('risk_level')})")

print("\n============================================================")
print("  TEST F: Confidential + Not Verified + public-endpoint-unauthorized")
print("============================================================")
reqF = dict(base_req)
reqF['data_classification'] = 'Confidential'
reqF['authorization_status'] = 'Not Verified'
reqF['target'] = 'public-endpoint-unauthorized'
rF = httpx.post('http://localhost:8000/api/govern', json=reqF).json()
print(f"Decision: {rF.get('decision')} | Risk: {rF.get('risk_score')} ({rF.get('risk_level')})")
