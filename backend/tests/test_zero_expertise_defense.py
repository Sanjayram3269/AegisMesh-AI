"""Tests for the Zero-Expertise Cyber Defense demo workflow."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def setup_function():
    client.post("/api/defense/demo/reset")


def test_summary_discloses_demo_mode_and_no_live_telemetry():
    response = client.get("/api/defense/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "SIMULATION"
    assert body["telemetry_connected"] is False
    assert body["incident_count"] >= 4
    assert "no live security sources" in body["coverage_message"].lower()


def test_incidents_are_plain_language_and_grouped():
    response = client.get("/api/defense/incidents")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 4
    incident = next(i for i in body["incidents"] if i["id"] == "INC-1001")
    assert incident["what_happened"]
    assert incident["why_it_matters"]
    assert incident["evidence"]
    assert incident["recommended_action"]
    assert incident["event_count"] > 1


def test_search_and_severity_filter():
    response = client.get("/api/defense/incidents?severity=high&search=workstation")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["incidents"][0]["id"] == "INC-1003"


def test_high_impact_containment_requires_approval_and_does_not_execute():
    response = client.post("/api/defense/incidents/INC-1001/response", json={"action": "simulate_containment"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending_approval"
    assert "No containment was executed" in body["message"]


def test_review_does_not_claim_threat_resolved():
    response = client.post("/api/defense/incidents/INC-1002/response", json={"action": "acknowledge"})
    assert response.status_code == 200
    assert "does not mean" in response.json()["message"]


def test_unknown_incident_returns_404():
    response = client.post("/api/defense/incidents/INC-NOT-REAL/response", json={"action": "acknowledge"})
    assert response.status_code == 404


def test_reset_restores_seed_incidents():
    client.post("/api/defense/incidents/INC-1002/response", json={"action": "acknowledge"})
    client.post("/api/defense/demo/reset")
    body = client.get("/api/defense/incidents").json()
    incident = next(i for i in body["incidents"] if i["id"] == "INC-1002")
    assert incident["status"] == "needs_attention"
