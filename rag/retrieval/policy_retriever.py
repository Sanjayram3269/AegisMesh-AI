import os, sys
from typing import Any

# Ensure backend directory is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.schemas.governance import PolicyEvidence
from rag.providers.local_provider import LocalProvider

async def retrieve_policy_context(action: str, context: dict = None) -> list[PolicyEvidence]:
    provider = LocalProvider()
    results = await provider.retrieve(action, context, top_k=5)
    
    evidence_list = []
    for res in results:
        evidence = PolicyEvidence(
            policy_id=res['policy_id'],
            policy_name=res['policy_name'],
            section=res['section'],
            text=res['text'],
            relevance_score=float(res['relevance_score']),
            source_file=res['source_file'],
            decision_action=res.get('decision_action', ''),
            priority=res.get('priority', '')
        )
        evidence_list.append(evidence)
        
    return evidence_list
