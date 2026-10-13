"""CyberForge Policy-Change Intelligence & Regression Testing Engine.

Evaluates proposed policy changes by running adversarial and benign test suites
against both historical and proposed policy versions. Measures empirical changes
in authorization, newly introduced attack exposure, and security regressions.
"""

from dataclasses import dataclass, field
import difflib
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Tuple

from agents.adversarial.scenarios import SCENARIOS, AttackScenario
from agents.adversarial.engine import (
    ADVERSARIAL_ENGINE, ExecutionMode, ScenarioExecutionResult
)
from agents.enforcement.gateway import ENFORCEMENT_GATEWAY


@dataclass
class PolicyDiff:
    policy_id: str
    field_changes: Dict[str, Dict[str, Any]]
    unified_rule_diff: List[str]
    is_breaking_change: bool
    summary: str


@dataclass
class ScenarioComparisonItem:
    scenario_id: str
    scenario_name: str
    category: str
    severity: str
    is_benign: bool
    old_decision: str
    new_decision: str
    old_executed: bool
    new_executed: bool
    change_type: str  # REGRESSION, IMPROVEMENT, FALSE_POSITIVE_INTRODUCED, FALSE_POSITIVE_RESOLVED, NO_CHANGE
    risk_impact: str  # HIGH, MEDIUM, LOW, NEUTRAL
    details: str


@dataclass
class PolicyRegressionReport:
    policy_id: str
    old_version: int
    new_version: int
    timestamp: str
    diff: PolicyDiff
    total_evaluated: int
    
    # Behavioral Changes
    newly_permitted_actions: List[str]
    newly_denied_actions: List[str]
    approval_requirement_changes: List[str]
    
    # Security Metrics
    security_regressions: List[ScenarioComparisonItem]
    security_improvements: List[ScenarioComparisonItem]
    false_positives_introduced: List[ScenarioComparisonItem]
    false_positives_resolved: List[ScenarioComparisonItem]
    
    safe_to_deploy: bool
    overall_verdict: str
    scenario_comparisons: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "timestamp": self.timestamp,
            "diff": {
                "policy_id": self.diff.policy_id,
                "field_changes": self.diff.field_changes,
                "unified_rule_diff": self.diff.unified_rule_diff,
                "is_breaking_change": self.diff.is_breaking_change,
                "summary": self.diff.summary,
            },
            "total_evaluated": self.total_evaluated,
            "newly_permitted_actions": self.newly_permitted_actions,
            "newly_denied_actions": self.newly_denied_actions,
            "approval_requirement_changes": self.approval_requirement_changes,
            "regressions_count": len(self.security_regressions),
            "improvements_count": len(self.security_improvements),
            "false_positives_count": len(self.false_positives_introduced),
            "safe_to_deploy": self.safe_to_deploy,
            "overall_verdict": self.overall_verdict,
            "scenario_comparisons": self.scenario_comparisons,
        }


def compute_policy_diff(old_policy: Dict[str, Any], new_policy: Dict[str, Any]) -> PolicyDiff:
    """Computes precise semantic and textual diff between two policy states."""
    pid = new_policy.get("policy_id", old_policy.get("policy_id", "UNKNOWN"))
    field_changes: Dict[str, Dict[str, Any]] = {}

    keys_to_check = ["name", "description", "rule_definition", "decision_action", "priority", "status"]
    for k in keys_to_check:
        old_val = old_policy.get(k)
        new_val = new_policy.get(k)
        if old_val != new_val:
            field_changes[k] = {"old": old_val, "new": new_val}

    # Unified rule text diff
    old_rule = (old_policy.get("rule_definition") or "").splitlines(keepends=True)
    new_rule = (new_policy.get("rule_definition") or "").splitlines(keepends=True)
    diff_lines = list(difflib.unified_diff(old_rule, new_rule, fromfile="v_old", tofile="v_new", lineterm=""))

    # Breaking change detection
    is_breaking = False
    old_act = old_policy.get("decision_action", "APPROVE")
    new_act = new_policy.get("decision_action", "APPROVE")
    if old_act in ["REJECT", "MODIFY"] and new_act == "APPROVE":
        is_breaking = True
    elif old_policy.get("status") == "ACTIVE" and new_policy.get("status") == "INACTIVE":
        is_breaking = True

    summary = f"Policy '{pid}' modified {len(field_changes)} fields."
    if is_breaking:
        summary += " WARNING: Potential breaking loosening change detected."

    return PolicyDiff(
        policy_id=pid,
        field_changes=field_changes,
        unified_rule_diff=diff_lines,
        is_breaking_change=is_breaking,
        summary=summary,
    )


