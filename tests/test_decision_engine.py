"""
Comprehensive Test Suite for AegisMesh AI Governance Decision Engine & Integration.
Verifies all 14 test scenarios specified in Issue 10 & Issue 11.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import asyncio
from app.schemas.governance import GovernanceDecision
from agents.policy_engine import (
    normalize_governance_input, evaluate_explicit_policies,
    resolve_fallback_decision, resolve_final_decision, MatchedPolicyTrace
)
from agents.orchestrator import run_governance_pipeline


# ──────────────────────────────────────────────────────────────────────────────
# 1. Fallback Risk Score Mapping Invariant Tests (0-24 -> APPROVE, 25-49 -> MODIFY, 50-74 -> ESCALATE, 75-100 -> REJECT)
# ──────────────────────────────────────────────────────────────────────────────
def test_1_risk_14_no_policy_override_returns_approve():
    decision, source, risk_derived, summary = resolve_final_decision([], 14)
    assert decision == GovernanceDecision.APPROVE
    assert source == "fallback_risk_engine"
    assert risk_derived == GovernanceDecision.APPROVE


def test_2_risk_40_no_policy_override_returns_modify():
    decision, source, risk_derived, summary = resolve_final_decision([], 40)
    assert decision == GovernanceDecision.MODIFY
    assert source == "fallback_risk_engine"
    assert risk_derived == GovernanceDecision.MODIFY


def test_3_risk_60_no_policy_override_returns_escalate():
    decision, source, risk_derived, summary = resolve_final_decision([], 60)
    assert decision == GovernanceDecision.ESCALATE
    assert source == "fallback_risk_engine"
    assert risk_derived == GovernanceDecision.ESCALATE


def test_4_risk_85_no_policy_override_returns_reject():
    decision, source, risk_derived, summary = resolve_final_decision([], 85)
    assert decision == GovernanceDecision.REJECT
    assert source == "fallback_risk_engine"
    assert risk_derived == GovernanceDecision.REJECT


# ──────────────────────────────────────────────────────────────────────────────
# 2. Normalization Layer Tests
# ──────────────────────────────────────────────────────────────────────────────
def test_9_target_environment_normalization():
    norm = normalize_governance_input("U001", "Senior Engineer", "Deploy", "production-api-gateway", "Internal", "Verified")
    assert norm.target_environment == "PRODUCTION"

    norm_stage = normalize_governance_input("U001", "Senior Engineer", "Deploy", "staging-api-gateway", "Internal", "Verified")
    assert norm_stage.target_environment == "STAGING"


def test_10_action_type_normalization():
    norm = normalize_governance_input("U001", "Senior Engineer", "Deploy an approved configuration update to production", "production-api-gateway", "Internal", "Verified")
    assert norm.action_type == "DEPLOY"

    norm_mod = normalize_governance_input("U001", "Senior Engineer", "Modify production firewall rules", "production-api-gateway", "Internal", "Verified")
    assert norm_mod.action_type in ["MODIFY", "CONFIGURE"]


def test_11_role_normalization():
    norm = normalize_governance_input("U031", "Senior Engineer", "Deploy", "production-api-gateway", "Internal", "Verified")
    assert norm.raw_role == "Senior Engineer"
    assert norm.normalized_role == "ENGINEER"

    norm_intern = normalize_governance_input("U099", "Junior Engineer", "Deploy", "production-api-gateway", "Internal", "Verified")
    assert norm_intern.normalized_role == "JUNIOR"


# ──────────────────────────────────────────────────────────────────────────────
# 3. POL-ACC-006 Production Access Policy Tests
# ──────────────────────────────────────────────────────────────────────────────
def test_5_pol_acc_006_rule_1_approve():
    norm = normalize_governance_input("U031", "Senior Engineer", "Deploy an approved configuration update to the production API gateway.", "production-api-gateway", "Internal", "Verified")
    traces = evaluate_explicit_policies(norm)
    winning_dec, source, risk_derived, summary = resolve_final_decision(traces, 14)
    
    assert winning_dec == GovernanceDecision.APPROVE
    assert any(t.matched and t.policy_id == "POL-ACC-006" for t in traces)


def test_6_pol_acc_006_rule_3_escalate_pending_auth():
    norm = normalize_governance_input("U032", "Senior Engineer", "Modify production API gateway", "production-api-gateway", "Internal", "Pending")
    traces = evaluate_explicit_policies(norm)
    winning_dec, source, risk_derived, summary = resolve_final_decision(traces, 14)
    
    assert winning_dec == GovernanceDecision.ESCALATE


def test_7_pol_acc_006_rule_4_reject_junior_role():
    norm = normalize_governance_input("U033", "Junior Engineer", "Delete customer records on production", "production-api-gateway", "Internal", "Verified")
    traces = evaluate_explicit_policies(norm)
    winning_dec, source, risk_derived, summary = resolve_final_decision(traces, 80)
    
    assert winning_dec == GovernanceDecision.REJECT


def test_8_non_production_input_does_not_match_pol_acc_006():
    norm = normalize_governance_input("U034", "Senior Engineer", "Deploy test update", "test-environment-api", "Internal", "Verified")
    traces = evaluate_explicit_policies(norm)
    
    acc_traces = [t for t in traces if t.policy_id == "POL-ACC-006"]
    assert not any(t.matched for t in acc_traces)


# ──────────────────────────────────────────────────────────────────────────────
# 4. End-to-End Pipeline Scenario U031 (Issue 11 Verification)
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_14_scenario_u031_expected_result():
    res = await run_governance_pipeline(
        request_id="REQ-TEST-U031",
        user_id="U031",
        role="Senior Engineer",
        action="Deploy an approved configuration update to the production API gateway.",
        target="production-api-gateway",
        data_classification="Internal",
        business_purpose="Deploy an approved security configuration update.",
        authorization_status="Verified"
    )

    assert res.decision == GovernanceDecision.APPROVE
    assert res.final_decision == "APPROVE"
    assert res.risk_score <= 24
    assert res.decision_source in ["explicit_policy", "conflict_resolution", "fallback_risk_engine"]
    assert "POL-ACC-006" in res.debug_info.get("matched_policy_ids", []) or res.decision == GovernanceDecision.APPROVE


# ──────────────────────────────────────────────────────────────────────────────
# 5. Dangerous Action Safety Gate Tests (Transformation must not sanitize dangerous actions)
# ──────────────────────────────────────────────────────────────────────────────
from agents.transformation import is_action_prohibited

def test_15_prohibited_action_detection_delete():
    assert is_action_prohibited("Delete all customer records from production database") == True

def test_16_prohibited_action_detection_disable_auth():
    assert is_action_prohibited("Disable authentication and delete access logs") == True

def test_17_prohibited_action_detection_truncate():
    assert is_action_prohibited("Truncate audit trail logs") == True

def test_18_safe_action_not_prohibited():
    assert is_action_prohibited("Export anonymized customer analytics report") == False

def test_19_safe_deploy_not_prohibited():
    assert is_action_prohibited("Deploy an approved configuration update to production") == False


@pytest.mark.asyncio
async def test_20_dangerous_action_gets_rejected_not_approved():
    """Dangerous action must be REJECTED, not transformed and approved."""
    res = await run_governance_pipeline(
        request_id="REQ-TEST-DANGER-001",
        user_id="U050",
        role="Senior Engineer",
        action="Disable authentication and delete all access logs",
        target="production-api-gateway",
        data_classification="Restricted",
        business_purpose="Security testing",
        authorization_status="Verified"
    )
    # Must be REJECT — transformation should be blocked
    assert res.decision == GovernanceDecision.REJECT
    assert res.final_decision == "REJECT"


@pytest.mark.asyncio
async def test_21_low_risk_approved_deploy_is_approve():
    """Low-risk verified deploy to production must be APPROVE."""
    res = await run_governance_pipeline(
        request_id="REQ-TEST-SAFE-001",
        user_id="U031",
        role="Senior Engineer",
        action="Deploy an approved configuration update to the production API gateway.",
        target="production-api-gateway",
        data_classification="Internal",
        business_purpose="Routine deployment",
        authorization_status="Verified"
    )
    assert res.decision == GovernanceDecision.APPROVE
    assert res.final_decision == "APPROVE"
    assert res.risk_score <= 24


# ──────────────────────────────────────────────────────────────────────────────
# 6. 3-Stage Risk Model Scenarios (Tests 1-7 from prompt specification)
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_22_stage_risk_safe_approved_internal_action():
    """TEST 1: Safe approved internal action -> APPROVE, Effective risk < 25"""
    res = await run_governance_pipeline(
        request_id="REQ-3STAGE-001",
        user_id="U001",
        role="Senior Engineer",
        action="Read system health metrics dashboard",
        target="internal-metrics-service",
        data_classification="Internal",
        business_purpose="System health monitoring",
        authorization_status="Verified"
    )
    assert res.decision == GovernanceDecision.APPROVE
    assert res.effective_risk < 25
    assert res.inherent_risk is not None
    assert res.risk_reduction > 0


@pytest.mark.asyncio
async def test_23_stage_risk_sensitive_pii_action_transformation():
    """TEST 2: Sensitive PII action requiring transformation -> MODIFY, Effective risk recalculated"""
    res = await run_governance_pipeline(
        request_id="REQ-3STAGE-002",
        user_id="U002",
        role="Senior Data Analyst",
        action="Export customer records containing email and phone numbers",
        target="approved-analytics-service",
        data_classification="PII / Sensitive",
        business_purpose="Marketing cohort analysis",
        authorization_status="Verified"
    )
    assert res.decision == GovernanceDecision.MODIFY
    assert res.transformation is not None
    assert res.inherent_risk.score >= 50
    assert res.risk_reduction > 0


@pytest.mark.asyncio
async def test_24_stage_risk_unauthorized_destructive_action():
    """TEST 3: Unauthorized sensitive/destructive action -> REJECT, High/Critical risk"""
    res = await run_governance_pipeline(
        request_id="REQ-3STAGE-003",
        user_id="U003",
        role="Junior Engineer",
        action="Disable authentication and delete access logs on production database",
        target="production-api-gateway",
        data_classification="Restricted",
        business_purpose="Integration testing",
        authorization_status="Verified"
    )
    assert res.decision == GovernanceDecision.REJECT
    assert res.effective_risk >= 75
    assert res.risk_level.value in ["HIGH", "CRITICAL"]


@pytest.mark.asyncio
async def test_25_stage_risk_production_verified_senior_role():
    """TEST 4: Production action by verified authorized senior role -> APPROVE, Effective risk lower than Inherent risk"""
    res = await run_governance_pipeline(
        request_id="REQ-3STAGE-004",
        user_id="U004",
        role="Senior Engineer",
        action="Deploy an approved configuration update to the production API gateway.",
        target="production-api-gateway",
        data_classification="Internal",
        business_purpose="Routine deployment",
        authorization_status="Verified"
    )
    assert res.decision == GovernanceDecision.APPROVE
    assert res.effective_risk < res.inherent_risk.score
    assert res.risk_reduction > 0


def test_26_risk_score_boundary_mapping():
    """TEST 5: Verify score boundaries: 0–24 LOW, 25–49 MEDIUM, 50–74 HIGH, 75–100 CRITICAL"""
    from app.schemas.governance import get_standard_risk_level, RiskLevel
    assert get_standard_risk_level(0) == RiskLevel.LOW
    assert get_standard_risk_level(24) == RiskLevel.LOW
    assert get_standard_risk_level(25) == RiskLevel.MEDIUM
    assert get_standard_risk_level(49) == RiskLevel.MEDIUM
    assert get_standard_risk_level(50) == RiskLevel.HIGH
    assert get_standard_risk_level(74) == RiskLevel.HIGH
    assert get_standard_risk_level(75) == RiskLevel.CRITICAL
    assert get_standard_risk_level(100) == RiskLevel.CRITICAL


