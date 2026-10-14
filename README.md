# CyberForge: The Runtime Security Layer for Autonomous AI Agents
*Built on the AegisMesh-AI Governance & Security Platform for the Mitigata CyberForge Challenge*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Runtime Enforcement](https://img.shields.io/badge/Runtime%20Enforcement-HMAC--SHA--256%20Tickets-emerald.svg)]()
[![Adversarial Suite](https://img.shields.io/badge/Adversarial%20Lab-21%20Scenarios%20%7C%2013%20Categories-red.svg)]()
[![Benchmark](https://img.shields.io/badge/Benchmark-100%25%20Attack%20Blocking%20Rate-purple.svg)]()
[![Tests](https://img.shields.io/badge/Tests-105%2F105%20Passed-brightgreen.svg)]()
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> **Central Security Principle**:  
> **An AI agent's recommendation is not an authorization decision.** Every protected operation must pass through an authoritative, fail-closed runtime enforcement boundary that validates canonical digests, authoritative server-side identities, and cryptographic execution tickets before any physical side effect occurs.

---

## 📑 Core Documentation Deliverables

| Document | Purpose & Description |
| :--- | :--- |
| **[SECURITY_AUDIT.md](SECURITY_AUDIT.md)** | Initial code audit, confirmed vulnerabilities (SEC-VULN-01 to 07), remediation architecture, and residual risk analysis. |
| **[THREAT_MODEL.md](THREAT_MODEL.md)** | Assets, trust boundaries, attacker capabilities, threat matrix (THR-01 to 12), and explicit limitations. |
| **[SECURITY_TEST_RESULTS.md](SECURITY_TEST_RESULTS.md)** | Full test execution breakdown across 105 passed test cases, Scenarios A–E, and adversarial test suites. |
| **[BENCHMARK_RESULTS.json](BENCHMARK_RESULTS.json)** | Machine-generated benchmark evaluation data across all 4 execution modes (162 KB). |
| **[DEMO_RUNBOOK.md](DEMO_RUNBOOK.md)** | Step-by-step 5-minute live hackathon presentation script covering Scenarios A through E. |

---

## 🏛️ System Architecture

```
                                      CYBERFORGE RUNTIME ARCHITECTURE
                                      
    ┌───────────────────────────┐
    │      AI Agent             │  (Subject to prompt injection, malicious context,
    │ (Planner / LLM Reasoning) │   jailbreaks, and compromised outputs)
    └─────────────┬─────────────┘
                  │ [Untrusted Proposed Action & Arguments]
                  ▼
    ┌───────────────────────────────────────────────────────────┐
    │          CyberForge Runtime Enforcement Gateway           │
    │  - Schema Validation & Argument Canonicalization          │
    │  - Deterministic SHA-256 Canonical Action Digest Binding  │
    └─────────────┬─────────────────────────────────────────────┘
                  │
                  ▼
    ┌───────────────────────────────────────────────────────────┐
    │       Identity & Authoritative Policy Evaluation          │
    │  - Server-Side Identity Directory (Anti-Role Spoofing)    │
    │  - Multi-Factor Governance & Risk Classification          │
    │  - Fail-Closed Policy Exception Envelope                  │
    └─────────────┬─────────────────────────────────────────────┘
                  │
                  ▼
    ┌───────────────────────────────────────────────────────────┐
    │                Human Approval Verification                │
    │  - Required for High-Risk & High-Impact Operations        │
    │  - Bound to Canonical Action Digest, Principal & TTL      │
    │  - Atomic Single-Use Consumption & Revocation State       │
    └─────────────┬─────────────────────────────────────────────┘
                  │ [Issued Single-Use Signed ExecutionTicket]
                  ▼
    ┌───────────────────────────────────────────────────────────┐
    │               Protected Tool Executor Barrier             │
    │  - Validates Ticket HMAC Signature & Single-Use Status    │
    │  - Rejects Direct Invocations without Valid Tickets       │
    │  - Zero Execution on Denied / Escalated Requests          │
    └─────────────┬─────────────────────────────────────────────┘
                  │ [Authorized Invocation Only]
                  ▼
    ┌───────────────────────────────────────────────────────────┐
    │                 Simulated Infrastructure                  │
    │  - Workstations (Normal & Compromised)                    │
    │  - Critical Domain Controller (`srv-domain-controller-01`)│
    │  - Enterprise User Accounts & Network ACLs                │
    │  - Observable State Before & State After Snapshots        │
    └───────────────────────────────────────────────────────────┘
                  │
                  ├───────────────────────────────┐
                  ▼                               ▼
    ┌───────────────────────────┐   ┌───────────────────────────┐
    │   Tamper-Evident Ledger   │   │ Policy Regression Engine  │
    │ - SHA-256 Hash Chain      │   │ - Pre-deployment Sandbox  │
    │ - Before/After Snapshots  │   │ - Detects Policy Loosen   │
    │ - Audit Verification API  │   │ - Blocks Unsafe Changes   │
    └───────────────────────────┘   └───────────────────────────┘
```

---

## ⚡ Key Security Guarantees & Features

### 1. Authoritative Physical Execution Barrier
- **Zero Direct Invocations**: Protected tools (`database_execute`, `customer_data_export`, `cloud_resource_deploy`, `payment_transfer`, `system_config_update`, `external_webhook_call`, `isolate_workstation`, `disable_server`, `restart_service`) cannot be called directly. Invoking `execute_protected()` without a valid, unconsumed `ExecutionTicket` raises `ExecutionBoundaryBypassError`.
- **Zero Side Effects on Denial**: When an action is denied or requires approval, the executor is never invoked and target infrastructure remains 100% unchanged.
- **Canonical Action Digest**: All action arguments are recursively sorted and hashed into a canonical SHA-256 digest. Modifying any parameter after authorization invalidates the digest and causes immediate rejection.

### 2. Authoritative Identity & Anti-Role Spoofing
- **Server-Side Trust Anchor**: Client-supplied role assertions in headers or payloads are strictly cross-checked against `AUTHORITATIVE_DIRECTORY`.
- **Privilege Escalation Prevention**: Unknown or unmapped user IDs trigger immediate `IdentityVerificationError` and fail closed.

### 3. Cryptographic Human Approval Workflow
- **Digest-Bound Approvals**: Approvals store the SHA-256 action digest. Mutating action parameters, environment, or target invalidates the approval token.
- **Atomic Single-Use State Machine**: Approvals transition atomically from `PENDING` → `APPROVED` → `CONSUMED` under thread locks in SQLite, preventing double-spend and concurrent replay attacks.
- **Revocation Support**: Approvals can be revoked by reviewers prior to execution, immediately blocking execution.

### 4. Fail-Closed Error Handling
- System dependencies (database, policy engine, AI providers) are wrapped in fail-closed exception envelopes. Any dependency failure strictly results in `DENY`.
- Sensitive error details (API keys, file paths, stack traces) are automatically masked via `mask_sensitive_error_details`.

### 5. Policy-Change Intelligence
- Before a proposed policy change is deployed, CyberForge runs the entire 21-scenario adversarial suite in an isolated sandbox against both historical and proposed versions.
- If a change permits previously blocked attacks or introduces security regressions, deployment is **BLOCKED** automatically.

---

## 🏆 Reproducible Benchmark Results

From machine-generated results in `BENCHMARK_RESULTS.json` across 21 standard scenarios (16 attacks, 5 benign controls):

| Metric | 1. Baseline (Unprotected) | 2. Detection-Only (Prompt Guardrails) | 3. CyberForge Runtime Enforcement |
| :--- | :---: | :---: | :---: |
| **Attack Scenarios Evaluated** | 16 | 16 | 16 |
| **Benign Control Scenarios** | 5 | 5 | 5 |
| **Attacks Successfully Blocked** | 0 / 16 (0.0%) | 6 / 16 (37.5%) | **16 / 16 (100.0%)** |
| **Unauthorized Action Blocking Rate** | 0.0% | 37.5% | **100.0%** |
| **Legitimate Action Blocking Rate (FP)** | 0.0% | 0.0% | **0.0%** |
| **Approval Bypass Attempts Blocked** | 0 / 2 (0.0%) | 0 / 2 (0.0%) | **2 / 2 (100.0%)** |
| **Approval Replay Attempts Blocked** | 0 / 1 (0.0%) | 0 / 1 (0.0%) | **1 / 1 (100.0%)** |
| **Executor Bypass Attempts Blocked** | 0 / 2 (0.0%) | 0 / 2 (0.0%) | **2 / 2 (100.0%)** |
| **Median Execution Latency** | 0.04 ms | 0.03 ms | **0.82 ms** |

---

## 🚀 Quickstart & Local Setup

### 1. Installation
```bash
git clone https://github.com/Sanjayram3269/AegisMesh-AI.git
cd AegisMesh-AI

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python run_server.py
```
Open **`http://localhost:8000`** in your browser to access the CyberForge Security Console.

---

## 🧪 Testing & Verification

Run the entire test suite (105 tests passing):
```bash
.venv/bin/pytest tests/ -v
```

Run the mandatory security scenarios (Scenarios A–E):
```bash
.venv/bin/pytest tests/test_mandatory_security_suite.py -v
```

Run the reproducible benchmark generator:
```bash
PYTHONPATH=.:backend .venv/bin/python3.14 -c "
from agents.adversarial.benchmark import BENCHMARK_MANAGER
from agents.adversarial.engine import ExecutionMode
for mode in [ExecutionMode.BASELINE_NO_ENFORCEMENT, ExecutionMode.GOVERNANCE_DETECTION_ONLY, ExecutionMode.RUNTIME_ENFORCEMENT]:
    run = BENCHMARK_MANAGER.run_benchmark(mode=mode)
    print(f'{mode.value:25} -> Block Rate: {1.0 - run.attack_success_rate:.1%}, Latency: {run.median_latency_ms:.2f}ms')
"
```

---

## 📡 API Reference

- `POST /api/cyberforge/execute`: Intercept and enforce policy on proposed action.
- `GET /api/cyberforge/traces`: Chronological execution traces with canonical digests and decisions.
- `GET /api/cyberforge/infrastructure/state`: Inspect observable simulated infrastructure state.
- `POST /api/cyberforge/infrastructure/reset`: Reset simulated infrastructure to known baseline.
- `GET /api/cyberforge/directory/principals`: Inspect authoritative server-side user directory.
- `POST /api/cyberforge/approvals/{id}/revoke`: Revoke an active approval request.
- `GET /api/cyberforge/adversarial/scenarios`: Full catalog of 21 adversarial attack scenarios.
- `POST /api/cyberforge/adversarial/run`: Execute a single attack scenario in chosen mode.
- `POST /api/cyberforge/benchmark/run`: Run 4-mode benchmark evaluation.
- `GET /api/cyberforge/audit/verify`: Verify SHA-256 audit ledger hash chain integrity.

---

## ⚠️ Known Limitations & Assumptions

1. **Local Hash Chain vs WORM Ledger**: The audit ledger implements a SHA-256 hash chain with cryptographic block linking. While this detects unauthorized in-app row modification or omission, it is stored locally in SQLite. A privileged administrator on the host could theoretically rewrite the database and recompute the hash chain. Production environments should stream digests to an external immutable transparency log.
2. **Deterministic Simulation**: All protected targets (domain controllers, workstations, firewall ACLs) are simulated in memory/SQLite to prevent destructive operations on host hardware.
3. **Single-Node Concurrency**: Approval locking currently uses Python thread locks and SQLite transactions. Multi-node distributed deployments require distributed locks (e.g. Redis Redlock).

---

## 📜 License

CyberForge is open-source software licensed under the [Apache License 2.0](LICENSE).
