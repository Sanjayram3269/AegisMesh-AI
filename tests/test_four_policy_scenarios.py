"""
Test suite verifying Part 5 four explicit policy scenarios in AegisMesh AI.

Tests:
1. TEST 1 — APPROVE (U020, Finance Manager, approved-finance-analytics, Restricted, Verified) -> APPROVE
2. TEST 2 — MODIFY (U021, Finance Manager, approved-finance-analytics, Restricted, Verified, Update action) -> MODIFY
3. TEST 3 — ESCALATE (U022, Financial Analyst, new-business-analytics, Confidential, Pending) -> ESCALATE
4. TEST 4 — REJECT (U023, Intern, public-external-platform, Restricted, Unverified) -> REJECT
"""

import pytest
import asyncio
from agents.orchestrator import run_governance_pipeline
from app.schemas.governance import GovernanceDecision


@pytest.mark.asyncio
async def test_scenario_1_approve_u020():
    res = await run_governance_pipeline(
        request_id="REQ-TEST-1",
        user_id="U020",
        role="Finance Manager",
        action="Generate an internal quarterly financial performance report using restricted financial records.",
        target="approved-finance-analytics",
        data_classification="Restricted",
        business_purpose="Quarterly internal financial analysis",
        authorization_status="Verified"
    )

    assert res.decision == GovernanceDecision.APPROVE
    assert res.final_decision == "APPROVE"
    assert res.inherent_risk.score <= 25
    assert res.inherent_risk.signals['external_exposure'] == 0.0
    assert res.inherent_risk.signals['user_authorization'] == 0.0
    assert res.inherent_risk.signals['target_trust'] == 5.0
    assert "POL-FIN-006" in res.debug_info['matched_policy_ids']
    assert res.decision_source in ["explicit_policy", "conflict_resolution"]


@pytest.mark.asyncio
async def test_scenario_2_modify_u021():
    res = await run_governance_pipeline(
        request_id="REQ-TEST-2",
        user_id="U021",
        role="Finance Manager",
        action="Update a restricted financial report and remove unnecessary account identifiers before publishing the revised internal version.",
        target="approved-finance-analytics",
        data_classification="Restricted",
        business_purpose="Publishing revised internal financial report",
        authorization_status="Verified"
    )

    assert res.decision == GovernanceDecision.MODIFY
    assert res.final_decision == "APPROVED AFTER MODIFICATION"
    assert res.transformation is not None
    assert res.transformation.transformation_applied is True
    assert "POL-FIN-006" in res.debug_info['matched_policy_ids']


@pytest.mark.asyncio
async def test_scenario_3_escalate_u022():
    res = await run_governance_pipeline(
        request_id="REQ-TEST-3",
        user_id="U022",
        role="Financial Analyst",
        action="Share confidential financial performance data with a new business analytics platform for executive reporting.",
        target="new-business-analytics",
        data_classification="Confidential",
        business_purpose="Executive reporting on new analytics vendor platform",
        authorization_status="Pending"
    )

    assert res.decision == GovernanceDecision.ESCALATE
    assert res.final_decision == "ESCALATE"
    assert res.human_review_required is True
    assert "POL-FIN-006" in res.debug_info['matched_policy_ids']


@pytest.mark.asyncio
async def test_scenario_4_reject_u023():
    res = await run_governance_pipeline(
        request_id="REQ-TEST-4",
        user_id="U023",
        role="Intern",
        action="Export restricted customer financial records and transaction details to a public external data-sharing platform.",
        target="public-external-platform",
        data_classification="Restricted",
        business_purpose="Testing external data export",
        authorization_status="Unverified"
    )

    assert res.decision == GovernanceDecision.REJECT
    assert res.final_decision == "REJECT"
    assert res.inherent_risk.score >= 75
    assert "POL-FIN-006" in res.debug_info['matched_policy_ids']
