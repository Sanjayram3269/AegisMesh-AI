import os
import re
import logging
from typing import Any
from .base import RAGProvider

logger = logging.getLogger('aegismesh.rag')

class LocalProvider(RAGProvider):
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.data_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'rag', 'data')
        else:
            self.data_dir = data_dir
        
    def _load_policies(self):
        """Load ACTIVE policies dynamically from persistent database storage."""
        policies = []
        try:
            from app.database.db import SessionLocal
            from app.database.models import DBPolicy
            
            db = SessionLocal()
            try:
                db_policies = db.query(DBPolicy).filter(DBPolicy.status == "ACTIVE").all()
                for p in db_policies:
                    policies.append({
                        'policy_id': p.policy_id,
                        'policy_name': p.name,
                        'section': f"Rule (Priority: {p.priority})",
                        'text': f"{p.rule_definition} Decision Action: {p.decision_action}.",
                        'decision_action': p.decision_action,
                        'priority': p.priority,
                        'source_file': f"{p.policy_id}.db"
                    })
            finally:
                db.close()
        except Exception as err:
            logger.warning(f"Failed to load active policies from DB, falling back to files: {err}")

        if not policies:
            policies = self._load_policies_from_files()

        return policies

    def _load_policies_from_files(self):
        policies = []
        if not os.path.exists(self.data_dir):
            return policies
            
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.md'):
                filepath = os.path.join(self.data_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                policy_id = filename.replace('.md', '')
                policy_name = policy_id.replace('_', ' ').title()
                
                sections = re.split(r'\n## ', content)
                for i, section in enumerate(sections):
                    if i == 0:
                        section_name = "Introduction"
                        section_text = section.strip()
                    else:
                        lines = section.split('\n', 1)
                        section_name = lines[0].strip() if len(lines) > 0 else "Unknown Section"
                        section_text = lines[1].strip() if len(lines) > 1 else ""
                        
                    if section_text:
                        policies.append({
                            'policy_id': policy_id,
                            'policy_name': policy_name,
                            'section': section_name,
                            'text': section_text,
                            'decision_action': "APPROVE",
                            'priority': "MEDIUM",
                            'source_file': filename
                        })
        return policies
        
    async def retrieve(self, query: str, context: dict[str, Any] = None, top_k: int = 5) -> list[dict[str, Any]]:
        context = context or {}
        active_policies = self._load_policies()
        
        combined_text = f"{query} {context.get('target', '')} {context.get('data_classification', '')} {context.get('authorization_status', '')} {context.get('role', '')}".lower()
        query_words = set(re.findall(r'\w+', combined_text))
        
        target = str(context.get('target', '')).lower()
        classification = str(context.get('data_classification', '')).lower()
        auth_status = str(context.get('authorization_status', '')).lower()

        results = []
        for policy in active_policies:
            text_lower = policy['text'].lower()
            text_words = set(re.findall(r'\w+', text_lower))
            
            match_count = len(query_words.intersection(text_words))
            
            pid_lower = policy['policy_id'].lower()
            # Dynamic Context Boosting based on Intake Fields & Policy ID/Rules
            if ('confidential' in classification or 'restricted' in classification or 'pii' in classification) and ('pii' in pid_lower or 'transfer' in pid_lower or 'trn' in pid_lower):
                match_count += 6
            if ('external' in target or 'public' in target or 'vendor' in target or 'unauthorized' in target) and ('transfer' in pid_lower or 'trn' in pid_lower or 'hum' in pid_lower or 'approval' in pid_lower):
                match_count += 6
            if ('not verified' in auth_status or 'pending' in auth_status or 'unauthorized' in auth_status) and ('hum' in pid_lower or 'approval' in pid_lower or 'access' in pid_lower):
                match_count += 5
            if ('export' in query.lower() or 'database' in query.lower()) and ('min' in pid_lower or 'minimization' in pid_lower or 'access' in pid_lower):
                match_count += 4
                
            if match_count > 0:
                result = dict(policy)
                normalized_score = min(max(round(match_count / 14.0, 2), 0.15), 0.99)
                result['relevance_score'] = normalized_score
                results.append(result)
                
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results[:top_k]
