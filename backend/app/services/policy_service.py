"""Policy Service for managing persistent database policies and seeding baseline rules."""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from app.database.models import DBPolicy, DBPolicyAudit
from app.schemas.policy import PolicyCreate, PolicyUpdate, PolicyStatus, PolicyPriority, PolicyDecisionAction

logger = logging.getLogger('aegismesh.policy')

DEFAULT_POLICIES = [
    {
        "policy_id": "POL-HUM-001",
        "name": "Human Approval Policy",
        "description": "Requires explicit human approval for high-risk actions, unverified roles, or transfers to unapproved external endpoints.",
        "rule_definition": "Risk Score >= 70 requires CISO or VP-level authorization. Transfers to unapproved external endpoints require explicit human review.",
        "decision_action": "ESCALATE",
        "priority": "HIGH",
        "status": "ACTIVE",
        "created_by": "system"
    },
    {
        "policy_id": "POL-TRN-002",
        "name": "Data Transfer Policy",
        "description": "Prohibits exporting Confidential or Restricted data to unauthorized public endpoints.",
        "rule_definition": "Confidential or Restricted data cannot be sent to unapproved public endpoints. Prohibited transfers result in immediate REJECT decision.",
        "decision_action": "REJECT",
        "priority": "CRITICAL",
        "status": "ACTIVE",
        "created_by": "system"
    },
    {
        "policy_id": "POL-PII-003",
        "name": "PII Protection Policy",
        "description": "Requires stripping or anonymizing customer PII fields before external transfer.",
        "rule_definition": "Customer records containing email or phone numbers must be anonymized before external transfer. The Transformation Agent applies automated field stripping.",
        "decision_action": "MODIFY",
        "priority": "MEDIUM",
        "status": "ACTIVE",
        "created_by": "system"
    },
    {
        "policy_id": "POL-ACC-006",
        "name": "Production System Access Control Policy",
        "description": "Governs access, modifications, and deployments to production environment systems based on role clearance, environment, and verification status.",
        "rule_definition": "IF target.environment = PRODUCTION AND action.type IN [DELETE, MODIFY, DEPLOY, CONFIGURE] AND authorization.status != VERIFIED THEN decision = ESCALATE.\nIF target.environment = PRODUCTION AND requester.role IN [INTERN, JUNIOR, CONTRACTOR] AND action.type IN [DELETE, MODIFY, DEPLOY, CONFIGURE] THEN decision = REJECT.\nIF target.environment = PRODUCTION AND authorization.status = VERIFIED AND requester.role IN [ADMIN, ENGINEER, MANAGER] AND action.type IN [DEPLOY, CONFIGURE] THEN decision = APPROVE.",
        "decision_action": "APPROVE",
        "priority": "HIGH",
        "status": "ACTIVE",
        "created_by": "system"
    },
    {
        "policy_id": "POL-FIN-006",
        "name": "Financial Data Access and Transfer Policy",
        "description": "Governs financial reporting, data export, and update operations on sensitive financial datasets.",
        "rule_definition": "IF data = RESTRICTED AND auth = VERIFIED AND role = FINANCE_MANAGER AND target.trust = HIGH THEN decision = APPROVE.\nIF data = RESTRICTED AND action = UPDATE THEN decision = MODIFY.\nIF auth = PENDING THEN decision = ESCALATE.\nIF target = PUBLIC THEN decision = REJECT.",
        "decision_action": "APPROVE",
        "priority": "HIGH",
        "status": "ACTIVE",
        "created_by": "system"
    },
    {
        "policy_id": "POL-MIN-004",
        "name": "Data Minimization Policy",
        "description": "Prohibits bulk database exports and mandates aggregated analytics views.",
        "rule_definition": "Full database exports are prohibited. Data transfers must use filtered views or aggregated metrics.",
        "decision_action": "MODIFY",
        "priority": "LOW",
        "status": "ACTIVE",
        "created_by": "system"
    }
]


def seed_default_policies(db: Session) -> None:
    """Seed baseline enterprise policies if they do not exist."""
    try:
        for pdata in DEFAULT_POLICIES:
            existing = db.query(DBPolicy).filter(DBPolicy.policy_id == pdata["policy_id"]).first()
            if not existing:
                policy = DBPolicy(
                    policy_id=pdata["policy_id"],
                    name=pdata["name"],
                    description=pdata["description"],
                    rule_definition=pdata["rule_definition"],
                    decision_action=pdata["decision_action"],
                    priority=pdata["priority"],
                    status=pdata["status"],
                    version=1,
                    created_by=pdata["created_by"]
                )
                db.add(policy)
                
                # Log audit creation event
                audit = DBPolicyAudit(
                    event_type="CREATED",
                    policy_id=pdata["policy_id"],
                    new_value_json=json.dumps(pdata),
                    user_id="system"
                )
                db.add(audit)

        db.commit()
        logger.info("Default enterprise policies successfully verified/seeded in database.")
    except Exception as err:
        db.rollback()
        logger.error(f"Error seeding default policies: {err}")


