"""Tests for the Zero-Expertise Cyber Defense demo workflow."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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


def test_support_request_keeps_incident_open():
    response = client.post("/api/defense/incidents/INC-1003/response", json={"action": "support_review"})
    assert response.status_code == 200
    assert response.json()["status"] == "pending_support"
    assert "remains open" in response.json()["message"]


def test_containment_is_rejected_for_non_containment_incident():
    response = client.post("/api/defense/incidents/INC-1002/response", json={"action": "simulate_containment"})
    assert response.status_code == 400

 
def test_imported_events_are_normalized_and_duplicate_ids_are_idempotent():
    payload = {
        "event_id": "event-demo-001",
        "source": "Imported identity alert",
        "event_type": "suspicious_login",
        "asset": "staff-account-7",
        "description": "Several sign-in attempts were reported for this account.",
        "evidence": ["Five failed sign-ins", "New location"],
    }
    first = client.post("/api/defense/events/ingest", json=payload)
    assert first.status_code == 200
    assert first.json()["duplicate"] is False
    incident_id = first.json()["incident_id"]

    duplicate = client.post("/api/defense/events/ingest", json=payload)
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["incident_id"] == incident_id


def test_related_imported_events_are_grouped():
    base = {
        "source": "Imported endpoint alert",
        "event_type": "malware_alert",
        "asset": "WS-DEMO-9",
        "description": "A suspicious process was reported by the endpoint tool.",
        "evidence": ["Suspicious process signal"],
    }
    first = client.post("/api/defense/events/ingest", json={"event_id": "endpoint-001", **base})
    second = client.post("/api/defense/events/ingest", json={"event_id": "endpoint-002", **base})
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["grouped"] is True
    assert second.json()["incident_id"] == first.json()["incident_id"]
    incident = next(i for i in client.get("/api/defense/incidents").json()["incidents"] if i["id"] == first.json()["incident_id"])
    assert incident["event_count"] == 2
