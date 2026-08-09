"""AegisMesh AI — Database Models for SQLite Persistence."""

from datetime import datetime, timezone
import json
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class DBAuditRecord(Base):
    __tablename__ = "audit_records"

    audit_id = Column(String, primary_key=True, index=True)
    request_id = Column(String, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user_id = Column(String, index=True)
    role = Column(String)
    action = Column(Text)
    target = Column(String)
    
    execution_id = Column(String, index=True, nullable=True)
    decision = Column(String)
    risk_score = Column(Integer)
    risk_level = Column(String)

    inherent_risk_json = Column(Text, default="{}")
    final_risk_json = Column(Text, default="{}")
    risk_reduction = Column(Integer, nullable=True)
    lifecycle_history_json = Column(Text, default="[]")
    
    explanation = Column(Text)
    recommended_action = Column(Text)
    
    policy_evidence_json = Column(Text, default="[]")
    agents_executed_json = Column(Text, default="[]")
    intent_json = Column(Text, default="{}")
    identity_json = Column(Text, default="{}")
    compliance_json = Column(Text, default="{}")
    risk_json = Column(Text, default="{}")
    review_json = Column(Text, default="{}")
    transformation_json = Column(Text, default="{}")
    
    human_review_required = Column(Boolean, default=False)
    human_review_status = Column(String, nullable=True)
    human_reviewer_id = Column(String, nullable=True)
    human_review_comments = Column(Text, nullable=True)
    
    llm_provider = Column(String, default="mock")


class DBPolicy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    policy_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    rule_definition = Column(Text, nullable=False)
    decision_action = Column(String, nullable=False, default="APPROVE")
    priority = Column(String, nullable=False, default="MEDIUM")
    status = Column(String, nullable=False, default="ACTIVE")
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = Column(String, default="system")


class DBPolicyAudit(Base):
    __tablename__ = "policy_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String, nullable=False)  # CREATED, UPDATED, ACTIVATED, DEACTIVATED, DELETED
    policy_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    old_value_json = Column(Text, nullable=True)
    new_value_json = Column(Text, nullable=True)
    user_id = Column(String, default="system")


class DBPolicyVersion(Base):
    __tablename__ = "policy_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    policy_id = Column(String, index=True, nullable=False)
    version = Column(Integer, nullable=False)
    snapshot_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = Column(String, default="system")


class DBPolicyChangeEvent(Base):
    __tablename__ = "policy_change_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, unique=True, index=True, nullable=False)
    policy_id = Column(String, index=True, nullable=False)
    version = Column(Integer, nullable=False)
    previous_version = Column(Integer, default=0)
    change_type = Column(String, nullable=False)
    impact_level = Column(String, nullable=False)
    impact_score = Column(Integer, nullable=False)
    
    old_snapshot_json = Column(Text, default="{}")
    new_snapshot_json = Column(Text, default="{}")
    report_json = Column(Text, default="{}")
    
    requires_human_review = Column(Boolean, default=False)
    human_review_status = Column(String, default="AUTO_ENFORCED")  # AUTO_ENFORCED, PENDING, APPROVED, REJECTED
    human_reviewer_id = Column(String, nullable=True)
    human_review_comments = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = Column(String, default="system")
