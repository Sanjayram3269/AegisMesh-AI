"""Comprehensive Unit & Integration Tests for Two-Stage Risk Model & Governance Pipeline."""
import os
import sys
import pytest

# Ensure backend & root are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.orchestrator import run_governance_pipeline
from agents.risk import compute_canonical_risk
from app.schemas.governance import GovernanceDecision, RiskLevel, get_standard_risk_level


def test_standardized_risk_levels():
    """Verify single 4-tier standardized risk level mapping across the system."""
    assert get_standard_risk_level(15) == RiskLevel.LOW
    assert get_standard_risk_level(24) == RiskLevel.LOW
    assert get_standard_risk_level(25) == RiskLevel.MEDIUM
    assert get_standard_risk_level(49) == RiskLevel.MEDIUM
    assert get_standard_risk_level(50) == RiskLevel.HIGH
    assert get_standard_risk_level(74) == RiskLevel.HIGH
    assert get_standard_risk_level(75) == RiskLevel.CRITICAL
    assert get_standard_risk_level(95) == RiskLevel.CRITICAL


@pytest.mark.asyncio
async def test_1_approve_workflow():
    """TEST 1 — APPROVE: Low inherent risk, approved policy decision."""
    res = await run_governance_pipeline(
        request_id="REQ-STAGE-APPROVE",
        user_id="U001",
        role="Senior Data Analyst",
        action="Export anonymized aggregated customer analytics",
        target="approved-internal-analytics",
        data_classification="Internal",
        business_purpose="Internal executive reporting",
        authorization_status="Verified"
    )
    assert res.inherent_risk is not None
    assert res.inherent_risk.score < 25
    assert res.inherent_risk.level == RiskLevel.LOW
    assert res.policy_decision == GovernanceDecision.APPROVE
    assert res.final_decision == "APPROVE"
    assert res.final_risk is None  # No transformation for APPROVE
    assert res.risk_reduction is None


@pytest.mark.asyncio
async def test_2_modify_workflow_two_stage_risk():
    """TEST 2 — MODIFY: Medium inherent risk transformed to lower effective final risk."""
    res = await run_governance_pipeline(
        request_id="REQ-STAGE-MODIFY",
        user_id="U002",
        role="Marketing Analyst",
        action="Export customer records containing email and phone numbers",
        target="approved-analytics-service",
        data_classification="PII / Sensitive",
        business_purpose="Marketing campaign outreach",
        authorization_status="Verified"
    )
    assert res.policy_decision == GovernanceDecision.MODIFY
    assert res.inherent_risk is not None
    assert res.inherent_risk.score >= 25

    # Transformation assertions
    assert res.transformation is not None
    assert res.transformation.transformation_applied is True
    assert res.transformation.modified_request != res.transformation.original_request

    # Effective / Final Risk assertions
    assert res.final_risk is not None
    assert res.final_risk.score < res.inherent_risk.score
    assert res.risk_reduction is not None
    assert res.risk_reduction == (res.inherent_risk.score - res.final_risk.score)
    assert res.final_decision == "APPROVED AFTER MODIFICATION"


@pytest.mark.asyncio
async def test_3_escalate_workflow_canonical_score_consistency():
    """TEST 3 — ESCALATE: Canonical inherent risk score is preserved in human review."""
    res = await run_governance_pipeline(
        request_id="REQ-STAGE-ESCALATE",
        user_id="U003",
        role="Marketing Analyst",
        action="Send sensitive customer dataset to a new external analytics vendor",
        target="new-external-vendor",
        data_classification="Restricted",
        authorization_status="Pending"
    )
    assert res.policy_decision == GovernanceDecision.ESCALATE
    assert res.human_review_required is True
    assert res.inherent_risk is not None

    # Assertion: Inherent risk score in response matches exact canonical inherent score
    assert res.risk_score == res.inherent_risk.score
    assert res.final_risk is None  # No transformation for ESCALATE


@pytest.mark.asyncio
async def test_4_reject_workflow_canonical_scoring():
    """TEST 4 — REJECT: Policy-based vs Risk-based REJECT maintains pure canonical score."""
    res = await run_governance_pipeline(
        request_id="REQ-STAGE-REJECT",
        user_id="U004",
        role="Junior Analyst",
        action="Export confidential customer database to unauthorized public endpoint",
        target="public-endpoint-unauthorized",
        data_classification="Confidential",
        business_purpose="Testing endpoint",
        authorization_status="Not Verified"
    )
    assert res.decision == GovernanceDecision.REJECT
    assert res.inherent_risk is not None
    assert res.risk_score == res.inherent_risk.score
    assert res.inherent_risk.score >= 50
    assert res.final_risk is None
