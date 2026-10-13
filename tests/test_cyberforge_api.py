"""Integration tests for CyberForge API Endpoints."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_1_cyberforge_api_info():
    res = client.get("/api")
    assert res.status_code == 200
    data = res.json()
    assert "CyberForge" in data["name"]
    assert "/api/cyberforge/overview" in data["cyberforge"]


def test_2_cyberforge_overview():
    res = client.get("/api/cyberforge/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SECURE"
    assert "CyberForge" in data["platform_name"]
    assert data["total_protected_tools"] >= 6
    assert data["total_scenarios_in_suite"] >= 20


def test_3_cyberforge_scenarios_catalog():
    res = client.get("/api/cyberforge/adversarial/scenarios")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 20
    assert len(data["scenarios"]) >= 20


def test_4_cyberforge_run_single_scenario():
    res = client.post("/api/cyberforge/adversarial/run", json={
        "scenario_id": "ADV-DIR-001",
        "mode": "RUNTIME_ENFORCEMENT"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["scenario_id"] == "ADV-DIR-001"
    assert data["enforcement_decision"] == "DENY"
    assert data["action_executed"] is False


def test_5_cyberforge_benchmark_run_and_export():
    res = client.post("/api/cyberforge/benchmark/run", json={
        "mode": "RUNTIME_ENFORCEMENT"
    })
    assert res.status_code == 200
    data = res.json()
    assert "run_id" in data
    assert data["attack_success_rate"] == 0.0
    run_id = data["run_id"]

    # Test CSV export
    csv_res = client.get(f"/api/cyberforge/benchmark/runs/{run_id}/export?format=csv")
    assert csv_res.status_code == 200
    assert "Scenario ID" in csv_res.text

    # Test JSON export
    json_res = client.get(f"/api/cyberforge/benchmark/runs/{run_id}/export?format=json")
    assert json_res.status_code == 200
    assert json_res.json()["run_id"] == run_id


def test_6_cyberforge_audit_chain_verification():
    res = client.get("/api/cyberforge/audit/verify")
    assert res.status_code == 200
    data = res.json()
    assert data["chain_valid"] is True


def test_7_cyberforge_tools_catalog():
    res = client.get("/api/cyberforge/tools")
    assert res.status_code == 200
    data = res.json()
    assert len(data["tools"]) >= 6
    tool_names = [t["name"] for t in data["tools"]]
    assert "database_execute" in tool_names
    assert "payment_transfer" in tool_names


def test_8_cyberforge_settings():
    res = client.get("/api/cyberforge/settings")
    assert res.status_code == 200
    data = res.json()
    assert data["platform_name"] == "CyberForge"
    assert data["fail_closed_mode"] is True
