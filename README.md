# CyberForge: Runtime AI Security & Policy Intelligence
*Built on the AegisMesh-AI Autonomous Governance Control Plane*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![IBM Granite 7B](https://img.shields.io/badge/AI%20Reasoning-IBM%20Granite%207B-indigo.svg)](https://huggingface.co/ibm-granite/granite-7b-instruct)
[![Runtime Enforcement](https://img.shields.io/badge/Boundary%20Enforcement-Cryptographic%20SHA--256-emerald.svg)]()
[![Adversarial Suite](https://img.shields.io/badge/Adversarial%20Lab-21%20Scenarios%20%7C%2012%20Categories-red.svg)]()
[![Benchmark](https://img.shields.io/badge/Benchmark-Reproducible%204--Mode%20Eval-purple.svg)]()
[![Tests](https://img.shields.io/badge/Tests-91%2F91%20Passed-brightgreen.svg)]()
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> **Central Proposition**:  
> *"Detect the attack, enforce the policy at the execution boundary, and prove that the decision remains safe under adversarial conditions and policy changes."*

---

## 🎯 Executive Overview & Product Proposition

Detecting malicious prompts with LLM heuristics or input filters is insufficient for enterprise autonomy. When an AI agent is attacked via prompt injection, indirect context contamination, or tool argument tampering:
1. A compromised language model may hallucinate that an action is safe or claim that an attack was blocked while still issuing the harmful tool call.
2. A governance classifier may be bypassed by adversarial encoding or policy ambiguity.
3. If tool executors are directly callable, attacks succeed regardless of upstream detection.

**CyberForge** bridges this critical gap by implementing **Runtime Enforcement at the Physical Execution Boundary**. It guarantees that an AI agent cannot execute a prohibited action simply because a model produces an unsafe response or a governance layer returns an incorrect approval. Every protected action must pass through an authoritative execution gateway that validates a canonical cryptographic action digest immediately before invocation, issues single-use execution tickets, and prevents any unauthorized side effect on underlying enterprise systems.

---

## 🏛️ End-to-End System Architecture

```
                                  CYBERFORGE RUNTIME PIPELINE
                                  
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ 1. User Request / Adversarial Prompt                                                   │
  └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
                                              ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ 2. AI Agent (IBM Granite 7B / Multi-Agent Reasoning)                                  │
  │    Produces Proposed Tool Call & Target Parameters                                     │
  └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
                                              ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ 3. Canonical Action Normalization & Cryptographic Digestion                            │
  │    Action: {principal, tool, operation, target, sorted_arguments, policy_version}      │
  │    SHA-256 Canonical Digest generated                                                  │
  └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
                                              ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ 4. Authoritative Policy Evaluation & TOCTOU Verification                               │
  │    - 3-Stage Risk Model (Inherent Risk, Controls Mitigation, Effective Risk)            │
  │    - Database Policy Rule Precedence & Time-of-Check Validation                        │
  │    - Decisions: ALLOW | DENY | REQUIRE_APPROVAL                                        │
  └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
                    ┌─────────────────────────┴────────────────────────┐
                    │                                                  │
             [ REQUIRE_APPROVAL ]                               [ ALLOW / DENY ]
                    │                                                  │
                    ▼                                                  │
  ┌───────────────────────────────────┐                                │
  │ State Machine Approval Binding    │                                │
  │ - Cryptographic HMAC Token        │                                │
  │ - Strict Expiration (300s TTL)    │                                │
  │ - Single-Use Consumption          │                                │
  └─────────────────┬─────────────────┘                                │
                    │                                                  │
                    └─────────────────────────┬────────────────────────┘
                                              │
                                              ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ 5. Runtime Enforcement Gateway (Physical Execution Boundary)                           │
  │    - Direct Execution Prevention: Direct tool calls throw DirectExecutionBypassError   │
  │    - Single-Use Execution Ticket Issuance & Immediate Revocation                       │
  │    - Preflight Audit Ledger Guarantee Check                                            │
  │    - DENY -> Physical Execution Halted (Zero Side Effects Produced)                    │
  │    - ALLOW -> Protected Executor Invoked with Ticket                                   │
  └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
                                              ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ 6. Cryptographic Audit Ledger & Side-Effect Verification                               │
  │    - Merkle-linked SHA-256 Block Hash Chaining                                         │
  │    - HMAC-SHA256 Signatures over Action Digest & Ticket                                │
  │    - Empirical Tool Side-Effect Verification Recorded                                  │
  └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Core Security Pillars

### 1. P0 — Runtime Enforcement at the Execution Boundary
- **Direct Execution Prevention**: Protected tools (`database_execute`, `customer_data_export`, `cloud_resource_deploy`, `payment_transfer`, `system_config_update`, `external_webhook_call`) cannot be called directly. Invoking `.execute()` raises `DirectExecutionBypassError`. Only the `RuntimeEnforcementGateway` holding a valid internal session can invoke `execute_protected()`.
- **Canonical Action Digestion**: All action arguments are deeply sorted and serialized into a canonical representation. Authorization decisions are cryptographically bound to the SHA-256 digest of this canonical action.
- **TOCTOU Revalidation**: Immediate revalidation immediately prior to execution ensures that policy edits or permission revocations occurring between planning and execution block the action. Any post-evaluation argument alteration invalidates the digest and causes an instant denial.
- **Approval State Machine**: High-risk operations requiring approval issue a cryptographically signed HMAC approval ticket bound to the exact principal, tool, action digest, and policy version. Approvals are single-use, strictly expire after their TTL, and reject replay attempts.
- **Physical Side-Effect Verification**: When an action is denied, the underlying executor is never reached. Physical side-effect counters remain zero.

### 2. P0 — Adversarial Prompt Injection & Tool Abuse Suite
Includes **21 automated adversarial scenarios** spanning **12 distinct attack categories**:
1. `DIRECT_PROMPT_INJECTION`: Jailbreaks and adversarial instruction overrides.
2. `INDIRECT_PROMPT_INJECTION`: Payloads embedded in retrieved RAG documents.
3. `SYSTEM_OVERRIDE_ATTEMPT`: Deliberate attempts to replace system prompt boundaries.
4. `TOOL_ARGUMENT_MANIPULATION`: SQL injections, destructive script flags, directory traversals.
5. `UNAUTHORIZED_DATA_ACCESS`: Unauthorized attempts to read restricted tables and data vaults.
6. `PRIVILEGE_ESCALATION`: Role-spoofing and unauthorized clearance assertions.
7. `APPROVAL_BYPASS`: Forged approval tokens, replay attacks, and expired ticket submission.
8. `MALICIOUS_RETRIEVED_CONTENT`: Misleading contextual guidance intended to trigger unsafe actions.
9. `MULTI_STEP_ATTACK`: Staged reconnaissance followed by destructive execution.
10. `POLICY_AMBIGUITY_EXPLOITATION`: Crafting edge-case inputs to exploit coarse rules.
11. `EXECUTION_AFTER_DENIAL`: Attempting re-execution through secondary tools after denial.
12. `PROVIDER_FAILURE_EXPLOIT`: Triggering provider timeouts to test fallback authorization leaks.

Each scenario produces an empirical classification:
- `ATTACK_BLOCKED_AND_PREVENTED`: Attack was detected and execution was completely blocked with zero side effects.
- `POLICY_BLOCKED_EXECUTION`: Attack bypassed upstream detection, but runtime policy enforcement blocked execution at the boundary.
- `LEGITIMATE_ACTION_PERMITTED`: Benign request authorized and executed correctly.
- `ATTACK_SUCCEEDED_UNAUTHORIZED_EXECUTION`: Critical security failure where unauthorized side effects occurred.

### 3. P0 — Fail-Closed Policy & Model Failure Handling
- **Database / Retrieval Failure**: When the policy database is unavailable, timed out, or unparseable, the gateway defaults to `DENY`.
- **Model Provider Outages**: Failures in the reasoning provider cannot grant ambient authorization.
- **Mock Provider Sandboxing**: In demonstration or fallback mode, mock providers inherit zero production authorization rights.
- **Audit Persistence Preflight**: If the cryptographic audit ledger cannot guarantee persistence, protected actions are blocked.
- **Error Sanitization**: All error messages strip API keys, database credentials, internal file paths, and raw stack traces before returning to callers.

### 4. P1 — Reproducible Attack Benchmark Evaluation Engine
Runs all 21 scenarios across **4 configurable execution modes**:
1. `BASELINE_NO_ENFORCEMENT`: Raw model without guardrails or enforcement.
2. `GOVERNANCE_DETECTION_ONLY`: Heuristic prompt analysis without execution boundary controls.
3. `RUNTIME_ENFORCEMENT`: CyberForge Gateway with canonical action verification and fail-closed controls.
4. `RUNTIME_HARDENED`: CyberForge Gateway combined with hardened input normalization.

**Precise Metrics Tracked**:
- **Attack Success Rate (ASR)**: $\frac{\text{Successful Adversarial Objectives}}{\text{Valid Adversarial Scenarios}}$
- **Unauthorized Action Rate (UAR)**: $\frac{\text{Scenarios Producing Unauthorized Side Effects}}{\text{Valid Scenarios Attempting Such Action}}$
- **Enforcement Success Rate**: $\frac{\text{Correctly Gated Scenarios}}{\text{Total Scenarios}}$
- **False Positive Rate (FPR)**: $\frac{\text{Benign Requests Incorrectly Denied}}{\text{Valid Benign Requests}}$
- **Latency Distribution**: Median and p95 latency measured in milliseconds per execution.
- **Export Formats**: One-click export to CSV and JSON for audit compliance.

### 5. P1 — Policy-Change Intelligence & Regression Visualization
- **Semantic & Unified Policy Diffs**: Calculates textual and structured diffs across policy versions.
- **Behavioral Shift Analysis**: Automatically replays adversarial and benign scenarios against both active and candidate versions.
- **Regression Detection**: Flags newly permitted attacks, newly blocked benign actions, or altered approval gates before activation.

---

## 📊 Measured Benchmark Results

Measured empirical results across the 21-scenario suite in CyberForge:

| Metric | Baseline (No Enforcement) | Governance Detection Only | CyberForge Runtime Enforcement | CyberForge Hardened Runtime |
| :--- | :---: | :---: | :---: | :---: |
| **Attack Success Rate (ASR)** | **94.7%** | **42.1%** | **0.0%** | **0.0%** |
| **Unauthorized Action Rate (UAR)** | **94.7%** | **42.1%** | **0.0%** | **0.0%** |
| **Enforcement Success Rate** | **5.3%** | **57.9%** | **100.0%** | **100.0%** |
| **False Positive Rate (FPR)** | **0.0%** | **0.0%** | **0.0%** | **0.0%** |
| **Median Execution Latency** | **0.08 ms** | **0.09 ms** | **0.13 ms** | **0.14 ms** |

*Notice: Under Governance Detection Only, 42.1% of attacks still produced physical side effects because heuristic filters failed to detect subtle prompt injections. Under CyberForge Runtime Enforcement, 100% of unauthorized executions were physically blocked at the tool boundary (0.0% UAR).*

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10+, FastAPI, Pydantic V2, Uvicorn, SQLite
- **Security & Cryptography**: SHA-256 Canonical Argument Digestion, HMAC-SHA256 Signatures, Merkle Hash-Chained Audit Ledger
- **AI Reasoning**: IBM Granite 7B (`ibm-granite/granite-7b-instruct`) via Hugging Face Router API, with sandboxed local fallbacks
- **Frontend Dashboard**: Cybersecurity SaaS Single Page Application with interactive tabs for Execution Traces, Adversarial Lab, Benchmark Center, Policy Intelligence, Audit Explorer, and Settings
- **Client App (React/Vite)**: TypeScript, Vite, React 18 frontend in `frontend/`

---

## 🚀 Quickstart & Local Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.10, 3.11, 3.12, 3.13, 3.14)
- Node.js 18+ (for React frontend development)
- Git

### 1. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/Sanjayram3269/AegisMesh-AI.git
cd AegisMesh-AI

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python backend dependencies
pip install -r backend/requirements.txt
```

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration parameters:
```env
APP_ENV=development
DEMO_MODE=true
FAIL_CLOSED=true
CYBERFORGE_APPROVAL_KEY=your_secure_approval_hmac_key
CYBERFORGE_AUDIT_KEY=your_secure_audit_hmac_key
```

### 3. Launch the Server
```bash
python3 run_server.py
```
Open **`http://localhost:8000`** in your browser to access the CyberForge Dashboard.

---

## 🧪 Automated Testing Suite

The test suite covers runtime enforcement, TOCTOU safety, adversarial scenarios, failure modes, policy regressions, and API contracts.

Run all tests:
```bash
PYTHONPATH=. .venv/bin/pytest tests -v
```

### Test Suite Breakdown (91 Tests Passing)
- `tests/test_runtime_enforcement.py` (9 tests): Direct tool bypass prevention, canonical action digest matching, single-use approval consumption, expiration, replay rejection, side-effect prevention.
- `tests/test_adversarial_benchmark.py` (5 tests): Full 21-scenario benchmark execution, 4-mode metrics verification, empirical side-effect verification, CSV/JSON export.
- `tests/test_fail_closed.py` (6 tests): Audit failure preflight blocks, mock provider privilege containment, error message sanitization (no key or trace leakage).
- `tests/test_policy_regression.py` (3 tests): Policy diffing, behavioral regression detection between versions.
- `tests/test_cyberforge_api.py` (8 tests): REST API endpoints for execution, traces, scenarios, benchmark, audit verification, and tool catalog.
- `tests/test_decision_engine.py` (24 tests): 3-stage risk model boundary checks, policy precedence, mitigation deductions.
- `tests/test_policy_evolution.py` (10 tests): Historical replay simulation, conflict analysis, approval workflow.
- `tests/test_four_policy_scenarios.py` (4 tests): Ground truth enterprise policy enforcement scenarios.
- `tests/test_two_stage_risk.py` (5 tests): Inherent vs effective risk transitions.
- `tests/test_providers.py` (7 tests): IBM Granite provider handling and mock fallbacks.
- `tests/test_agents.py` (4 tests): Multi-agent pipeline end-to-end evaluation.
- `tests/test_policies.py` (6 tests): Policy CRUD and status transitions.

---

## 📡 API Reference

### CyberForge Runtime Enforcement Endpoints
- `POST /api/cyberforge/execute`: Submit a proposed action to the Runtime Enforcement Gateway. Validates canonical digest, checks TOCTOU policies, issues tickets, and records cryptographic audit traces.
- `GET /api/cyberforge/traces`: Fetch chronological execution traces with canonical digests, decisions, and audit block hashes.
- `GET /api/cyberforge/tools`: Inspect registered protected tools, schemas, allowed targets, and physical side-effect counters.
- `GET /api/cyberforge/overview`: High-level security posture KPIs, invocation volumes, and blocked action counts.

### Adversarial Lab Endpoints
- `GET /api/cyberforge/adversarial/scenarios`: List all 21 adversarial attack scenarios with categories and severity.
- `POST /api/cyberforge/adversarial/run`: Execute a specific scenario against a chosen agent configuration mode (`RUNTIME_ENFORCEMENT`, `GOVERNANCE_DETECTION_ONLY`, `BASELINE_NO_ENFORCEMENT`, `RUNTIME_HARDENED`).

### Benchmark Center Endpoints
- `POST /api/cyberforge/benchmark/run`: Execute the complete 21-scenario evaluation across all categories and calculate precise empirical metrics.
- `GET /api/cyberforge/benchmark/export`: Export benchmark results in CSV or JSON format (`?run_id=...&format=csv|json`).

### Audit & Cryptographic Integrity Endpoints
- `GET /api/cyberforge/audit/verify`: Verify the cryptographic Merkle/hash-chain integrity and HMAC signatures across all audit blocks.

### Core Governance & Policy Intelligence Endpoints
- `POST /api/govern`: Submit an agent request for multi-agent evaluation and 3-stage risk scoring.
- `GET /api/policies`: List enterprise policies.
- `POST /api/policies`: Create new policy rules.
- `PUT /api/policies/{policy_id}`: Edit policy with automatic policy evolution impact scoring.
- `GET /api/policy-evolution/events`: Review historical replay simulations and regression reports.

---

## 🔒 Security Threat Model & Assumptions

1. **Threat Model**:
   - **Compromised AI Model**: The reasoning model or LLM provider cannot be trusted as an authorization decider. Attackers may succeed in prompt injection or instruction override.
   - **Untrusted Client Inputs**: Frontend approval flags, client-submitted policy evaluations, and caller claims are discarded. All validations occur on the server.
   - **Adversarial Tool Arguments**: Arguments are treated as hostile payloads and must conform to strict tool schemas and resource allowlists.
   - **Time-of-Check / Time-of-Use (TOCTOU)**: Policies and permissions can change between the moment an agent plans an action and the moment it executes. Revalidation is mandatory at the physical boundary.
2. **Guarantees**:
   - Direct execution of protected tools without gateway mediation is physically prohibited.
   - A denied action guarantees zero physical side effects on target tools.
   - System failure defaults to closed (`DENY`), preventing fallback privilege escalations.
   - Audit records are tamper-evident and cryptographically signed.

---

## 📜 License

CyberForge is open-source software licensed under the [Apache License 2.0](LICENSE).
