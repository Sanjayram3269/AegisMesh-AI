# AegisMesh AI — Agentic AI Governance Control Plane

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![IBM Granite 7B](https://img.shields.io/badge/AI%20Reasoning-IBM%20Granite%207B-indigo.svg)](https://huggingface.co/ibm-granite/granite-7b-instruct)
[![Governance](https://img.shields.io/badge/Governance-3--Stage%20Risk%20Model-emerald.svg)]()
[![Policy Evolution](https://img.shields.io/badge/Novelty-Autonomous%20Change%20Intelligence-purple.svg)]()
[![Tests](https://img.shields.io/badge/Tests-34%2F34%20Passed-brightgreen.svg)]()
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> **AegisMesh AI** is an enterprise-grade agentic AI governance control plane. As autonomous AI agents take actions across internal databases and external APIs, AegisMesh intercepts and evaluates proposed actions against grounded enterprise policies, computes multi-dimensional policy-aware risk scores, applies dynamic action transformations (such as data minimization & PII stripping), enforces human-in-the-loop escalation for high-impact decisions, and autonomously predicts governance impact whenever policies evolve.

---

## 🎯 Executive Summary & Value Proposition

Traditional Identity & Access Management (IAM) and Role-Based Access Control (RBAC) systems were built for human users clicking buttons in web apps. Autonomous AI agents present a fundamentally new threat model:
- AI agents dynamically construct database queries and API payloads.
- AI agents can attempt unintended bulk data exports, PII exfiltration, or destructive infrastructure changes.
- Static enterprise policies cannot dynamically evaluate intent, data sensitivity, or policy change dynamics.

**AegisMesh AI solves this by placing an authoritative, multi-agent control plane between AI agent actions and enterprise target systems.**

```
[ AI AGENTS ] 
     │
     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     AEGISGRID GOVERNANCE CONTROL PLANE                 │
│                                                                        │
│  ┌──────────────┐    ┌─────────────────┐    ┌───────────────────────┐  │
│  │ 7-Agent Flow │ ──►│ RAG Policy Base │ ──►│ IBM Granite 7B Engine │  │
│  └──────────────┘    └─────────────────┘    └───────────────────────┘  │
│         │                     │                         │              │
│         ▼                     ▼                         ▼              │
│  ┌──────────────┐    ┌─────────────────┐    ┌───────────────────────┐  │
│  │ 3-Stage Risk │    │ Action          │    │ Policy Evolution      │  │
│  │ Analysis     │    │ Transformation  │    │ Change Intelligence   │  │
│  └──────────────┘    └─────────────────┘    └───────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
     │ 
     ├──► [ APPROVE ] ➔ Execution Authorized
     ├──► [ MODIFY ]  ➔ Anonymize / Scope Payload & Re-evaluate
     ├──► [ ESCALATE] ➔ Send to CISO / Security Review
     └──► [ REJECT ]  ➔ Block Prohibited Operation
```

---

## ✨ Key Platform Pillars

### 1. Multi-Agent Governance Orchestration (7 Core Agents)
AegisMesh pipeline orchestrates 7 specialized governance agents:
1. **Planner Agent**: Decomposes proposed AI tool actions into required validation checks.
2. **Intent Agent**: Classifies action intent, data sensitivity, and external exposure.
3. **Identity Agent**: Validates user clearance, enterprise roles, and department permissions.
4. **Policy RAG Agent**: Retrieves authoritative policy evidence and clauses from enterprise knowledge base.
5. **Compliance Agent**: Evaluates action attributes against retrieved policies to detect specific violations.
6. **Risk Agent**: Calculates multi-dimensional weighted risk scores.
7. **Reviewer Agent**: Validates decision consistency and triggers human escalation if required.

### 2. 3-Stage Policy-Aware Risk Scoring System
- **Stage 1: Inherent Risk (0–100)**: Evaluates raw action sensitivity, requester clearance, and target trust *before* mitigations.
- **Stage 2: Controls & Mitigations**: Deducts risk points based on verified user authentication, approved proxy endpoints, and automated action transformations (up to -55 pts).
- **Stage 3: Effective Risk (0–100)**: Computes final risk score and maps directly to governance decision boundaries:
  - **`0–24` (LOW)**: `APPROVE`
  - **`25–49` (MEDIUM)**: `MODIFY` (Action Transformation)
  - **`50–74` (HIGH)**: `ESCALATE` (Human Review Required)
  - **`75–100` (CRITICAL)**: `REJECT`
- **Policy Precedence Guarantee**: Explicit database policies (e.g., `POL-ACC-006` or `POL-TRN-002`) override baseline risk thresholds when rule conditions match.

### 3. Autonomous Policy Evolution & Change Intelligence (Novelty Layer)
AegisMesh doesn't just evaluate user actions against policies—it autonomously analyzes what happens when enterprise policies change:
- **Canonical Before/After Snapshots**: Version control (`v1 → v2`) tracking all policy edits, creations, and deactivations.
- **Structural & Semantic Classification**: Categorizes policy changes into `COSMETIC`, `SCOPE_EXPANSION`, `DECISION_CHANGE`, `SECURITY_WEAKENING`, or `DEACTIVATION`.
- **Policy Impact Score (0–100)**: Predicts enterprise governance blast radius.
- **Historical Action Replay Simulation**: Non-mutative replay of stored audit records against updated policy rules to count affected historical actions and detect regressions.
- **Overlap & Conflict Detection**: Scans active enterprise policies for overlapping condition targets with conflicting decision outcomes.
- **Autonomous Enforcement Gate**: Low-impact policy changes are `AUTO_ENFORCED`; high-impact policy changes require elevated `PENDING_HUMAN_REVIEW` before control plane activation.

### 4. Dynamic Action Transformation Engine
When an action intent is valid but unsafe (e.g., bulk PII export or raw database query), the Transformation Agent automatically:
- Strips PII fields (email, phone numbers, SSN).
- Converts raw database export queries into aggregated metrics views.
- Routes external endpoint requests through approved internal security proxies.
- Re-evaluates transformed requests to verify effective risk reduction.

---

## 🛠️ Technology Stack

- **Backend Core**: Python 3.13+, FastAPI, Pydantic V2, Uvicorn
- **AI Reasoning Engine**: IBM Granite 7B (`ibm-granite/granite-7b-instruct:featherless-ai`) via Hugging Face Inference API with fallback to MockProvider
- **Storage & Retrieval**: SQLite + RAG Retrieval Engine
- **Frontend Architecture**: Vanilla HTML5, CSS3 Custom Tokens, Modular JavaScript SPA with zero framework bloat

---

## 🚀 Quickstart & Local Installation

### Prerequisites
- Python 3.10+ (Python 3.13 recommended)
- Git

### 1. Clone Repository & Setup Environment
```bash
git clone https://github.com/Sanjayram3269/AegisMesh-AI.git
cd AegisMesh-AI

# Create virtual environment
python -m venv venv
# Activate on Windows:
venv\Scripts\activate
# Activate on Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the root directory (or use default mock provider):
```env
HUGGINGFACE_API_KEY=your_huggingface_api_key_here
DEMO_MODE=True
LOG_LEVEL=INFO
```

### 3. Run AegisMesh Server
```bash
python run_server.py
```
The server will initialize the SQLite database, seed default enterprise policies, and start at **`http://localhost:8000`**.

---

## 🧪 Running Unit & Integration Tests

AegisMesh includes a 34-test suite covering decision engine invariants, 3-stage risk model boundary mapping, prohibited action gates, and policy evolution change intelligence.

```bash
python -m pytest tests/test_decision_engine.py tests/test_policy_evolution.py -v
```

**Expected Output**:
```text
============================== 34 passed in 11.8s ==============================
```

---

## 📡 API Reference

### 1. Evaluate AI Action Request
`POST /api/govern`

**Request Payload**:
```json
{
  "request_id": "REQ-1001",
  "user_id": "U001",
  "role": "Senior Data Analyst",
  "action": "Export anonymized aggregated customer analytics",
  "target": "approved-internal-analytics",
  "data_classification": "Internal",
  "business_purpose": "Internal executive reporting",
  "authorization_status": "Verified"
}
```

**Response**:
```json
{
  "status": 200,
  "request_id": "REQ-1001",
  "decision": "APPROVE",
  "explanation": "Governance decision: APPROVE for action.",
  "inherent_risk": { "score": 20, "level": "LOW" },
  "risk_reduction": 0,
  "effective_risk": 20,
  "decision_source": "explicit_policy",
  "confidence": 0.91
}
```

### 2. Manage Enterprise Policies (Policy-as-Code)
- `GET /api/policies`: List all active enterprise policies
- `POST /api/policies`: Create a new policy rule
- `PUT /api/policies/{policy_id}`: Edit policy criteria (triggers Policy Evolution Analysis & version increment)
- `PATCH /api/policies/{policy_id}/status`: Toggle policy active/inactive status

### 3. Policy Evolution Intelligence Endpoints
- `GET /api/policy-evolution/kpi`: Overview change metrics
- `GET /api/policy-evolution/events`: List change intelligence reports & historical replays
- `GET /api/policy-evolution/conflicts`: Detect overlapping policy rule conflicts
- `POST /api/policy-evolution/approve-enforcement`: Administrator approval for high-impact policy changes

### 4. Audit Trail & Human Review
- `GET /api/audit`: Retrieve complete governance audit trail
- `POST /api/review/{request_id}`: Submit human review decision (`APPROVE` / `REJECT`)

---

## 🏛️ Project Directory Structure

```
AegisMesh-AI/
├── agents/                      # 7 Multi-Agent Governance Pipeline
│   ├── orchestrator.py          # Central Control Plane & Stage Resolution
│   ├── planner.py               # Action Decomposition Agent
│   ├── intent.py                # Intent & Exposure Classifier Agent
│   ├── identity.py              # Identity & Clearance Agent
│   ├── compliance.py            # Policy Compliance Agent
│   ├── risk.py                  # 3-Stage Risk Model Agent
│   ├── transformation.py        # Dynamic Action Transformation Agent
│   ├── reviewer.py              # Human Escalation Agent
│   └── policy_engine.py         # Policy-as-Code Decision Engine
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI REST Endpoints (govern, policies, audit, evolution)
│   │   ├── database/            # SQLite ORM Models & Migrations
│   │   ├── schemas/             # Pydantic Schemas & Data Contracts
│   │   ├── services/            # Audit & Evolution Analysis Services
│   │   ├── static/              # Enterprise SPA Frontend (index.html)
│   │   └── main.py              # FastAPI Application Entrypoint
│   └── requirements.txt         # Dependencies
├── rag/                         # Retrieval-Augmented Generation & IBM Granite Layer
│   ├── granite/                 # IBM Granite 7B Provider & Factory
│   └── retrieval/               # RAG Policy Context Retriever
├── tests/                       # Complete Pytest Test Suite
│   ├── test_decision_engine.py  # 26 Decision Engine Tests
│   └── test_policy_evolution.py # 10 Policy Evolution Novelty Tests
├── run_server.py                # Application Launcher Script
├── README.md                    # Platform Documentation
└── LICENSE                      # Apache 2.0 License
```

---

## 📜 License

AegisMesh AI is open-source software licensed under the [Apache License 2.0](LICENSE).
