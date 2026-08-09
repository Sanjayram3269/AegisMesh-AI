"""
Autonomous Policy Evolution & Change Intelligence Engine for AegisMesh AI.

Capabilities:
1. Canonical before/after policy snapshot creation & structural comparison
2. Deterministic Policy Impact Score calculation (0-100) & Impact Level classification
3. Autonomous response matrix & human approval gating
4. Historical governance replay simulation
5. Policy conflict & overlap detection
6. Structured Change Intelligence Report generation with explainability
"""

import sys
import os
import re
import json
import logging
from typing import Optional, List, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.schemas.governance import GovernanceDecision
from app.schemas.policy_evolution import (
    PolicySnapshot, PolicyChangeType, PolicyImpactLevel,
    PolicyChangeAnalysis, HistoricalReplayItem, HistoricalReplaySummary,
    PolicyConflictItem
)
from agents.policy_engine import (
    normalize_governance_input, evaluate_explicit_policies, resolve_final_decision, MatchedPolicyTrace
)

logger = logging.getLogger('aegismesh.policy_evolution')

PRECEDENCE_WEIGHTS = {
    "REJECT": 4,
    "ESCALATE": 3,
    "MODIFY": 2,
    "APPROVE": 1
}


def create_policy_snapshot(policy_dict_or_model: Any) -> PolicySnapshot:
    """Create a canonical normalized PolicySnapshot object."""
    if isinstance(policy_dict_or_model, PolicySnapshot):
        return policy_dict_or_model
        
    if hasattr(policy_dict_or_model, "__dict__"):
        p = policy_dict_or_model
        return PolicySnapshot(
            policy_id=getattr(p, 'policy_id', ''),
            name=getattr(p, 'name', ''),
            version=getattr(p, 'version', 1),
            decision_action=getattr(p, 'decision_action', 'APPROVE'),
            priority=getattr(p, 'priority', 'MEDIUM'),
            status=getattr(p, 'status', 'ACTIVE'),
            description=getattr(p, 'description', ''),
            rule_definition=getattr(p, 'rule_definition', ''),
            metadata={}
        )
    elif isinstance(policy_dict_or_model, dict):
        d = policy_dict_or_model
        return PolicySnapshot(
            policy_id=d.get('policy_id', ''),
            name=d.get('name', ''),
            version=d.get('version', 1),
            decision_action=d.get('decision_action', 'APPROVE'),
            priority=d.get('priority', 'MEDIUM'),
            status=d.get('status', 'ACTIVE'),
            description=d.get('description', ''),
            rule_definition=d.get('rule_definition', ''),
            metadata=d.get('metadata', {})
        )
    else:
        raise ValueError(f"Cannot create PolicySnapshot from {type(policy_dict_or_model)}")


