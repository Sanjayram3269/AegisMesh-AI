# AegisMesh AI — Demo Scenarios

## Purpose of Demo Scenarios
These scenarios are designed to showcase the full capabilities of the AegisMesh AI governance pipeline, demonstrating how the multi-agent system handles various levels of risk and complexity.

## Scenarios

### 1. APPROVE: Anonymized Analytics Export
- **Risk Level**: Low
- **User Role**: Data Analyst
- **Action**: Export
- **Target**: Anonymized marketing metrics (Q3)
- **Expected Flow**:
  - Intent Agent: Identifies Data Export.
  - RAG: Retrieves "Internal Analytics Data Handling Policy".
  - Compliance Agent: Passes all checks (data is anonymized).
  - Risk Agent: Score 15 (Low).
  - Reviewer Agent: Consolidates and approves.
- **Expected Decision**: **APPROVE**

### 2. MODIFY: PII Data Export
- **Risk Level**: Medium
- **User Role**: Marketing Manager
- **Action**: Export
- **Target**: Raw customer contact list
- **Expected Flow**:
  - Intent Agent: Identifies PII Export.
  - RAG: Retrieves "PII Handling Policy".
  - Compliance Agent: Flags violation (Raw PII export forbidden).
  - Transformation Agent: Proposes applying data masking to email and phone fields.
  - Loop back to Compliance: Passes with masked data.
  - Reviewer Agent: Recommends modification.
- **Expected Decision**: **MODIFY** (System executes export with dynamic masking applied).

### 3. ESCALATE: External Vendor Transfer
- **Risk Level**: High
- **User Role**: Sales Engineer
- **Action**: API Integration Transfer
- **Target**: Client financial history
- **Expected Flow**:
  - Intent Agent: Identifies External Data Transfer.
  - RAG: Retrieves "External Vendor Data Sharing Policy".
  - Compliance Agent: Identifies strict NDA and approval requirements for financial data.
  - Risk Agent: Score 85 (High).
  - Reviewer Agent: Cannot autonomously approve high-risk external transfers.
- **Expected Decision**: **ESCALATE** (Requires human review in frontend UI).

### 4. REJECT: Unauthorized Public Endpoint
- **Risk Level**: Critical
- **User Role**: Junior Developer
- **Action**: Deploy Model
- **Target**: Publicly accessible S3 bucket
- **Expected Flow**:
  - Intent Agent: Identifies Public Deployment.
  - RAG: Retrieves "Cloud Storage Security Policy".
  - Compliance Agent: Critical violation of "Zero-Trust Public Access Policy".
  - Risk Agent: Score 99 (Critical).
  - Reviewer Agent: Policy strictly forbids this action without exception.
- **Expected Decision**: **REJECT** (Request blocked immediately).

## Demo Mode Explanation
When running with `DEMO_MODE=true`, the system bypasses live LLM calls for these specific predefined request payloads and uses the `MockProvider` to return deterministic agent traces. This ensures reliable presentations.

## How to Run Demos
Use the provided Postman collection or the frontend "Scenario Testing" panel to trigger these exact workflows.
