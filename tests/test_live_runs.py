"""Live telemetry reflects real work and never crosses account boundaries."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.main import app
from app.operations import api
from app.operations.service import Operations
from app.operations.store import Store
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    service = Operations(Store(tmp_path))
    monkeypatch.setattr(api, "operations", lambda: service)
    monkeypatch.setenv("AEGIS_PROVIDER", "offline")
    client = TestClient(app)
    credentials = json.loads((tmp_path / "credentials.json").read_text())
    tokens = {
        role: client.post("/api/ops/login", json=credential).json()["token"]
        for role, credential in credentials.items()
    }
    return client, tokens


def auth(tokens, role="agent"):
    return {"Authorization": "Bearer " + tokens[role]}


def test_live_trace_authentication_and_ownership(client):
    c, tokens = client
    assert c.post("/api/ops/runs", json={"operation": "chat"}).status_code == 401
    run = c.post(
        "/api/ops/runs", headers=auth(tokens), json={"operation": "chat"}
    ).json()
    assert not run["events"] and not run["complete"]
    assert (
        c.get("/api/ops/runs/" + run["id"], headers=auth(tokens, "manager")).status_code
        == 403
    )
    assert (
        c.post(
            "/api/ops/runs", headers=auth(tokens), json={"operation": "pretend_execute"}
        ).status_code
        == 422
    )


def test_planning_trace_never_claims_execution(client):
    c, tokens = client
    run = c.post(
        "/api/ops/runs", headers=auth(tokens), json={"operation": "chat"}
    ).json()
    headers = {**auth(tokens), "X-Aegis-Run": run["id"]}
    response = c.post(
        "/api/ops/chat", headers=headers, json={"message": "Resolve ticket 101"}
    )
    assert response.status_code == 200 and not response.json()["executed"]
    trace = c.get("/api/ops/runs/" + run["id"], headers=auth(tokens)).json()
    assert trace["complete"]
    assert [e["stage"] for e in trace["events"]] == [
        "identity",
        "intent",
        "intent",
        "policy",
        "policy",
        "risk",
        "run",
    ]
    assert not any(e["stage"] == "execution" for e in trace["events"])
    assert (
        c.post(
            "/api/ops/chat", headers=headers, json={"message": "Resolve ticket 101"}
        ).status_code
        == 409
    )


@pytest.mark.parametrize("sensitive", [False, True])
def test_execution_trace_separates_approval_from_business_effects(client, sensitive):
    c, tokens = client
    p = c.post(
        "/api/ops/proposals",
        headers=auth(tokens),
        json={
            "tool": "reports.export",
            "fields": ["ticket_id", "email"] if sensitive else ["ticket_id", "status"],
        },
    ).json()
    run = c.post(
        "/api/ops/runs", headers=auth(tokens), json={"operation": "execute"}
    ).json()
    result = c.post(
        "/api/ops/execute",
        headers={**auth(tokens), "X-Aegis-Run": run["id"]},
        json={"proposal_id": p["id"]},
    ).json()
    trace = c.get("/api/ops/runs/" + run["id"], headers=auth(tokens)).json()
    assert trace["complete"]
    assert trace["events"][-1]["stage"] == "run"
    execution = [e for e in trace["events"] if e["stage"] == "execution"]
    assert execution[-1]["state"] == ("waiting" if sensitive else "complete")
    assert result["executed"] is (not sensitive)
    assert any(
        e["stage"] == "audit" and e["state"] == "complete" for e in trace["events"]
    )


def test_trace_cannot_be_claimed_for_another_operation(client):
    c, tokens = client
    run = c.post(
        "/api/ops/runs", headers=auth(tokens), json={"operation": "review"}
    ).json()
    response = c.post(
        "/api/ops/chat",
        headers={**auth(tokens), "X-Aegis-Run": run["id"]},
        json={"message": "Resolve ticket 101"},
    )
    assert response.status_code == 409