def get_all_policies(db: Session) -> List[DBPolicy]:
    """Retrieve all policies sorted by ID."""
    return db.query(DBPolicy).order_by(DBPolicy.id.asc()).all()


def get_active_policies(db: Session) -> List[DBPolicy]:
    """Retrieve only ACTIVE policies for RAG and governance evaluation."""
    return db.query(DBPolicy).filter(DBPolicy.status == "ACTIVE").order_by(DBPolicy.id.asc()).all()


def get_policy_by_id(db: Session, policy_id: str) -> Optional[DBPolicy]:
    """Retrieve a single policy by policy_id."""
    return db.query(DBPolicy).filter(DBPolicy.policy_id == policy_id).first()


def create_policy(db: Session, data: PolicyCreate) -> DBPolicy:
    """Create a new policy in persistent storage and record policy evolution analysis."""
    existing = db.query(DBPolicy).filter(DBPolicy.policy_id == data.policy_id).first()
    if existing:
        raise ValueError(f"Policy with ID '{data.policy_id}' already exists.")

    policy = DBPolicy(
        policy_id=data.policy_id,
        name=data.name,
        description=data.description or "",
        rule_definition=data.rule_definition,
        decision_action=data.decision_action.value if hasattr(data.decision_action, 'value') else str(data.decision_action),
        priority=data.priority.value if hasattr(data.priority, 'value') else str(data.priority),
        status=data.status.value if hasattr(data.status, 'value') else str(data.status),
        version=1,
        created_by=data.created_by
    )
    db.add(policy)
    db.flush()

    audit = DBPolicyAudit(
        event_type="CREATED",
        policy_id=policy.policy_id,
        new_value_json=json.dumps({
            "name": policy.name,
            "rule_definition": policy.rule_definition,
            "decision_action": policy.decision_action,
            "priority": policy.priority,
            "status": policy.status
        }),
        user_id=data.created_by
    )
    db.add(audit)
    db.commit()
    
    # Re-query directly from database to guarantee fresh persistence
    persisted = db.query(DBPolicy).filter(DBPolicy.policy_id == data.policy_id).first()

    # Record Policy Version & Evolution Analysis
    try:
        from app.services.policy_version_service import save_policy_version_and_event
        save_policy_version_and_event(db, persisted, old_state_dict=None, changed_fields=["policy_id", "name", "rule_definition"], user_id=data.created_by)
    except Exception as ev_err:
        logger.warning(f"Failed to record evolution analysis on create: {ev_err}")

    return persisted