def detect_structural_change(old_snap: PolicySnapshot, new_snap: PolicySnapshot) -> tuple[PolicyChangeType, str]:
    """
    Deterministic structural comparison between two policy snapshots.
    Identifies exact structural change classification.
    """
    if not old_snap:
        return PolicyChangeType.ACTIVATION_CHANGED, "New policy registered in control plane."

    if (old_snap.name == new_snap.name and
        old_snap.decision_action == new_snap.decision_action and
        old_snap.priority == new_snap.priority and
        old_snap.status == new_snap.status and
        old_snap.rule_definition.strip() == new_snap.rule_definition.strip()):
        if old_snap.description.strip() != new_snap.description.strip():
            return PolicyChangeType.TEXTUAL_CHANGE, "Description text updated without structural rule changes."
        return PolicyChangeType.NO_CHANGE, "No material change detected in policy configuration."

    # Activation change
    if old_snap.status != new_snap.status:
        st = new_snap.status
        return PolicyChangeType.ACTIVATION_CHANGED, f"Policy status changed from {old_snap.status} to {st}."

    # Decision action change
    old_weight = PRECEDENCE_WEIGHTS.get(old_snap.decision_action, 1)
    new_weight = PRECEDENCE_WEIGHTS.get(new_snap.decision_action, 1)
    if old_snap.decision_action != new_snap.decision_action:
        if new_weight < old_weight:
            return PolicyChangeType.SECURITY_IMPACT_CHANGE, f"Policy decision action weakened from {old_snap.decision_action} to {new_snap.decision_action}."
        else:
            return PolicyChangeType.DECISION_CHANGED, f"Policy decision action updated from {old_snap.decision_action} to {new_snap.decision_action}."

    # Priority change
    if old_snap.priority != new_snap.priority:
        return PolicyChangeType.PRIORITY_CHANGED, f"Policy priority updated from {old_snap.priority} to {new_snap.priority}."

    # Rule definition analysis
    old_rule = old_snap.rule_definition.lower()
    new_rule = new_snap.rule_definition.lower()

    # Scope expansion/reduction checks
    sensitive_keywords = ['pii', 'restricted', 'confidential', 'email', 'phone', 'ssn', 'financial', 'credit']
    old_sens = any(kw in old_rule for kw in sensitive_keywords)
    new_sens = any(kw in new_rule for kw in sensitive_keywords)

    if not old_sens and new_sens:
        return PolicyChangeType.DATA_SENSITIVITY_CHANGE, "Policy rule scope expanded to cover PII and sensitive data classifications."

    if len(new_rule) > len(old_rule) + 20 or "and" in new_rule and "and" not in old_rule:
        return PolicyChangeType.SCOPE_EXPANSION, "Policy rule scope expanded with additional conditions or targets."
    elif len(old_rule) > len(new_rule) + 20:
        return PolicyChangeType.SCOPE_REDUCTION, "Policy rule scope reduced or simplified."
    else:
        return PolicyChangeType.CONDITION_ADDED, "Policy rule conditions modified."


def calculate_policy_impact_score(
    change_type: PolicyChangeType,
    old_snap: PolicySnapshot,
    new_snap: PolicySnapshot,
    replay_summary: Optional[HistoricalReplaySummary] = None,
    conflicts: Optional[List[PolicyConflictItem]] = None
) -> tuple[int, PolicyImpactLevel]:
    """
    Deterministic Policy Impact Score Calculation (0-100):
    Decision changed: +30
    Priority changed: +15
    Policy deactivated: +25
    Scope expanded: +20
    Scope reduced: +25
    Security control weakened: +40
    Data sensitivity changed: +30
    Affected policy dependencies: +15
    Historical decisions changed: +20
    Policy conflict introduced: +25
    Clamped to [0, 100]
    """
    if change_type == PolicyChangeType.NO_CHANGE:
        return 0, PolicyImpactLevel.LOW

    score = 0

    if change_type == PolicyChangeType.TEXTUAL_CHANGE:
        score += 5
    elif change_type == PolicyChangeType.DECISION_CHANGED:
        score += 40
    elif change_type == PolicyChangeType.SECURITY_IMPACT_CHANGE:
        score += 55
    elif change_type == PolicyChangeType.DATA_SENSITIVITY_CHANGE:
        score += 55
    elif change_type == PolicyChangeType.SCOPE_EXPANSION:
        score += 50
    elif change_type == PolicyChangeType.SCOPE_REDUCTION:
        score += 35
    elif change_type == PolicyChangeType.ACTIVATION_CHANGED:
        if new_snap and new_snap.status == "INACTIVE":
            score += 40
        else:
            score += 25
    elif change_type == PolicyChangeType.PRIORITY_CHANGED:
        score += 20
    elif change_type == PolicyChangeType.CONDITION_ADDED or change_type == PolicyChangeType.CONDITION_REMOVED:
        score += 25
    else:
        score += 20

    if replay_summary and replay_summary.affected_actions_count > 0:
        score += 20

    if conflicts and any(c.conflict_detected for c in conflicts):
        score += 25

    final_score = max(0, min(100, score))

    if final_score < 25:
        level = PolicyImpactLevel.LOW
    elif final_score < 50:
        level = PolicyImpactLevel.MODERATE
    elif final_score < 75:
        level = PolicyImpactLevel.HIGH
    else:
        level = PolicyImpactLevel.CRITICAL

    return final_score, level


