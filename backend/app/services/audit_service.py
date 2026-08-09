"""Audit Service for AegisMesh AI with SQLite Persistence."""

import json
import logging
from typing import Optional
from datetime import datetime, timezone
import sys, os

# Ensure backend directory is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.schemas.governance import AuditRecord, GovernanceDecision, HumanReviewAction, RiskLevel
from app.database.db import SessionLocal, init_db
from app.database.models import DBAuditRecord

logger = logging.getLogger(__name__)

# Initialize database tables on startup
try:
    init_db()
except Exception as e:
    logger.warning(f"Database initialization warning: {e}")

class AuditService:
    """Manages audit record persistence to SQLite database with in-memory cache."""
    
    _memory_cache: dict[str, AuditRecord] = {}
    
    def save_record(self, record: AuditRecord) -> None:
        self._memory_cache[record.request_id] = record
        
        try:
            db = SessionLocal()
            try:
                db_record = DBAuditRecord(
                    audit_id=record.audit_id,
                    request_id=record.request_id,
                    timestamp=record.timestamp,
                    user_id=record.user_id,
                    role=record.role,
                    action=record.action,
                    target=record.target,
                    decision=record.decision.value if record.decision else "ESCALATE",
                    risk_score=record.risk_score,
                    risk_level=record.risk_level.value if record.risk_level else "HIGH",
                    explanation=record.explainability.summary if record.explainability else "",
                    recommended_action="",
                    policy_evidence_json=json.dumps([e.model_dump() for e in record.policy_evidence]),
                    agents_executed_json=json.dumps([a.model_dump() for a in record.agents_executed], default=str),
                    intent_json=json.dumps(record.intent.model_dump() if record.intent else {}),
                    identity_json=json.dumps(record.identity.model_dump() if record.identity else {}),
                    compliance_json=json.dumps(record.compliance.model_dump() if record.compliance else {}),
                    risk_json=json.dumps(record.risk.model_dump() if record.risk else {}),
                    review_json=json.dumps(record.review.model_dump() if record.review else {}),
                    transformation_json=json.dumps(record.transformation.model_dump() if record.transformation else {}),
                    human_review_required=record.human_review_required,
                    human_review_status=record.human_review_status,
                    human_reviewer_id=record.human_reviewer_id,
                    human_review_comments=record.human_review_comments,
                    llm_provider=record.llm_provider,
                )
                db.merge(db_record)
                db.commit()
                logger.info(f"Audit record persisted to SQLite: {record.audit_id} for request {record.request_id}")
            except Exception as ex:
                db.rollback()
                logger.warning(f"Failed to persist audit to DB (using in-memory): {ex}")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"DB session error: {e}")

    def get_record(self, request_id: str) -> Optional[AuditRecord]:
        if request_id in self._memory_cache:
            return self._memory_cache[request_id]
            
        try:
            db = SessionLocal()
            try:
                db_record = db.query(DBAuditRecord).filter(DBAuditRecord.request_id == request_id).first()
                if db_record:
                    return AuditRecord(
                        audit_id=db_record.audit_id,
                        request_id=db_record.request_id,
                        timestamp=db_record.timestamp,
                        user_id=db_record.user_id,
                        role=db_record.role,
                        action=db_record.action,
                        target=db_record.target,
                        decision=GovernanceDecision(db_record.decision),
                        risk_score=db_record.risk_score,
                        risk_level=RiskLevel(db_record.risk_level),
                        human_review_required=db_record.human_review_required or False,
                        human_review_status=db_record.human_review_status,
                        human_reviewer_id=db_record.human_reviewer_id,
                        human_review_comments=db_record.human_review_comments,
                        llm_provider=db_record.llm_provider or "mock",
                    )
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Error querying audit record: {e}")
            
        return None

    def list_records(self) -> list[AuditRecord]:
        cached = list(self._memory_cache.values())
        if cached:
            return cached
            
        records = []
        try:
            db = SessionLocal()
            try:
                db_records = db.query(DBAuditRecord).order_by(DBAuditRecord.timestamp.desc()).limit(100).all()
                for db_record in db_records:
                    rec = AuditRecord(
                        audit_id=db_record.audit_id,
                        request_id=db_record.request_id,
                        timestamp=db_record.timestamp,
                        user_id=db_record.user_id,
                        role=db_record.role,
                        action=db_record.action,
                        target=db_record.target,
                        decision=GovernanceDecision(db_record.decision) if db_record.decision in GovernanceDecision.__members__ else GovernanceDecision.ESCALATE,
                        risk_score=db_record.risk_score or 0,
                        risk_level=RiskLevel(db_record.risk_level) if db_record.risk_level in RiskLevel.__members__ else RiskLevel.HIGH,
                        human_review_required=db_record.human_review_required or False,
                        human_review_status=db_record.human_review_status,
                        human_reviewer_id=db_record.human_reviewer_id,
                        human_review_comments=db_record.human_review_comments,
                        llm_provider=db_record.llm_provider or "mock",
                    )
                    records.append(rec)
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Error listing audit records from DB: {e}")
            
        return records

    def update_human_review(
        self,
        request_id: str,
        reviewer_id: str,
        action: HumanReviewAction,
        comments: str = "",
        updated_decision: Optional[GovernanceDecision] = None,
    ) -> Optional[AuditRecord]:
        record = self.get_record(request_id)
        if record:
            record.human_review_status = action.value
            record.human_reviewer_id = reviewer_id
            record.human_review_comments = comments
            if updated_decision:
                record.decision = updated_decision
            self._memory_cache[request_id] = record
            
            try:
                db = SessionLocal()
                try:
                    db_record = db.query(DBAuditRecord).filter(DBAuditRecord.request_id == request_id).first()
                    if db_record:
                        db_record.human_review_status = action.value
                        db_record.human_reviewer_id = reviewer_id
                        db_record.human_review_comments = comments
                        if updated_decision:
                            db_record.decision = updated_decision.value
                        db.commit()
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"Error updating human review in DB: {e}")
                
        return record
