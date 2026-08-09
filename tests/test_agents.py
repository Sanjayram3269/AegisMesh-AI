"""Unit tests for AegisMesh AI Governance Agents and Pipeline."""

import pytest
import asyncio
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from agents.orchestrator import run_governance_pipeline
from app.schemas.governance import GovernanceDecision, RiskLevel

@pytest.mark.asyncio
async def test_scenario_approve():
    res = await run_governance_pipeline(
        request_id="TEST-001",
        user_id="U001",
        role="Senior Data Analyst",
        action="Export anonymized aggregated customer analytics",
        target="approved-internal-analytics"
    )
    assert res.decision == GovernanceDecision.APPROVE
    assert res.risk_score <= 25
    assert res.risk_level == RiskLevel.LOW

@pytest.mark.asyncio
async def test_scenario_modify():
    res = await run_governance_pipeline(
        request_id="TEST-002",
        user_id="U002",
        role="Marketing Analyst",
        action="Export customer records containing email and phone numbers",
        target="approved-analytics-service"
    )
    assert res.decision == GovernanceDecision.MODIFY
    assert res.risk_score <= 55
    assert res.transformation is not None

@pytest.mark.asyncio
async def test_scenario_escalate():
    res = await run_governance_pipeline(
        request_id="TEST-003",
        user_id="U003",
        role="Marketing Analyst",
        action="Send sensitive customer dataset to a new external analytics vendor",
        target="new-external-vendor",
        data_classification="Restricted",
        authorization_status="Pending"
    )
    assert res.decision == GovernanceDecision.ESCALATE
    assert res.human_review_required is True

@pytest.mark.asyncio
async def test_scenario_reject():
    res = await run_governance_pipeline(
        request_id="TEST-004",
        user_id="U004",
        role="Junior Analyst",
        action="Export confidential customer database to unauthorized public endpoint",
        target="public-endpoint-unauthorized",
        data_classification="Restricted",
        authorization_status="Unauthorized"
    )
    assert res.decision == GovernanceDecision.REJECT
    assert res.risk_score >= 75
    assert res.risk_level == RiskLevel.CRITICAL
