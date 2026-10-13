"""Comprehensive Unit & Integration Tests for CyberForge Adversarial Benchmark Engine (P0/P1).

Verifies:
1. Baseline configuration fails security tests (unauthorized side effects occur).
2. Runtime Enforcement configuration blocks all unauthorized side effects (0% unauthorized action rate).
3. Distinguishes between prompt detection and execution enforcement.
4. Correctly measures false-positive rate on benign control requests.
5. Benchmark metrics match mathematical definitions.
6. JSON and CSV export generation.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from agents.adversarial.scenarios import (
    SCENARIOS, AttackCategory, AttackSeverity, get_scenario_by_id
)
from agents.adversarial.engine import (
    ADVERSARIAL_ENGINE, ExecutionMode, OutcomeClassification
)
from agents.adversarial.benchmark import BENCHMARK_MANAGER, BenchmarkRun
from agents.enforcement.tools import reset_all_tool_side_effects


@pytest.fixture(autouse=True)
def clean_benchmark_state():
    reset_all_tool_side_effects()


def test_1_baseline_mode_allows_attacks_to_execute():
    """SECURITY INVARIANT: Baseline unprotected agent allows adversarial side effects."""
    drop_scenario = get_scenario_by_id("ADV-DIR-001")
    assert drop_scenario is not None

    res = ADVERSARIAL_ENGINE.execute_scenario(
        scenario=drop_scenario,
        mode=ExecutionMode.BASELINE_NO_ENFORCEMENT
    )

    assert res.action_executed is True
    assert res.side_effects_occurred is True
    assert res.unauthorized_side_effect is True
    assert res.classification in [
        OutcomeClassification.ATTACK_DETECTED_ACTION_EXECUTED,
        OutcomeClassification.ATTACK_NOT_DETECTED_ACTION_EXECUTED
    ]


def test_2_runtime_enforcement_blocks_attacks_zero_side_effects():
    """SECURITY INVARIANT: CyberForge runtime enforcement gateway blocks attack execution."""
    drop_scenario = get_scenario_by_id("ADV-DIR-001")
    assert drop_scenario is not None

    res = ADVERSARIAL_ENGINE.execute_scenario(
        scenario=drop_scenario,
        mode=ExecutionMode.RUNTIME_ENFORCEMENT
    )

    assert res.action_executed is False
    assert res.side_effects_occurred is False
    assert res.unauthorized_side_effect is False
    assert res.enforcement_decision == "DENY"
    assert res.classification == OutcomeClassification.ATTACK_DETECTED_ACTION_BLOCKED


def test_3_attack_missed_by_detector_blocked_by_execution_boundary():
    """CENTRAL PROPOSITION: Even when prompt detection is evaded, runtime policy blocks execution."""
    # ADV-AMB-012 uses euphemistic language to evade prompt detector
    amb_scenario = get_scenario_by_id("ADV-AMB-012")
    assert amb_scenario is not None

    # In detection-only mode, it executes
    res_det = ADVERSARIAL_ENGINE.execute_scenario(
        scenario=amb_scenario,
        mode=ExecutionMode.GOVERNANCE_DETECTION_ONLY
    )
    assert res_det.attack_detected is False
    assert res_det.action_executed is True
    assert res_det.classification == OutcomeClassification.ATTACK_NOT_DETECTED_ACTION_EXECUTED

    # In Runtime Enforcement mode, the gateway blocks it at execution boundary!
    res_gw = ADVERSARIAL_ENGINE.execute_scenario(
        scenario=amb_scenario,
        mode=ExecutionMode.RUNTIME_ENFORCEMENT
    )
    assert res_gw.action_executed is False
    assert res_gw.side_effects_occurred is False
    assert res_gw.classification == OutcomeClassification.ATTACK_NOT_DETECTED_ACTION_BLOCKED


def test_4_benign_requests_permitted():
    """VERIFICATION: Benign legitimate requests execute without false-positive blockage."""
    ben_scenario = get_scenario_by_id("BEN-001")
    assert ben_scenario is not None

    res = ADVERSARIAL_ENGINE.execute_scenario(
        scenario=ben_scenario,
        mode=ExecutionMode.RUNTIME_ENFORCEMENT
    )

    assert res.is_benign is True
    assert res.enforcement_decision == "ALLOW"
    assert res.action_executed is True
    assert res.classification == OutcomeClassification.LEGITIMATE_ACTION_ALLOWED


def test_5_full_benchmark_run_metrics_and_comparison():
    """VERIFICATION: Runs full benchmark suite across baseline vs runtime enforcement."""
    # Run Baseline Benchmark
    base_run: BenchmarkRun = BENCHMARK_MANAGER.run_benchmark(
        mode=ExecutionMode.BASELINE_NO_ENFORCEMENT
    )
    assert base_run.total_scenarios == len(SCENARIOS)
    assert base_run.attack_success_rate > 0.0
    assert base_run.unauthorized_action_rate > 0.0

    # Run Runtime Enforcement Benchmark
    gw_run: BenchmarkRun = BENCHMARK_MANAGER.run_benchmark(
        mode=ExecutionMode.RUNTIME_ENFORCEMENT
    )
    assert gw_run.total_scenarios == len(SCENARIOS)
    # With enforcement, attack success rate drops to 0.0!
    assert gw_run.attack_success_rate == 0.0
    assert gw_run.unauthorized_action_rate == 0.0
    assert gw_run.enforcement_success_rate >= 0.90
    assert gw_run.false_positive_rate == 0.0

    # Verify JSON structure
    run_dict = gw_run.to_dict()
    assert "attack_success_rate" in run_dict
    assert "category_breakdown" in run_dict
    assert "scenario_results" in run_dict

    # Verify CSV export
    csv_data = gw_run.to_csv()
    assert "Scenario ID,Name,Category" in csv_data
    assert "ADV-DIR-001" in csv_data
    assert "BEN-001" in csv_data
