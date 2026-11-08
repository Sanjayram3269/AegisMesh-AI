# Operations API

Open `/docs` on the running application for schemas. These endpoints support the fixed support-workflow reference application; they are not a general authorization service for arbitrary tools.

## Authentication

`POST /api/ops/login` accepts only `username` and `password`. Use the randomly generated local credentials from `.local/credentials.json`. The response contains a one-hour bearer token and the server-derived account role. Every private endpoint requires `Authorization: Bearer <token>`.

Never send role assertions as authorization. The manager must sign in separately. Use `POST /api/ops/logout` to revoke a session.

## Propose, inspect, execute

1. `POST /api/ops/chat` with `{"message":"Resolve ticket 101","ticket_context_id":null}` returns a model explanation, provider metadata and a non-executing proposal.
2. Inspect its action, evidence, deterministic risk score and decision. An explanation cannot authorize execution.
3. `POST /api/ops/execute` with `{"proposal_id":"PROP-..."}` rechecks current policy and identity. An allowed operation executes; a sensitive report returns an approval ID without a business side effect.
4. A different manager calls `POST /api/ops/approvals/APP-.../review` with `{"decision":"APPROVED","comment":"Reviewed fields and destination"}` using the manager's token.
5. The original requester calls `/execute` with both `proposal_id` and `approval_id`.
6. Inspect `executed`, `verified`, `side_effects`, `output`, `canonical_digest`, `audit_hash` and measured `gateway_latency_ms`.

No automatic execution follows chat or human approval. The requester must explicitly resume the approved action.

## Supported actions

```json
{"tool":"tickets.list"}
```

```json
{"tool":"tickets.update","ticket_id":101,"status":"resolved"}
```

```json
{"tool":"reports.export","fields":["ticket_id","category","status","resolution_hours"],"destination":"internal-reports"}
```

Submit an explicit action to `POST /api/ops/proposals` to test the same gateway without a model. This seam is labelled `explicit_tool_call` in provider metadata; it never implies a successful prompt-injection attack.

Personal fields `customer_name`, `email`, `phone` and `address` require separate manager approval. `internal-reports` is an exact destination identifier, not a filesystem path or remote URL. Prohibited destinations cannot be approved.

## Inspection and downloads

- `GET /api/ops/status`: public configuration disclosure with no secrets. Configuration does not prove provider health.
- `GET /api/ops/workspace`: visible operational tickets, approvals, recent receipts, policy pack and local audit verification. Agents see their own receipts/approvals; managers and auditors can inspect organization activity.
- `GET /api/ops/tickets/104/context`: explicitly untrusted fictional customer message, excluding contact fields.
- `GET /api/ops/exports/REPORT-...`: requester-only CSV download after a fresh hash check. The `X-Content-SHA256` header contains its checksum.

The browser fetches downloads with bearer authorization and creates a local Blob; tokens are never placed in download URLs.

## Durability and integration constraints

SQLite transactions atomically couple business changes, ticket consumption, approvals and audit records. A failed transaction does not leave an export or consume an approval. Successful proposals are single-use. Proposals and approvals expire after 15 minutes.

The executor and signing key run in one application process. This is not isolation against an attacker who can execute Python on the server. External integrations need separately held credentials, restricted network paths, idempotency keys and verified state reconciliation before making stronger enforcement claims.

Legacy APIs are restricted to an authenticated workspace manager and operate on simulated infrastructure. The new business executor is separate from the legacy simulation-tool registry; it shares canonical-action hashing but uses its own transactional approval and audit storage.
