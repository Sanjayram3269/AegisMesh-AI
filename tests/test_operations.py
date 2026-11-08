"""Integration checks for actual business effects and the public API boundary."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.operations import api, provider
from app.operations.models import Action, SAFE_FIELDS
from app.operations.service import Operations
from app.operations.store import Store


@pytest.fixture
def lab(tmp_path, monkeypatch):
    service = Operations(Store(tmp_path))
    monkeypatch.setattr(api, "operations", lambda: service)
    monkeypatch.setenv("AEGIS_PROVIDER", "offline")
    client = TestClient(app)
    credentials = json.loads((tmp_path / "credentials.json").read_text())
    tokens = {
        role: client.post("/api/ops/login", json=cred).json()["token"]
        for role, cred in credentials.items()
    }
    users = {role: service.store.authenticate(token) for role, token in tokens.items()}
    return service, client, tokens, users


def headers(tokens, role="agent"):
    return {"Authorization": "Bearer " + tokens[role]}


def propose(service, user, **changes):
    action = Action(tool="reports.export", fields=SAFE_FIELDS, **changes)
    return service.propose(
        user, action, "Test proposal", {"provider": "explicit_test", "live_llm": False}
    )


def personal(service, user):
    return service.propose(
        user,
        Action(tool="reports.export", fields=["ticket_id", "email"]),
        "Personal report",
        {"provider": "test"},
    )


def test_authentication_and_role_claims(lab):
    service, client, tokens, users = lab
    assert client.get("/api/ops/workspace").status_code == 401
    assert (
        client.get(
            "/api/ops/workspace", headers={"Authorization": "Bearer demo-admin"}
        ).status_code
        == 401
    )
    assert (
        client.get("/api/ops/workspace", headers=headers(tokens)).json()["user"]["role"]
        == "agent"
    )
    assert (
        client.post(
            "/api/ops/login",
            json={
                "username": "agent@aegis.local",
                "password": "wrong",
                "role": "manager",
            },
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/cyberforge/directory/principals", headers=headers(tokens)
        ).status_code
        == 403
    )
    directory = client.get(
        "/api/cyberforge/directory/principals", headers=headers(tokens, "manager")
    ).json()
    assert all("api_token" not in p for p in directory["principals"])


def test_real_update_verified_and_persistent(lab):
    service, client, tokens, users = lab
    p = service.propose(
        users["agent"],
        Action(tool="tickets.update", ticket_id=101, status="resolved"),
        "Resolve",
        {},
    )
    result = service.execute(users["agent"], p["id"])
    assert result["executed"] and result["verified"] and result["side_effects"]
    reopened = Operations(Store(service.store.directory))
    assert reopened.dashboard(users["agent"])["tickets"][0]["status"] == "resolved"
    assert reopened.dashboard(users["agent"])["audit"]["valid"]


def test_minimized_export_download_hash_and_fields(lab):
    service, client, tokens, users = lab
    p = propose(service, users["agent"])
    r = service.execute(users["agent"], p["id"])
    response = client.get(r["output"]["download_url"], headers=headers(tokens))
    assert response.status_code == 200
    assert hashlib.sha256(response.content).hexdigest() == r["output"]["sha256"]
    assert response.text.splitlines()[0] == ",".join(SAFE_FIELDS)
    assert "example.test" not in response.text
    assert r["output"]["rows"] == 6 and r["verified"]
    assert (
        client.get(
            r["output"]["download_url"], headers=headers(tokens, "manager")
        ).status_code
        == 403
    )


def test_approval_workflow_and_replay(lab):
    service, client, tokens, users = lab
    p = personal(service, users["agent"])
    pending = service.execute(users["agent"], p["id"])
    assert pending["status"] == "pending_approval" and not pending["executed"]
    with service.store.transaction() as db:
        assert db.execute("SELECT COUNT(*) FROM exports").fetchone()[0] == 0
    approval_id = pending["approval_id"]
    assert (
        client.post(
            f"/api/ops/approvals/{approval_id}/review",
            headers=headers(tokens),
            json={"decision": "APPROVED"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/ops/approvals/{approval_id}/review",
            headers=headers(tokens, "manager"),
            json={"decision": "APPROVED", "role": "manager"},
        ).status_code
        == 422
    )
    service.review(users["manager"], approval_id, "APPROVED", "Reviewed")
    result = service.execute(users["agent"], p["id"], approval_id=approval_id)
    assert result["verified"] and result["executed"]
    replay = service.execute(users["agent"], p["id"], approval_id=approval_id)
    assert replay["decision"] == "DENY" and not replay["side_effects"]


def test_approval_survives_restart(lab):
    service, _, _, users = lab
    p = personal(service, users["agent"])
    pending = service.execute(users["agent"], p["id"])
    service.review(users["manager"], pending["approval_id"], "APPROVED", "Reviewed")
    reopened = Operations(Store(service.store.directory))
    assert reopened.execute(
        users["agent"], p["id"], approval_id=pending["approval_id"]
    )["verified"]


@pytest.mark.parametrize("change", ["destination", "fields", "tool"])
def test_changed_approved_action_never_executes(lab, change):
    service, _, _, users = lab
    p = personal(service, users["agent"])
    pending = service.execute(users["agent"], p["id"])
    service.review(users["manager"], pending["approval_id"], "APPROVED", "Reviewed")
    action = Action.model_validate(p["action"])
    if change == "destination":
        action.destination = "https://external.example/collect"
    elif change == "fields":
        action.fields = ["ticket_id"]
    else:
        action = Action(tool="tickets.update", ticket_id=101, status="resolved")
    r = service.execute(users["agent"], p["id"], action, pending["approval_id"])
    assert r["decision"] == "DENY" and not r["executed"]
    with service.store.transaction() as db:
        assert db.execute("SELECT COUNT(*) FROM exports").fetchone()[0] == 0
        assert (
            db.execute("SELECT status FROM tickets WHERE ticket_id=101").fetchone()[0]
            == "open"
        )


def test_external_destination_cannot_be_approved(lab):
    service, _, _, users = lab
    p = propose(
        service, users["agent"], destination="internal-reports.attacker.example"
    )
    r = service.execute(users["agent"], p["id"])
    assert r["decision"] == "DENY" and not r["approval_id"]


def test_self_approval_and_cross_user_execution_denied(lab):
    service, _, _, users = lab
    p = personal(service, users["manager"])
    r = service.execute(users["manager"], p["id"])
    with pytest.raises(PermissionError):
        service.review(users["manager"], r["approval_id"], "APPROVED", "")
    with pytest.raises(PermissionError):
        service.execute(users["agent"], p["id"])


@pytest.mark.parametrize("state", ["REJECTED", "REVOKED", "EXPIRED"])
def test_unusable_approvals(lab, state):
    service, _, _, users = lab
    p = personal(service, users["agent"])
    pending = service.execute(users["agent"], p["id"])
    if state == "EXPIRED":
        service.review(users["manager"], pending["approval_id"], "APPROVED", "")
        with service.store.transaction() as db:
            db.execute(
                "UPDATE approvals SET expires=0 WHERE id=?", (pending["approval_id"],)
            )
    else:
        service.review(users["manager"], pending["approval_id"], state, "")
    result = service.execute(
        users["agent"], p["id"], approval_id=pending["approval_id"]
    )
    assert result["decision"] == "DENY" and not result["executed"]


def test_concurrent_approval_consumed_once(lab):
    service, _, _, users = lab
    p = personal(service, users["agent"])
    pending = service.execute(users["agent"], p["id"])
    service.review(users["manager"], pending["approval_id"], "APPROVED", "")

    def run(_):
        return service.execute(
            users["agent"], p["id"], approval_id=pending["approval_id"]
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, range(4)))
    assert sum(r["executed"] for r in results) == 1
    assert sum(r["decision"] == "DENY" for r in results) == 3


def test_audit_failure_rolls_back_business_effect_and_consumption(lab, monkeypatch):
    service, _, _, users = lab
    p = personal(service, users["agent"])
    pending = service.execute(users["agent"], p["id"])
    service.review(users["manager"], pending["approval_id"], "APPROVED", "")

    def fail(*args):
        raise OSError("Injected storage failure")

    monkeypatch.setattr(service.store, "append_audit", fail)
    with pytest.raises(OSError):
        service.execute(users["agent"], p["id"], approval_id=pending["approval_id"])
    with service.store.transaction() as db:
        assert db.execute("SELECT COUNT(*) FROM exports").fetchone()[0] == 0
        assert (
            db.execute(
                "SELECT status FROM approvals WHERE id=?", (pending["approval_id"],)
            ).fetchone()[0]
            == "APPROVED"
        )


def test_tampered_ledger_disables_future_execution(lab):
    service, _, _, users = lab
    p = propose(service, users["agent"])
    service.execute(users["agent"], p["id"])
    with service.store.transaction() as db:
        db.execute("UPDATE audit SET payload='{}' WHERE seq=1")
    assert not service.dashboard(users["agent"])["audit"]["valid"]
    q = propose(service, users["agent"])
    with pytest.raises(ValueError, match="Audit integrity"):
        service.execute(users["agent"], q["id"])


def test_verification_failure_rolls_back_export(lab, monkeypatch):
    service, _, _, users = lab
    p = propose(service, users["agent"])
    original = service._execute_tool

    def unverified(*args):
        output, _, side_effects = original(*args)
        return output, False, side_effects

    monkeypatch.setattr(service, "_execute_tool", unverified)
    with pytest.raises(ValueError, match="verification failed"):
        service.execute(users["agent"], p["id"])
    with service.store.transaction() as db:
        assert db.execute("SELECT COUNT(*) FROM exports").fetchone()[0] == 0


def test_csv_phone_values_are_literal_in_spreadsheets(lab):
    service, _, _, users = lab
    p = service.propose(
        users["agent"],
        Action(tool="reports.export", fields=["ticket_id", "phone"]),
        "Contact export",
        {},
    )
    pending = service.execute(users["agent"], p["id"])
    service.review(users["manager"], pending["approval_id"], "APPROVED", "Reviewed")
    result = service.execute(
        users["agent"], p["id"], approval_id=pending["approval_id"]
    )
    report = service.export(users["agent"], result["output"]["export_id"])
    assert "'+91-0000000101" in report["content"]


def test_expired_proposal_cannot_run(lab):
    service, _, _, users = lab
    p = propose(service, users["agent"])
    with service.store.transaction() as db:
        db.execute("UPDATE proposals SET expires=0 WHERE id=?", (p["id"],))
    with pytest.raises(ValueError, match="expired"):
        service.execute(users["agent"], p["id"])


def test_extra_fields_and_sql_column_injection_rejected(lab):
    service, client, tokens, users = lab
    r = client.post(
        "/api/ops/proposals",
        headers=headers(tokens),
        json={
            "tool": "reports.export",
            "fields": ["email FROM tickets; DROP TABLE tickets;--"],
        },
    )
    assert r.json()["decision"] == "DENY"
    assert (
        client.post(
            "/api/ops/proposals",
            headers=headers(tokens),
            json={"tool": "tickets.list", "role": "manager"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/ops/proposals",
            headers=headers(tokens),
            json={"tool": "tickets.update", "ticket_id": True, "status": "resolved"},
        ).status_code
        == 422
    )


def test_auditor_cannot_mutate(lab):
    service, client, tokens, users = lab
    p = propose(service, users["auditor"])
    assert service.execute(users["auditor"], p["id"])["decision"] == "DENY"
    assert (
        client.post(
            "/api/ops/chat",
            headers=headers(tokens, "auditor"),
            json={"message": "Resolve ticket 101"},
        ).status_code
        == 403
    )


def test_chat_is_a_proposal_only_and_discloses_offline(lab):
    service, client, tokens, users = lab
    data = client.post(
        "/api/ops/chat", headers=headers(tokens), json={"message": "Resolve ticket 101"}
    ).json()
    assert data["proposal"]["action"]["tool"] == "tickets.update"
    assert not data["executed"] and not data["provider"]["live_llm"]
    assert service.dashboard(users["agent"])["tickets"][0]["status"] == "open"


def test_provider_failure_never_falls_back_or_proposes(lab, monkeypatch):
    service, client, tokens, users = lab
    monkeypatch.setenv("AEGIS_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    r = client.post(
        "/api/ops/chat", headers=headers(tokens), json={"message": "Resolve ticket 101"}
    )
    assert r.status_code == 503
    assert not service.dashboard(users["agent"])["receipts"]


def test_logout_and_session_expiry(lab):
    service, client, tokens, users = lab
    assert client.post("/api/ops/logout", headers=headers(tokens)).status_code == 200
    assert client.get("/api/ops/workspace", headers=headers(tokens)).status_code == 401
    with service.store.transaction() as db:
        db.execute("UPDATE sessions SET expires=0")
    assert (
        client.get("/api/ops/workspace", headers=headers(tokens, "manager")).status_code
        == 401
    )


def test_legacy_identity_missing_or_prefix_token_is_rejected():
    from agents.enforcement.identity_registry import (
        IDENTITY_SERVICE,
        IdentityVerificationError,
    )

    for token in [None, "demo-admin", "cf-admin", ""]:
        with pytest.raises(IdentityVerificationError):
            IDENTITY_SERVICE.verify_and_resolve_principal("U_ADMIN", "ADMIN", token)


def test_legacy_executor_rejects_forged_ticket_and_changed_arguments():
    from agents.enforcement.tools import get_tool, DirectExecutionBypassError
    from agents.enforcement.canonical_action import (
        CanonicalAction,
        PrincipalIdentity,
        ResourceScope,
    )
    from agents.enforcement.tickets import ExecutionTicket

    tool = get_tool("database_execute")
    action = CanonicalAction(
        "TEST",
        PrincipalIdentity("U_ENG", "ENGINEER"),
        tool.name,
        "1.2.0",
        "READ",
        ResourceScope("internal-db"),
        {"query": "SELECT 1", "database": "internal-db"},
    )
    ticket = ExecutionTicket(
        "TEST-TICKET",
        action.compute_digest(),
        tool.name,
        datetime.now(timezone.utc).isoformat(),
    )
    with pytest.raises(DirectExecutionBypassError):
        tool.execute_protected(
            {"query": "DROP TABLE customers", "database": "internal-db"},
            ticket,
            action.resource_scope,
            action,
        )
    forged = type("Forged", (), {"verify": lambda *a, **k: (True, "Valid")})()
    with pytest.raises(DirectExecutionBypassError):
        tool.execute_protected(action.arguments, forged, action.resource_scope, action)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["groq", "openai"])
async def test_live_provider_transport_contract_without_network(
    monkeypatch, provider_name
):
    import httpx

    monkeypatch.setenv("AEGIS_PROVIDER", provider_name)
    monkeypatch.setenv(provider_name.upper() + "_API_KEY", "test-key-not-real")
    monkeypatch.setenv(provider_name.upper() + "_MODEL", "test-model")
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "explanation": "Resolve requested ticket",
                                    "action": {
                                        "tool": "tickets.update",
                                        "ticket_id": 101,
                                        "status": "resolved",
                                    },
                                }
                            )
                        }
                    }
                ],
                "usage": {"total_tokens": 30},
            },
        )

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        provider.httpx,
        "AsyncClient",
        lambda **kw: original_client(transport=httpx.MockTransport(handle), **kw),
    )
    result, info = await provider.plan("Resolve ticket 101")
    assert result.action.ticket_id == 101
    assert info["provider"] == provider_name and info["health"] == "request_succeeded"
    assert requests[0]["response_format"]["json_schema"]["strict"] is True
    assert "test-key" not in json.dumps(requests)


@pytest.mark.asyncio
async def test_invalid_model_output_does_not_authorize(monkeypatch):
    import httpx

    monkeypatch.setenv("AEGIS_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")

    def handle(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"explanation":"Approved","action":{"tool":"reports.export","fields":["email"],"role":"manager"}}'
                        }
                    }
                ]
            },
        )

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        provider.httpx,
        "AsyncClient",
        lambda **kw: original_client(transport=httpx.MockTransport(handle), **kw),
    )
    with pytest.raises(provider.ProviderUnavailable):
        await provider.plan("Export a report")
