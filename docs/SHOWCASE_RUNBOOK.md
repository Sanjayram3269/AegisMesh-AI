# AegisMesh: eight-minute showcase

## Positioning

**AegisMesh lets an AI assistant perform useful business work while the organization controls which exact actions may execute.**

Initial user: a small customer-support team. Business tasks: reviewing tickets, updating status, and preparing reports without unnecessarily exposing personal data. The working demonstration uses a local SQLite application and fictional records. Customer demand and business impact remain hypotheses; no real customer deployment has been validated.

## Before presenting

1. Launch `start-showcase.ps1`. Keep the terminal and the local credentials available privately. Open `http://127.0.0.1:8000` and sign in as the agent.
2. Confirm the sidebar identifies Groq and the selected model. Open **AI workspace** and send one request to check access. Never display `.env` or the credential file while screen sharing.
3. If ticket 101 is already resolved, ask to **reopen ticket 101** and confirm it before starting. Historical audit records can remain; do not reset evidence to imply it never happened.
4. Prepare a separate manager session through the Approvals authentication button. Explain that this is a controlled demonstration of two distinct accounts; in a deployment they belong to different people.
5. Test the internet connection. Record a full working walkthrough beforehand. If the live provider fails, identify the failure and show the recording; offline mode must be labelled explicitly.
6. Keep a downloaded minimized report, a sensitive report, and exported evidence JSON ready. The export files contain fictional data only.
7. Keep any actual invitation/rubric available. This repository does not establish the competition's judging criteria or guarantee acceptance of upgrades.

## Timed script

| Time | Screen/action | What to say |
| --- | --- | --- |
| 0:00–0:40 | One problem slide | “A support team wants an assistant that can update records and prepare reports. A plausible AI answer is not permission to expose customer information.” |
| 0:40–1:10 | Agent overview → select a 3D stage → AI workspace | “These six stages show real server events: one model planner and five deterministic controls. AegisMesh sits between the proposal and the business tool. This is a live controlled lab with fictional customers and real database actions.” |
| 1:10–1:55 | Ask “Resolve ticket 101”; inspect and confirm | “The request is scoped to one ticket. The gateway checks policy, the database changes, and an independent read verifies the result.” |
| 1:55–2:45 | Ask “Export a customer report including email and phone”; request approval | “Personal fields require a separate manager. At this point no report has been generated.” Show fields, destination, rule and digest. |
| 2:45–3:30 | Manager approves; use “Test changed destination” | “Approval belongs to the exact action. Changing its destination does not inherit permission.” Show the blocked receipt. |
| 3:30–4:15 | Execute the original approval; download CSV; test approval replay | “The unchanged authorized report succeeds. The same approval cannot execute twice.” Open the actual file. |
| 4:15–4:55 | Security checks; ticket 104 | “This customer message contains a planted instruction. Model behavior is one layer; the execution gateway separately rejects prohibited operations.” Distinguish a real model response from an explicit tool-call test. |
| 4:55–5:40 | One architecture slide | “The model interprets. Server rules authorize. A different person reviews sensitive work. Execution produces independently checked evidence.” |
| 5:40–6:20 | Test and evaluation evidence | State the freshly measured test count. The documented live development run passed seven specific planning cases; its median is approximately 1.60 seconds. Do not call that a production SLA or general benchmark. |
| 6:20–7:00 | Codex engineering evidence | Show one code diff and the regression test for the boundary it fixes. Explain your review and verification role. |
| 7:00–7:35 | Adoption and limits | “The next pilot is one support team and one existing ticket system. We would measure task completion, human review burden and incorrect or unauthorized actions. Today we have a working local reference application.” |
| 7:35–8:00 | Close and buffer | “You saw useful work succeed, altered work fail, and a real result verified. That is accountable automation.” |

## Six-slide structure

The 3D mesh follows actual request events; a quick stage can finish between polling updates. Click a stage to inspect its role, then **Inspect event stream** for timestamps. **Replay trace** replays recorded observations and never executes another action. Avoid spending demo time rotating the scene; use the visuals to explain the execution boundary.

1. Customer, task and concrete risk.
2. AegisMesh promise; move immediately to the product.
3. Trust boundary diagram (return to it after the demo).
4. Measured engineering evidence with scope and limitations.
5. How Codex was used and what you personally verified.
6. Initial pilot, next integration, and closing statement.

## Answers to likely questions

**“Why not just prompt the model to behave?”** The model can interpret a request, but a prompt cannot grant an authenticated identity or consume an approval transaction. This gateway independently checks the actual operation.

**“Is this production-ready?”** No. It is a tested, single-organization reference application. Managed identity, HTTPS, external audit anchoring, tenant isolation and real integration evaluation remain work before production use.

**“Is every stage an AI agent?”** No. The historical repository contains specialized governance modules. The new assistant uses one model planner and deterministic identity, policy, approval and execution stages. Do not present code modules as independent LLM calls.

**“Where is ChromaDB?”** It belongs to the historical stack. The new supported-tool path retrieves reviewed policy evidence by tool scope. This is intentionally small and inspectable; it does not claim semantic ChromaDB retrieval.

**“Did OpenAI power this?”** Codex was used for implementation and verification. The verified runtime uses Groq serving `openai/gpt-oss-120b`. An OpenAI API adapter exists but was not live-verified with an OpenAI key. State all three facts separately.

**“What did Codex actually improve?”** Show the identity/approval fixes, business tool implementation, transaction rollback tests, and browser verification. See `BUILD_WITH_CODEX.md`.

**“How will you prove customer value?”** Observe a real team completing the same tasks with its existing workflow and with AegisMesh. Measure completion time, correctness, review burden and inappropriate disclosures. No savings figure has been measured yet.
