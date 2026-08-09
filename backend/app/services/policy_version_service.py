"""
Policy Version Service for AegisMesh AI Autonomous Policy Evolution & Change Intelligence.

Manages:
- Database policy version snapshots (DBPolicyVersion)
- Policy change event analytics & reports (DBPolicyChangeEvent)
- Historical audit replay simulations
- Human review enforcement approval workflows
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.database.models import DBPolicy, DBAuditRecord, DBPolicyVersion, DBPolicyChangeEvent
from app.schemas.policy_evolution import (
    PolicySnapshot, PolicyChangeAnalysis, PolicyEvolutionReport,
    HistoricalReplaySummary, PolicyEvolutionKPICards, PolicyEnforcementApproval
)
from agents.policy_evolution import (
    create_policy_snapshot, analyze_policy_change, run_historical_replay, detect_policy_conflicts
)

logger = logging.getLogger('aegismesh.policy_version')


def save_policy_version_and_event(
    db: Session,
    policy: DBPolicy,
    old_state_dict: Optional[Dict[str, Any]] = None,
    changed_fields: Optional[List[str]] = None,
    user_id: str = "system"
) -> Optional[DBPolicyChangeEvent]:
    """
    Called whenever a policy is created, updated, activated, or deactivated.
    Preserves old/new canonical snapshots, performs evolution analysis, runs historical replay,
    and persists the change event.
    """
    # Build new snapshot
    new_snapshot_dict = {
        "policy_id": policy.policy_id,
        "name": policy.name,
        "version": policy.version,
        "decision_action": policy.decision_action,
        "priority": policy.priority,
        "status": policy.status,
        "description": policy.description or "",
        "rule_definition": policy.rule_definition,
        "metadata": {"created_by": policy.created_by or user_id}
    }
    new_snap = create_policy_snapshot(new_snapshot_dict)

    # Build old snapshot
    if old_state_dict:
        old_snapshot_dict = {
            "policy_id": policy.policy_id,
            "name": old_state_dict.get("name", policy.name),
            "version": old_state_dict.get("version", policy.version - 1),
            "decision_action": old_state_dict.get("decision_action", policy.decision_action),
            "priority": old_state_dict.get("priority", policy.priority),
            "status": old_state_dict.get("status", "ACTIVE"),
            "description": old_state_dict.get("description", ""),
            "rule_definition": old_state_dict.get("rule_definition", policy.rule_definition),
            "metadata": {}
        }
        old_snap = create_policy_snapshot(old_snapshot_dict)
    else:
        old_snap = None

    # Derive changed_fields if not provided
    if not changed_fields and old_snap:
        changed_fields = []
        if old_snap.name != new_snap.name: changed_fields.append("name")
        if old_snap.description != new_snap.description: changed_fields.append("description")
        if old_snap.rule_definition.strip() != new_snap.rule_definition.strip(): changed_fields.append("rule_definition")
        if old_snap.decision_action != new_snap.decision_action: changed_fields.append("decision_action")
        if old_snap.priority != new_snap.priority: changed_fields.append("priority")
        if old_snap.status != new_snap.status: changed_fields.append("status")

    # If updating an existing policy and no fields changed, skip event creation
    if old_snap and not changed_fields:
        logger.info(f"[POLICY EVOLUTION] No meaningful changes for {policy.policy_id}. Skipping event creation.")
        return None

    event_id = f"EVO-{uuid.uuid4().hex[:8].upper()}"

    # Save immutable version snapshot
    version_rec = DBPolicyVersion(
        policy_id=policy.policy_id,
        version=policy.version,
        snapshot_json=json.dumps(new_snapshot_dict),
        created_by=user_id
    )
    db.add(version_rec)

    # Retrieve all active policies for conflict & replay analysis
    all_db_policies = db.query(DBPolicy).all()
    active_snaps = [create_policy_snapshot({
        "policy_id": p.policy_id, "name": p.name, "version": p.version,
        "decision_action": p.decision_action, "priority": p.priority,
        "status": p.status, "description": p.description or "",
        "rule_definition": p.rule_definition
    }) for p in all_db_policies]

    # Retrieve historical audit records for replay simulation
    historical_audits = db.query(DBAuditRecord).order_by(DBAuditRecord.timestamp.desc()).limit(100).all()

    # Perform Autonomous Evolution Analysis
    analysis: PolicyChangeAnalysis = analyze_policy_change(
        old_policy=old_snap,
        new_policy=new_snap,
        active_policies=active_snaps,
        historical_records=historical_audits
    )

    replay_summary: HistoricalReplaySummary = run_historical_replay(
        old_snap=old_snap,
        new_snap=new_snap,
        historical_records=historical_audits,
        active_policies=active_snaps
    )

    # Determine review status
    if analysis.requires_human_review:
        review_status = "PENDING"
    else:
        review_status = "AUTO_ENFORCED"

    report_data = {
        "event_id": event_id,
        "policy_id": policy.policy_id,
        "policy_name": policy.name,
        "version": policy.version,
        "previous_version": old_snap.version if old_snap else 0,
        "changed_fields": changed_fields or [],
        "analysis": analysis.dict(),
        "replay_summary": replay_summary.dict()
    }

    change_event = DBPolicyChangeEvent(
        event_id=event_id,
        policy_id=policy.policy_id,
        version=policy.version,
        previous_version=old_snap.version if old_snap else 0,
        change_type=analysis.change_type.value,
        impact_level=analysis.impact_level.value,
        impact_score=analysis.impact_score,
        old_snapshot_json=json.dumps(old_snap.dict() if old_snap else {}),
        new_snapshot_json=json.dumps(new_snap.dict()),
        report_json=json.dumps(report_data),
        requires_human_review=analysis.requires_human_review,
        human_review_status=review_status,
        created_by=user_id
    )
    db.add(change_event)
    db.commit()
    db.refresh(change_event)

    logger.info(f"[POLICY EVOLUTION] Event {event_id} recorded for {policy.policy_id} v{policy.version} (Type: {analysis.change_type.value}, Impact: {analysis.impact_score}/100 - {analysis.impact_level.value})")
    return change_event


def get_policy_versions(db: Session, policy_id: str) -> List[DBPolicyVersion]:
    """Retrieve full version history for a given policy_id."""
    return db.query(DBPolicyVersion).filter(DBPolicyVersion.policy_id == policy_id).order_by(DBPolicyVersion.version.asc()).all()


def get_change_event_by_id(db: Session, event_id: str) -> Optional[DBPolicyChangeEvent]:
    """Retrieve a change event by event_id."""
    return db.query(DBPolicyChangeEvent).filter(DBPolicyChangeEvent.event_id == event_id).first()


def get_all_change_events(db: Session, limit: int = 50) -> List[DBPolicyChangeEvent]:
    """Retrieve recent policy change events."""
    return db.query(DBPolicyChangeEvent).order_by(DBPolicyChangeEvent.created_at.desc()).limit(limit).all()


def get_active_conflicts(db: Session) -> List[Dict[str, Any]]:
    """Scan all active policies in DB and detect conflicts."""
    all_db_policies = db.query(DBPolicy).filter(DBPolicy.status == "ACTIVE").all()
    snaps = [create_policy_snapshot({
        "policy_id": p.policy_id, "name": p.name, "version": p.version,
        "decision_action": p.decision_action, "priority": p.priority,
        "status": p.status, "description": p.description or "",
        "rule_definition": p.rule_definition
    }) for p in all_db_policies]

    all_conflicts = []
    seen = set()
    for s in snaps:
        conflicts = detect_policy_conflicts(s, snaps)
        for c in conflicts:
            key = tuple(sorted(c.policy_ids))
            if key not in seen:
                seen.add(key)
                all_conflicts.append(c.dict())
    return all_conflicts


def approve_policy_enforcement(db: Session, data: PolicyEnforcementApproval) -> DBPolicyChangeEvent:
    """Approve or reject a high-impact policy change enforcement."""
    event = db.query(DBPolicyChangeEvent).filter(DBPolicyChangeEvent.event_id == data.event_id).first()
    if not event:
        raise KeyError(f"Policy change event '{data.event_id}' not found.")

    if data.action.upper() == "APPROVE":
        event.human_review_status = "APPROVED"
    else:
        event.human_review_status = "REJECTED"

    event.human_reviewer_id = data.reviewer_id
    event.human_review_comments = data.comments
    db.commit()
    db.refresh(event)
    return event


def get_evolution_kpi_cards(db: Session) -> PolicyEvolutionKPICards:
    """Compute top KPI summary cards for the Policy Evolution dashboard."""
    active_count = db.query(DBPolicy).filter(DBPolicy.status == "ACTIVE").count()
    events_count = db.query(DBPolicyChangeEvent).count()
    review_count = db.query(DBPolicyChangeEvent).filter(DBPolicyChangeEvent.human_review_status == "PENDING").count()
    
    # Count critical regressions (impact >= 75 or regressions_detected)
    critical_count = db.query(DBPolicyChangeEvent).filter(
        (DBPolicyChangeEvent.impact_level == "CRITICAL") | 
        (DBPolicyChangeEvent.impact_score >= 75)
    ).count()

    return PolicyEvolutionKPICards(
        active_policies_count=active_count,
        policy_changes_detected=events_count,
        requires_human_review_count=review_count,
        critical_regressions_count=critical_count
    )