def update_policy(db: Session, policy_id: str, data: PolicyUpdate) -> DBPolicy:
    """Update an existing policy, increment version ONLY if meaningful fields change, and run change intelligence analysis."""
    policy = db.query(DBPolicy).filter(DBPolicy.policy_id == policy_id).first()
    if not policy:
        raise KeyError(f"Policy '{policy_id}' not found.")

    old_state = {
        "id": policy.id,
        "policy_id": policy.policy_id,
        "name": policy.name,
        "description": policy.description or "",
        "rule_definition": policy.rule_definition,
        "decision_action": policy.decision_action,
        "priority": policy.priority,
        "status": policy.status,
        "version": policy.version
    }

    # Detect meaningful changes
    changed_fields = []
    if data.name is not None and data.name.strip() != policy.name:
        changed_fields.append("name")
    if data.description is not None and data.description.strip() != (policy.description or ""):
        changed_fields.append("description")
    if data.rule_definition is not None and data.rule_definition.strip() != policy.rule_definition.strip():
        changed_fields.append("rule_definition")
    if data.decision_action is not None:
        val = data.decision_action.value if hasattr(data.decision_action, 'value') else str(data.decision_action)
        if val != policy.decision_action:
            changed_fields.append("decision_action")
    if data.priority is not None:
        val = data.priority.value if hasattr(data.priority, 'value') else str(data.priority)
        if val != policy.priority:
            changed_fields.append("priority")
    if data.status is not None:
        val = data.status.value if hasattr(data.status, 'value') else str(data.status)
        if val != policy.status:
            changed_fields.append("status")

    # If NO meaningful change occurred, return existing policy directly without incrementing version or creating duplicate events
    if not changed_fields:
        return policy

    # Apply changes
    if "name" in changed_fields:
        policy.name = data.name.strip()
    if "description" in changed_fields:
        policy.description = data.description.strip()
    if "rule_definition" in changed_fields:
        policy.rule_definition = data.rule_definition.strip()
    if "decision_action" in changed_fields:
        policy.decision_action = data.decision_action.value if hasattr(data.decision_action, 'value') else str(data.decision_action)
    if "priority" in changed_fields:
        policy.priority = data.priority.value if hasattr(data.priority, 'value') else str(data.priority)
    if "status" in changed_fields:
        policy.status = data.status.value if hasattr(data.status, 'value') else str(data.status)

    policy.version += 1
    policy.updated_at = datetime.now(timezone.utc)

    new_state = {
        "id": policy.id,
        "policy_id": policy.policy_id,
        "name": policy.name,
        "description": policy.description,
        "rule_definition": policy.rule_definition,
        "decision_action": policy.decision_action,
        "priority": policy.priority,
        "status": policy.status,
        "version": policy.version
    }

    audit = DBPolicyAudit(
        event_type="UPDATED",
        policy_id=policy.policy_id,
        old_value_json=json.dumps(old_state),
        new_value_json=json.dumps(new_state),
        user_id="admin"
    )
    db.add(audit)
    db.commit()
    
    # Re-query directly from database to guarantee fresh persistence
    persisted = db.query(DBPolicy).filter(DBPolicy.policy_id == policy_id).first()

    # Record Policy Version & Evolution Analysis
    try:
        from app.services.policy_version_service import save_policy_version_and_event
        save_policy_version_and_event(db, persisted, old_state_dict=old_state, changed_fields=changed_fields, user_id="admin")
    except Exception as ev_err:
        logger.warning(f"Failed to record evolution analysis on update: {ev_err}")

    return persisted


def update_policy_status(db: Session, policy_id: str, status: str) -> DBPolicy:
    """Activate, deactivate, or set draft status for a policy."""
    policy = db.query(DBPolicy).filter(DBPolicy.policy_id == policy_id).first()
    if not policy:
        raise KeyError(f"Policy '{policy_id}' not found.")

    new_status = status.upper()
    if policy.status == new_status:
        return policy

    old_status = policy.status
    old_state = {
        "id": policy.id,
        "policy_id": policy.policy_id,
        "name": policy.name,
        "description": policy.description or "",
        "rule_definition": policy.rule_definition,
        "decision_action": policy.decision_action,
        "priority": policy.priority,
        "status": old_status,
        "version": policy.version
    }

    policy.status = new_status
    policy.version += 1
    policy.updated_at = datetime.now(timezone.utc)

    event_type = "ACTIVATED" if policy.status == "ACTIVE" else "DEACTIVATED" if policy.status == "INACTIVE" else "UPDATED"

    audit = DBPolicyAudit(
        event_type=event_type,
        policy_id=policy.policy_id,
        old_value_json=json.dumps({"status": old_status}),
        new_value_json=json.dumps({"status": policy.status}),
        user_id="admin"
    )
    db.add(audit)
    db.commit()
    
    # Re-query directly from database to guarantee fresh persistence
    persisted = db.query(DBPolicy).filter(DBPolicy.policy_id == policy_id).first()

    # Record Policy Version & Evolution Analysis
    try:
        from app.services.policy_version_service import save_policy_version_and_event
        save_policy_version_and_event(db, persisted, old_state_dict=old_state, changed_fields=["status"], user_id="admin")
    except Exception as ev_err:
        logger.warning(f"Failed to record evolution analysis on status change: {ev_err}")

    return persisted


def delete_policy(db: Session, policy_id: str) -> bool:
    """Delete a policy from persistent database storage."""
    policy = db.query(DBPolicy).filter(DBPolicy.policy_id == policy_id).first()
    if not policy:
        raise KeyError(f"Policy '{policy_id}' not found.")

    old_state = {
        "policy_id": policy.policy_id,
        "name": policy.name,
        "rule_definition": policy.rule_definition,
        "status": policy.status
    }

    audit = DBPolicyAudit(
        event_type="DELETED",
        policy_id=policy_id,
        old_value_json=json.dumps(old_state),
        user_id="admin"
    )
    db.add(audit)
    db.delete(policy)
    db.commit()
    return True
