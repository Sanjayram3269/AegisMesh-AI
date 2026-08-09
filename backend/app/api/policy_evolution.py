"""
FastAPI Router for AegisMesh AI Autonomous Policy Evolution & Change Intelligence.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import DBPolicy, DBAuditRecord
from app.schemas.policy_evolution import (
    PolicySnapshot, PolicyChangeAnalysis, PolicyEvolutionReport,
    HistoricalReplaySummary, PolicyEvolutionKPICards, PolicyEnforcementApproval
)
from app.services import policy_version_service, policy_service
from agents.policy_evolution import (
    create_policy_snapshot, analyze_policy_change, run_historical_replay, detect_policy_conflicts
)

logger = logging.getLogger('aegismesh.api.policy_evolution')

router = APIRouter(prefix="/api/policy-evolution", tags=["Policy Evolution"])


@router.get("/kpi", response_model=PolicyEvolutionKPICards)
def get_kpi_cards(db: Session = Depends(get_db)):
    """Retrieve top KPI summary metrics for Policy Evolution dashboard."""
    return policy_version_service.get_evolution_kpi_cards(db)


@router.get("/events")
def get_change_events(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    """Retrieve recent policy change events timeline."""
    events = policy_version_service.get_all_change_events(db, limit=limit)
    results = []
    for ev in events:
        report_data = json.loads(ev.report_json) if ev.report_json else {}
        results.append({
            "event_id": ev.event_id,
            "policy_id": ev.policy_id,
            "version": ev.version,
            "previous_version": ev.previous_version,
            "change_type": ev.change_type,
            "impact_level": ev.impact_level,
            "impact_score": ev.impact_score,
            "requires_human_review": ev.requires_human_review,
            "human_review_status": ev.human_review_status,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
            "old_snapshot": json.loads(ev.old_snapshot_json) if ev.old_snapshot_json else {},
            "new_snapshot": json.loads(ev.new_snapshot_json) if ev.new_snapshot_json else {},
            "analysis": report_data.get("analysis", {}),
            "replay_summary": report_data.get("replay_summary", {})
        })
    return {"total": len(results), "events": results}


@router.get("/history/{policy_id}")
def get_policy_version_history(policy_id: str, db: Session = Depends(get_db)):
    """Retrieve version history snapshots for a given policy_id."""
    versions = policy_version_service.get_policy_versions(db, policy_id)
    results = []
    for v in versions:
        results.append({
            "id": v.id,
            "policy_id": v.policy_id,
            "version": v.version,
            "snapshot": json.loads(v.snapshot_json) if v.snapshot_json else {},
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "created_by": v.created_by
        })
    return {"policy_id": policy_id, "total_versions": len(results), "versions": results}


@router.get("/event/{event_id}")
def get_change_event_detail(event_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed Policy Change Intelligence Report for a specific event."""
    ev = policy_version_service.get_change_event_by_id(db, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Change event '{event_id}' not found.")

    report_data = json.loads(ev.report_json) if ev.report_json else {}
    return {
        "event_id": ev.event_id,
        "policy_id": ev.policy_id,
        "version": ev.version,
        "previous_version": ev.previous_version,
        "change_type": ev.change_type,
        "impact_level": ev.impact_level,
        "impact_score": ev.impact_score,
        "requires_human_review": ev.requires_human_review,
        "human_review_status": ev.human_review_status,
        "human_reviewer_id": ev.human_reviewer_id,
        "human_review_comments": ev.human_review_comments,
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
        "old_snapshot": json.loads(ev.old_snapshot_json) if ev.old_snapshot_json else {},
        "new_snapshot": json.loads(ev.new_snapshot_json) if ev.new_snapshot_json else {},
        "report": report_data
    }


@router.get("/conflicts")
def get_policy_conflicts(db: Session = Depends(get_db)):
    """Detect active policy overlaps and conflicts across all active policies."""
    conflicts = policy_version_service.get_active_conflicts(db)
    return {"total": len(conflicts), "conflicts": conflicts}


@router.post("/analyze-change")
def analyze_proposed_policy_change(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Preview & analyze a proposed policy change before saving.
    Payload format: { "old_policy": {...}, "new_policy": {...} }
    """
    old_p = payload.get("old_policy")
    new_p = payload.get("new_policy")

    if not new_p:
        raise HTTPException(status_code=400, detail="Missing 'new_policy' object in payload.")

    all_db_policies = db.query(DBPolicy).all()
    active_snaps = [create_policy_snapshot({
        "policy_id": p.policy_id, "name": p.name, "version": p.version,
        "decision_action": p.decision_action, "priority": p.priority,
        "status": p.status, "description": p.description or "",
        "rule_definition": p.rule_definition
    }) for p in all_db_policies]

    historical_audits = db.query(DBAuditRecord).order_by(DBAuditRecord.timestamp.desc()).limit(100).all()

    old_snap = create_policy_snapshot(old_p) if old_p else None
    new_snap = create_policy_snapshot(new_p)

    analysis = analyze_policy_change(old_snap, new_snap, active_snaps, historical_audits)
    replay = run_historical_replay(old_snap, new_snap, historical_audits, active_snaps)

    return {
        "analysis": analysis.dict(),
        "replay_summary": replay.dict()
    }


@router.post("/approve-enforcement")
def approve_enforcement(data: PolicyEnforcementApproval, db: Session = Depends(get_db)):
    """Approve or reject a high-impact or critical policy change enforcement."""
    try:
        updated_event = policy_version_service.approve_policy_enforcement(db, data)
        return {
            "status": "success",
            "event_id": updated_event.event_id,
            "human_review_status": updated_event.human_review_status,
            "reviewer_id": updated_event.human_reviewer_id,
            "message": f"Policy enforcement status updated to {updated_event.human_review_status}."
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
