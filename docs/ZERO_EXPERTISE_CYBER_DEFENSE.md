# Zero-Expertise Cyber Defense: Acceptance Criteria and Roadmap

## Product goal

AegisMesh should help a non-technical staff member understand security activity, choose a proportionate response, and know whether the response succeeded. The existing deterministic runtime enforcement layer remains responsible for authorization and safe execution; an AI explanation must never grant permission.

## Current prototype delivered on this branch

- A standalone dashboard at `/defense` designed around plain-language incidents.
- A demo incident API with summary counts, search, severity/status filters, grouped event counts, evidence, confidence labels, recommendations, and explicit limitations.
- A normalized JSON-alert intake endpoint with deterministic category-to-guidance mapping, idempotency by event ID, and grouping by source/type/asset. This is an import seam, not a live provider integration.
- Demo actions for acknowledging an incident, requesting support, or requesting approval.
- High-impact containment requests remain pending approval in the prototype. The prototype does not execute real containment.
- A visible simulation banner and API disclosure that no live telemetry is connected.
- Tests for demo disclosure, incident fields, filtering, approval boundary, status behavior, unknown incidents, and reset behavior.

## Challenge acceptance criteria

| Requirement | Acceptance test / evidence required |
| --- | --- |
| Automated security workflow | Ingest events from defined connectors; record source and ingestion time; process without manual copying |
| Intuitive for non-experts | Representative non-technical users can find the highest-priority incident and explain the next step without specialist assistance |
| Small-organization fit | Test clinic, school, and retail scenarios; include service criticality and operational impact |
| Threat visibility | Show monitored source coverage, last successful ingestion, affected asset/account, evidence, and gaps |
| Decision clarity | Every incident explains what happened, why it matters, urgency, evidence, recommended action, consequences, and uncertainty |
| Jargon abstraction | User-facing text passes plain-language review; technical detail remains available as an optional evidence view |
| Noise reduction | Deduplicate and correlate events; measure duplicate reduction and ensure meaningful incidents are not silently discarded |
| Actionable translation | Recommendations are grounded in event evidence and tested against a reviewed expected response |
| Guided defensive action | Provide step-by-step verification, safe response choices, approval where required, and escalation when uncertain |
| Confident action | Verify action results through the connected target system; distinguish attempted, failed, blocked, pending, and confirmed outcomes |
| No cybersecurity expertise required | Measure task completion, comprehension, and time-to-action in usability tests |

## Implementation phases

### Phase 1 — Prototype workflow (this branch)
- [x] Plain-language incident dashboard and incident detail.
- [x] Search, severity and status filters.
- [x] Demo-only grouped event counts and evidence.
- [x] Approval-aware simulated response workflow.
- [x] Explicit no-live-telemetry disclosure.
- [x] API tests added; execution still needs to be run in a configured environment.
- [ ] Build and run the frontend/backend locally and perform manual accessibility checks.

### Phase 2 — Reliable event intake and incident processing
- [x] Define a normalized JSON alert schema and import endpoint for the prototype.
- [ ] Connect an authenticated real provider or ingestion pipeline.
- [ ] Validate and normalize untrusted events; preserve original evidence and source metadata.
- [ ] Replace in-memory prototype storage with persistent incident/event storage and durable deduplication keys.
- [ ] Track source health, coverage, freshness, and ingestion failures.
- [ ] Add tests for malformed, duplicate, stale, conflicting, and incomplete events.

### Phase 3 — Response integrations and verification
- [ ] Select a narrow supported response integration, beginning in dry-run mode.
- [ ] Authenticate and authorize every action on the server.
- [ ] Bind approvals to the exact target and operation; reuse the existing enforcement layer where appropriate.
- [ ] Verify final state from the target system rather than trusting a successful API response alone.
- [ ] Add rollback/escalation guidance and tests for timeout, partial failure, and unavailable dependencies.

### Phase 4 — Evaluation and production readiness
- [ ] Build a labelled evaluation set for incident grouping, priority, explanation fidelity, and recommended actions.
- [ ] Measure false positives, missed incidents, duplicate reduction, and response correctness.
- [ ] Conduct usability tests with representative non-technical users.
- [ ] Add authentication, tenant isolation, secrets management, retention controls, and externally anchored audit evidence before any production deployment.

## Safety and claim boundaries

- Seeded incidents and all response state changes in the current prototype are simulations.
- A grouped count demonstrates the interface, not a validated production correlation algorithm.
- The current prototype accepts normalized JSON alerts through an API, but does not connect to email, identity, endpoint, firewall, SIEM, or cloud control-plane systems.
- Marking an incident reviewed is not equivalent to resolving the threat.
- A pending approval is not an executed action.
- The existing attack-blocking benchmark applies only to its documented test scenarios. It does not establish universal prevention or real-world detection accuracy.
- The interface must not report “protected” or “all clear” when telemetry is absent, stale, or incomplete.