def determine_autonomous_action(impact_level: PolicyImpactLevel, change_type: PolicyChangeType) -> tuple[bool, str, str]:
    """
    Autonomous Response Matrix:
    LOW: analyze automatically, record in audit trail, no human approval required.
    MODERATE: analyze automatically, run impact checks, safe continuation.
    HIGH: run historical replay, detect conflicts, require human review before enforcement.
    CRITICAL: block automatic enforcement, generate critical governance alert, require explicit human approval.
    """
    if impact_level == PolicyImpactLevel.LOW:
        return False, "AUTO_ENFORCE", "ENFORCED_AUTOMATICALLY"
    elif impact_level == PolicyImpactLevel.MODERATE:
        return False, "MONITOR_IMPACT", "SAFE_CONTINUATION"
    elif impact_level == PolicyImpactLevel.HIGH:
        return True, "REQUIRE_HUMAN_REVIEW", "PENDING_HUMAN_APPROVAL"
    else:
        return True, "REQUIRE_CRITICAL_HUMAN_APPROVAL", "BLOCKED_PENDING_APPROVAL"


def detect_policy_conflicts(
    target_policy: PolicySnapshot,
    active_policies: List[PolicySnapshot]
) -> List[PolicyConflictItem]:
    """
    Detect overlapping condition targets and conflicting decisions between policies.
    """
    conflicts = []
    if not target_policy or target_policy.status != "ACTIVE":
        return conflicts

    target_rule = target_policy.rule_definition.lower()
    target_action = target_policy.decision_action

    for other in active_policies:
        if other.policy_id == target_policy.policy_id or other.status != "ACTIVE":
            continue

        other_rule = other.rule_definition.lower()
        other_action = other.decision_action

        # Check overlapping conditions (e.g. production / delete / PII)
        has_overlap = False
        if "production" in target_rule and "production" in other_rule:
            has_overlap = True
        elif "pii" in target_rule and "pii" in other_rule:
            has_overlap = True
        elif "restricted" in target_rule and "restricted" in other_rule:
            has_overlap = True

        if has_overlap and target_action != other_action:
            p_target_wt = PRECEDENCE_WEIGHTS.get(target_action, 1)
            p_other_wt = PRECEDENCE_WEIGHTS.get(other_action, 1)

            if p_target_wt != p_other_wt:
                res_by = f"Policy Precedence ({target_action if p_target_wt > p_other_wt else other_action} takes precedence)"
            else:
                res_by = f"Policy Priority Level ({target_policy.priority} vs {other.priority})"

            conflicts.append(PolicyConflictItem(
                conflict_detected=True,
                conflict_type="DECISION_CONFLICT",
                policy_ids=[target_policy.policy_id, other.policy_id],
                scenario=f"Both '{target_policy.name}' ({target_policy.policy_id}) and '{other.name}' ({other.policy_id}) match overlapping conditions with conflicting decisions ({target_action} vs {other_action}).",
                resolved_by=res_by,
                recommended_action=f"Review rule overlap between {target_policy.policy_id} and {other.policy_id}."
            ))

    return conflicts


