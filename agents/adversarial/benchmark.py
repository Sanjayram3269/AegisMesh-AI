"""CyberForge Reproducible Attack Benchmark Evaluation Engine.

Executes test suites across 4 standardized configurations, calculates authoritative metrics,
stores historical runs, and exports results in JSON and CSV formats.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import io
import json
import statistics
import uuid
from typing import Any, Dict, List, Optional

from agents.adversarial.scenarios import (
    SCENARIOS, AttackScenario, AttackCategory, AttackSeverity,
    get_all_scenarios, get_scenario_by_id
)
from agents.adversarial.engine import (
    ADVERSARIAL_ENGINE, ExecutionMode, ScenarioExecutionResult, OutcomeClassification
)
from agents.enforcement.tools import reset_all_tool_side_effects


@dataclass
class CategoryMetricSummary:
    total: int
    attack_count: int
    benign_count: int
    attacks_blocked: int
    unauthorized_actions: int
    attack_success_rate: float
    enforcement_success_rate: float


@dataclass
class BenchmarkRun:
    run_id: str
    mode: ExecutionMode
    policy_version: int
    scenario_version: str
    provider_info: str
    timestamp: str
    total_scenarios: int
    adversarial_scenarios: int
    benign_scenarios: int
    
    # Core Metrics
    attack_success_rate: float
    unauthorized_action_rate: float
    enforcement_success_rate: float
    false_positive_rate: float
    false_negative_rate: float
    
    median_latency_ms: float
    p95_latency_ms: float
    
    category_breakdown: Dict[str, Dict[str, Any]]
    severity_breakdown: Dict[str, Dict[str, Any]]
    scenario_results: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode.value,
            "policy_version": self.policy_version,
            "scenario_version": self.scenario_version,
            "provider_info": self.provider_info,
            "timestamp": self.timestamp,
            "total_scenarios": self.total_scenarios,
            "adversarial_scenarios": self.adversarial_scenarios,
            "benign_scenarios": self.benign_scenarios,
            "attack_success_rate": round(self.attack_success_rate, 4),
            "unauthorized_action_rate": round(self.unauthorized_action_rate, 4),
            "enforcement_success_rate": round(self.enforcement_success_rate, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "false_negative_rate": round(self.false_negative_rate, 4),
            "median_latency_ms": round(self.median_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "category_breakdown": self.category_breakdown,
            "severity_breakdown": self.severity_breakdown,
            "scenario_results": self.scenario_results,
        }

    def to_csv(self) -> str:
        """Exports per-scenario benchmark evaluation results to CSV."""
        output = io.StringIO()
        headers = [
            "Scenario ID", "Name", "Category", "Severity", "Is Benign",
            "Attack Detected", "Enforcement Decision", "Action Executed",
            "Unauthorized Side Effect", "Classification", "Latency (ms)", "Digest"
        ]
        output.write(",".join(headers) + "\n")
        for res in self.scenario_results:
            row = [
                f'"{res.get("scenario_id")}"',
                f'"{res.get("scenario_name")}"',
                f'"{res.get("category")}"',
                f'"{res.get("severity")}"',
                str(res.get("is_benign")),
                str(res.get("attack_detected")),
                f'"{res.get("enforcement_decision")}"',
                str(res.get("action_executed")),
                str(res.get("unauthorized_side_effect")),
                f'"{res.get("classification")}"',
                str(res.get("latency_ms")),
                f'"{res.get("canonical_digest")}"',
            ]
            output.write(",".join(row) + "\n")
        return output.getvalue()


class BenchmarkManager:
    """Orchestrates benchmark runs, metric computations, and historical persistence."""

    def __init__(self):
        self._history: Dict[str, BenchmarkRun] = {}

    def run_benchmark(
        self,
        mode: ExecutionMode = ExecutionMode.RUNTIME_ENFORCEMENT,
        scenario_ids: Optional[List[str]] = None,
        policy_version: int = 1,
        provider_info: str = "CyberForge Control Plane",
    ) -> BenchmarkRun:
        run_id = f"BM-{uuid.uuid4().hex[:10].upper()}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        target_scenarios = (
            [s for s in SCENARIOS if s.scenario_id in scenario_ids]
            if scenario_ids
            else SCENARIOS
        )

        results: List[ScenarioExecutionResult] = []
        latencies: List[float] = []

        # Clean tool side-effects prior to benchmark run for deterministic measurement
        reset_all_tool_side_effects()

        for sc in target_scenarios:
            res = ADVERSARIAL_ENGINE.execute_scenario(
                scenario=sc,
                mode=mode,
                policy_version=policy_version,
            )
            results.append(res)
            latencies.append(res.latency_ms)

        # ──────────────────────────────────────────────────────────────────────
        # Metric Calculations
        # ──────────────────────────────────────────────────────────────────────
        total = len(results)
        adv_results = [r for r in results if not r.is_benign]
        ben_results = [r for r in results if r.is_benign]

        adv_count = len(adv_results)
        ben_count = len(ben_results)

        # Attack success rate = attacks where unauthorized objective succeeded / valid attack scenarios
        unauthorized_count = sum(1 for r in adv_results if r.unauthorized_side_effect)
        attack_success_rate = (unauthorized_count / adv_count) if adv_count > 0 else 0.0

        # Unauthorized action rate = scenarios producing unauthorized side effect / valid attack scenarios
        unauthorized_action_rate = (unauthorized_count / adv_count) if adv_count > 0 else 0.0

        # Enforcement success rate = (blocked attacks + permitted benign) / total valid scenarios
        blocked_attacks = sum(1 for r in adv_results if not r.action_executed)
        permitted_benign = sum(1 for r in ben_results if r.action_executed and r.enforcement_decision == "ALLOW")
        enforcement_success_rate = ((blocked_attacks + permitted_benign) / total) if total > 0 else 0.0

        # False-positive rate = benign requests incorrectly denied / valid benign requests
        false_positives = sum(1 for r in ben_results if r.enforcement_decision in ["DENY", "REQUIRE_APPROVAL"])
        false_positive_rate = (false_positives / ben_count) if ben_count > 0 else 0.0

        # False-negative rate = adversarial attacks that succeeded in executing / valid attacks
        false_negative_rate = (unauthorized_count / adv_count) if adv_count > 0 else 0.0

        # Latencies
        sorted_latencies = sorted(latencies) if latencies else [0.0]
        med_lat = statistics.median(sorted_latencies) if sorted_latencies else 0.0
        p95_idx = int(0.95 * len(sorted_latencies))
        p95_lat = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)] if sorted_latencies else 0.0

        # Category Breakdown
        cat_map: Dict[str, List[ScenarioExecutionResult]] = {}
        for r in results:
            cat_map.setdefault(r.category.value, []).append(r)

        category_breakdown = {}
        for cat, items in cat_map.items():
            cat_adv = [i for i in items if not i.is_benign]
            cat_unauth = sum(1 for i in cat_adv if i.unauthorized_side_effect)
            category_breakdown[cat] = {
                "total": len(items),
                "adversarial": len(cat_adv),
                "unauthorized_actions": cat_unauth,
                "attack_success_rate": round((cat_unauth / len(cat_adv)) if cat_adv else 0.0, 4),
                "enforcement_rate": round(sum(1 for i in items if (not i.is_benign and not i.action_executed) or (i.is_benign and i.action_executed)) / len(items), 4),
            }

        # Severity Breakdown
        sev_map: Dict[str, List[ScenarioExecutionResult]] = {}
        for r in results:
            sev_map.setdefault(r.severity.value, []).append(r)

        severity_breakdown = {}
        for sev, items in sev_map.items():
            sev_adv = [i for i in items if not i.is_benign]
            sev_unauth = sum(1 for i in sev_adv if i.unauthorized_side_effect)
            severity_breakdown[sev] = {
                "total": len(items),
                "adversarial": len(sev_adv),
                "unauthorized_actions": sev_unauth,
                "attack_success_rate": round((sev_unauth / len(sev_adv)) if sev_adv else 0.0, 4),
            }

        benchmark_run = BenchmarkRun(
            run_id=run_id,
            mode=mode,
            policy_version=policy_version,
            scenario_version="2026.1",
            provider_info=provider_info,
            timestamp=timestamp,
            total_scenarios=total,
            adversarial_scenarios=adv_count,
            benign_scenarios=ben_count,
            attack_success_rate=attack_success_rate,
            unauthorized_action_rate=unauthorized_action_rate,
            enforcement_success_rate=enforcement_success_rate,
            false_positive_rate=false_positive_rate,
            false_negative_rate=false_negative_rate,
            median_latency_ms=med_lat,
            p95_latency_ms=p95_lat,
            category_breakdown=category_breakdown,
            severity_breakdown=severity_breakdown,
            scenario_results=[r.to_dict() for r in results],
        )

        self._history[run_id] = benchmark_run
        return benchmark_run

    def get_run(self, run_id: str) -> Optional[BenchmarkRun]:
        return self._history.get(run_id)

    def list_runs(self) -> List[Dict[str, Any]]:
        return [
            {
                "run_id": r.run_id,
                "mode": r.mode.value,
                "policy_version": r.policy_version,
                "timestamp": r.timestamp,
                "total_scenarios": r.total_scenarios,
                "attack_success_rate": round(r.attack_success_rate, 4),
                "unauthorized_action_rate": round(r.unauthorized_action_rate, 4),
                "enforcement_success_rate": round(r.enforcement_success_rate, 4),
                "false_positive_rate": round(r.false_positive_rate, 4),
                "median_latency_ms": round(r.median_latency_ms, 2),
            }
            for r in reversed(list(self._history.values()))
        ]


# Global Benchmark Manager
BENCHMARK_MANAGER = BenchmarkManager()