class PolicyRegressionTester:
    """Runs regression test suites across historical vs proposed policies."""

    def compare_policy_versions(
        self,
        policy_id: str,
        old_policy_dict: Dict[str, Any],
        new_policy_dict: Dict[str, Any],
        scenarios: Optional[List[AttackScenario]] = None,
    ) -> PolicyRegressionReport:
        target_scenarios = scenarios or SCENARIOS
        diff = compute_policy_diff(old_policy_dict, new_policy_dict)

        old_ver = old_policy_dict.get("version", 1)
        new_ver = new_policy_dict.get("version", old_ver + 1)

        # 1. Run scenarios against old policy state
        ENFORCEMENT_GATEWAY.set_active_policy_context(version=old_ver, db_policies=[old_policy_dict])
        old_results: Dict[str, ScenarioExecutionResult] = {}
        for sc in target_scenarios:
            old_results[sc.scenario_id] = ADVERSARIAL_ENGINE.execute_scenario(
                scenario=sc,
                mode=ExecutionMode.RUNTIME_ENFORCEMENT,
                policy_version=old_ver,
            )

        # 2. Run scenarios against new proposed policy state
        ENFORCEMENT_GATEWAY.set_active_policy_context(version=new_ver, db_policies=[new_policy_dict])
        new_results: Dict[str, ScenarioExecutionResult] = {}
        for sc in target_scenarios:
            new_results[sc.scenario_id] = ADVERSARIAL_ENGINE.execute_scenario(
                scenario=sc,
                mode=ExecutionMode.RUNTIME_ENFORCEMENT,
                policy_version=new_ver,
            )

        # Reset active policy context to default
        ENFORCEMENT_GATEWAY.set_active_policy_context(version=1, db_policies=None)

        # 3. Analyze differences
        newly_permitted: List[str] = []
        newly_denied: List[str] = []
        approval_changes: List[str] = []

        regressions: List[ScenarioComparisonItem] = []
        improvements: List[ScenarioComparisonItem] = []
        fp_introduced: List[ScenarioComparisonItem] = []
        fp_resolved: List[ScenarioComparisonItem] = []
        comparisons_list: List[Dict[str, Any]] = []

        for sc in target_scenarios:
            o_res = old_results[sc.scenario_id]
            n_res = new_results[sc.scenario_id]

            o_dec = o_res.enforcement_decision
            n_dec = n_res.enforcement_decision

            change_type = "NO_CHANGE"
            risk_impact = "NEUTRAL"
            details = "Outcome remained identical."

            if o_dec != n_dec:
                if n_dec == "ALLOW" and o_dec != "ALLOW":
                    newly_permitted.append(f"{sc.scenario_id} [{sc.name}]")
                    if not sc.is_benign:
                        change_type = "REGRESSION"
                        risk_impact = "HIGH"
                        details = "CRITICAL REGRESSION: Attack was previously blocked, now PERMITTED by loosened policy!"
                        regressions.append(ScenarioComparisonItem(
                            scenario_id=sc.scenario_id,
                            scenario_name=sc.name,
                            category=sc.category.value,
                            severity=sc.severity.value,
                            is_benign=sc.is_benign,
                            old_decision=o_dec,
                            new_decision=n_dec,
                            old_executed=o_res.action_executed,
                            new_executed=n_res.action_executed,
                            change_type=change_type,
                            risk_impact=risk_impact,
                            details=details,
                        ))
                    else:
                        change_type = "FALSE_POSITIVE_RESOLVED"
                        risk_impact = "LOW"
                        details = "Legitimate benign request is now allowed."
                        fp_resolved.append(ScenarioComparisonItem(
                            scenario_id=sc.scenario_id,
                            scenario_name=sc.name,
                            category=sc.category.value,
                            severity=sc.severity.value,
                            is_benign=sc.is_benign,
                            old_decision=o_dec,
                            new_decision=n_dec,
                            old_executed=o_res.action_executed,
                            new_executed=n_res.action_executed,
                            change_type=change_type,
                            risk_impact=risk_impact,
                            details=details,
                        ))

                elif n_dec == "DENY" and o_dec != "DENY":
                    newly_denied.append(f"{sc.scenario_id} [{sc.name}]")
                    if not sc.is_benign:
                        change_type = "IMPROVEMENT"
                        risk_impact = "LOW"
                        details = "SECURITY IMPROVEMENT: Attack that previously executed is now BLOCKED."
                        improvements.append(ScenarioComparisonItem(
                            scenario_id=sc.scenario_id,
                            scenario_name=sc.name,
                            category=sc.category.value,
                            severity=sc.severity.value,
                            is_benign=sc.is_benign,
                            old_decision=o_dec,
                            new_decision=n_dec,
                            old_executed=o_res.action_executed,
                            new_executed=n_res.action_executed,
                            change_type=change_type,
                            risk_impact=risk_impact,
                            details=details,
                        ))
                    else:
                        change_type = "FALSE_POSITIVE_INTRODUCED"
                        risk_impact = "MEDIUM"
                        details = "Benign legitimate action is newly blocked by stricter policy."
                        fp_introduced.append(ScenarioComparisonItem(
                            scenario_id=sc.scenario_id,
                            scenario_name=sc.name,
                            category=sc.category.value,
                            severity=sc.severity.value,
                            is_benign=sc.is_benign,
                            old_decision=o_dec,
                            new_decision=n_dec,
                            old_executed=o_res.action_executed,
                            new_executed=n_res.action_executed,
                            change_type=change_type,
                            risk_impact=risk_impact,
                            details=details,
                        ))

                if "REQUIRE_APPROVAL" in [o_dec, n_dec]:
                    approval_changes.append(f"{sc.scenario_id}: {o_dec} -> {n_dec}")

            comparisons_list.append({
                "scenario_id": sc.scenario_id,
                "name": sc.name,
                "category": sc.category.value,
                "severity": sc.severity.value,
                "is_benign": sc.is_benign,
                "old_decision": o_dec,
                "new_decision": n_dec,
                "change_type": change_type,
                "risk_impact": risk_impact,
                "details": details,
            })

        safe_to_deploy = len(regressions) == 0
        if regressions:
            overall_verdict = f"BLOCKED: {len(regressions)} security regressions detected. Attack exposure introduced."
        elif improvements:
            overall_verdict = f"APPROVED: {len(improvements)} security improvements verified with 0 regressions."
        elif fp_introduced:
            overall_verdict = f"WARNING: {len(fp_introduced)} benign false positives introduced. Review required."
        else:
            overall_verdict = "SAFE: No behavioral regressions detected."

        return PolicyRegressionReport(
            policy_id=policy_id,
            old_version=old_ver,
            new_version=new_ver,
            timestamp=datetime.now(timezone.utc).isoformat(),
            diff=diff,
            total_evaluated=len(target_scenarios),
            newly_permitted_actions=newly_permitted,
            newly_denied_actions=newly_denied,
            approval_requirement_changes=approval_changes,
            security_regressions=regressions,
            security_improvements=improvements,
            false_positives_introduced=fp_introduced,
            false_positives_resolved=fp_resolved,
            safe_to_deploy=safe_to_deploy,
            overall_verdict=overall_verdict,
            scenario_comparisons=comparisons_list,
        )


# Global Tester Instance
POLICY_REGRESSION_TESTER = PolicyRegressionTester()