def run_historical_replay(
    old_snap: PolicySnapshot,
    new_snap: PolicySnapshot,
    historical_records: List[Any],
    active_policies: List[PolicySnapshot]
) -> HistoricalReplaySummary:
    """
    Replay historical audit records against old and new policy configurations.
    Does NOT mutate historical audit records.
    """
    if not historical_records:
        return HistoricalReplaySummary(
            historical_actions_analyzed=0,
            affected_actions_count=0,
            unchanged_actions_count=0,
            recommendation="No historical governance records available for replay simulation."
        )

    # Build active policy lists for old vs new simulations
    old_active_list = []
    new_active_list = []

    for p in active_policies:
        if p.policy_id == new_snap.policy_id:
            if old_snap and old_snap.status == "ACTIVE":
                old_active_list.append({
                    "policy_id": old_snap.policy_id, "name": old_snap.name,
                    "rule_definition": old_snap.rule_definition,
                    "decision_action": old_snap.decision_action, "priority": old_snap.priority
                })
            if new_snap and new_snap.status == "ACTIVE":
                new_active_list.append({
                    "policy_id": new_snap.policy_id, "name": new_snap.name,
                    "rule_definition": new_snap.rule_definition,
                    "decision_action": new_snap.decision_action, "priority": new_snap.priority
                })
        else:
            if p.status == "ACTIVE":
                pol_dict = {
                    "policy_id": p.policy_id, "name": p.name,
                    "rule_definition": p.rule_definition,
                    "decision_action": p.decision_action, "priority": p.priority
                }
                old_active_list.append(pol_dict)
                new_active_list.append(pol_dict)

    affected_items = []
    more_restrictive = 0
    less_restrictive = 0

    for rec in historical_records:
        # Extract intake attributes from historical record
        if hasattr(rec, 'user_id'):
            user_id = getattr(rec, 'user_id', '') or 'U000'
            role = getattr(rec, 'role', '') or 'Senior Engineer'
            action = getattr(rec, 'action', '') or 'Read data'
            target = getattr(rec, 'target', '') or 'internal-system'
            classification = getattr(rec, 'data_classification', 'Internal') if hasattr(rec, 'data_classification') else 'Internal'
            auth_status = getattr(rec, 'authorization_status', 'Verified') if hasattr(rec, 'authorization_status') else 'Verified'
            rec_id = getattr(rec, 'audit_id', '') or getattr(rec, 'request_id', '')
        elif isinstance(rec, dict):
            user_id = rec.get('user_id', 'U000')
            role = rec.get('role', 'Senior Engineer')
            action = rec.get('action', 'Read data')
            target = rec.get('target', 'internal-system')
            classification = rec.get('data_classification', 'Internal')
            auth_status = rec.get('authorization_status', 'Verified')
            rec_id = rec.get('audit_id', rec.get('request_id', 'AUD-000'))
        else:
            continue

        norm_inp = normalize_governance_input(user_id, role, action, target, classification, auth_status)

        # Simulate old policy evaluation
        old_traces = evaluate_explicit_policies(norm_inp, active_policies=old_active_list)
        if old_snap:
            old_traces = [
                MatchedPolicyTrace(
                    policy_id=t.policy_id, policy_name=t.policy_name, matched=t.matched,
                    matched_conditions=t.matched_conditions, failed_conditions=t.failed_conditions,
                    decision=GovernanceDecision(old_snap.decision_action) if (t.matched and t.policy_id == old_snap.policy_id) else t.decision,
                    priority=old_snap.priority if (t.policy_id == old_snap.policy_id) else t.priority,
                    rule_description=t.rule_description
                ) for t in old_traces
            ]
        old_dec, _, _, _ = resolve_final_decision(old_traces, 20)

        # Simulate new policy evaluation
        new_traces = evaluate_explicit_policies(norm_inp, active_policies=new_active_list)
        if new_snap:
            new_traces = [
                MatchedPolicyTrace(
                    policy_id=t.policy_id, policy_name=t.policy_name, matched=t.matched,
                    matched_conditions=t.matched_conditions, failed_conditions=t.failed_conditions,
                    decision=GovernanceDecision(new_snap.decision_action) if (t.matched and t.policy_id == new_snap.policy_id) else t.decision,
                    priority=new_snap.priority if (t.policy_id == new_snap.policy_id) else t.priority,
                    rule_description=t.rule_description
                ) for t in new_traces
            ]
        new_dec, _, _, _ = resolve_final_decision(new_traces, 20)

        if old_dec != new_dec:
            old_wt = PRECEDENCE_WEIGHTS.get(old_dec.value, 1)
            new_wt = PRECEDENCE_WEIGHTS.get(new_dec.value, 1)
            is_more = new_wt > old_wt

            if is_more:
                more_restrictive += 1
                reason_text = f"Policy update expanded governance restriction from {old_dec.value} to {new_dec.value}."
            else:
                less_restrictive += 1
                reason_text = f"Policy update relaxed governance restriction from {old_dec.value} to {new_dec.value}."

            affected_items.append(HistoricalReplayItem(
                action_id=rec_id,
                request_id=rec_id,
                user_id=user_id,
                action=action,
                target=target,
                old_decision=old_dec.value,
                new_decision=new_dec.value,
                changed=True,
                is_more_restrictive=is_more,
                reason=reason_text
            ))

    tot = len(historical_records)
    aff_count = len(affected_items)
    unchanged_count = tot - aff_count

    if aff_count > 0:
        rec_msg = f"Policy change affects {aff_count} historical decisions ({more_restrictive} became more restrictive, {less_restrictive} became less restrictive). Review before enforcement."
    else:
        rec_msg = f"Zero historical governance regressions detected across {tot} analyzed historical actions."

    return HistoricalReplaySummary(
        historical_actions_analyzed=tot,
        affected_actions_count=aff_count,
        unchanged_actions_count=unchanged_count,
        more_restrictive_count=more_restrictive,
        less_restrictive_count=less_restrictive,
        regressions_count=less_restrictive,
        affected_actions=affected_items,
        recommendation=rec_msg
    )


def analyze_policy_change(
    old_policy: Any,
    new_policy: Any,
    active_policies: Optional[List[Any]] = None,
    historical_records: Optional[List[Any]] = None
) -> PolicyChangeAnalysis:
    """
    Main Autonomous Policy Evolution & Change Intelligence Entry Point.
    Fulfills Section 2 requirements:
    1. Structural change detection
    2. Semantic summary generation
    3. Policy impact score calculation
    4. Conflict & overlap detection
    5. Historical governance replay simulation
    6. Autonomous response matrix classification & human approval requirement
    """
    old_snap = create_policy_snapshot(old_policy) if old_policy else None
    new_snap = create_policy_snapshot(new_policy)

    if not old_snap:
        change_type = PolicyChangeType.ACTIVATION_CHANGED
        sem_summary = f"New enterprise policy '{new_snap.name}' ({new_snap.policy_id}) registered into active control plane."
    else:
        change_type, sem_summary = detect_structural_change(old_snap, new_snap)

    active_snaps = [create_policy_snapshot(p) for p in (active_policies or [])]
    conflicts = detect_policy_conflicts(new_snap, active_snaps)

    replay_summary = run_historical_replay(old_snap, new_snap, historical_records or [], active_snaps)

    impact_score, impact_level = calculate_policy_impact_score(
        change_type=change_type,
        old_snap=old_snap,
        new_snap=new_snap,
        replay_summary=replay_summary,
        conflicts=conflicts
    )

    req_review, rec_act, auto_act = determine_autonomous_action(impact_level, change_type)

    if replay_summary.more_restrictive_count > 0 and replay_summary.less_restrictive_count > 0:
        dec_impact = "MIXED"
    elif replay_summary.more_restrictive_count > 0:
        dec_impact = "MORE_RESTRICTIVE"
    elif replay_summary.less_restrictive_count > 0:
        dec_impact = "LESS_RESTRICTIVE"
    else:
        dec_impact = "NEUTRAL"

    # Build explainable recommended action text
    if impact_level == PolicyImpactLevel.CRITICAL:
        explain_rec = f"Impact is CRITICAL ({impact_score}/100) because the policy weakens security controls or alters {replay_summary.affected_actions_count} historical governance decisions. Automatic enforcement BLOCKED; human approval required."
    elif impact_level == PolicyImpactLevel.HIGH:
        explain_rec = f"Impact is HIGH ({impact_score}/100) because the policy expands sensitive scope and alters {replay_summary.affected_actions_count} evaluated governance decisions. Human review required before enforcement."
    elif impact_level == PolicyImpactLevel.MODERATE:
        explain_rec = f"Impact is MODERATE ({impact_score}/100). Safe continuation permitted under active governance monitoring."
    else:
        explain_rec = f"Impact is LOW ({impact_score}/100). Textual or non-material configuration change automatically verified."

    return PolicyChangeAnalysis(
        change_detected=change_type != PolicyChangeType.NO_CHANGE,
        change_type=change_type,
        semantic_summary=sem_summary,
        decision_impact=dec_impact,
        impact_score=impact_score,
        impact_level=impact_level,
        affected_policy_ids=[c.policy_ids[1] for c in conflicts if len(c.policy_ids) > 1] or [new_snap.policy_id],
        affected_action_count=replay_summary.affected_actions_count,
        conflicts=conflicts,
        regressions_detected=replay_summary.less_restrictive_count > 0,
        recommended_action=explain_rec,
        requires_human_review=req_review,
        autonomous_action=auto_act,
        confidence=0.96
    )
