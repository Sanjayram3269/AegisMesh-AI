# AegisMesh AI — Multi-Agent Design

## Agent Philosophy
The multi-agent system in AegisMesh AI is designed around a strict single-responsibility principle. Each agent handles one specific domain of the governance evaluation, reducing hallucination risk and improving observability.

## Shared State Schema (GovernanceState)
All agents read from and write to a shared state object during a request lifecycle:
```typescript
interface GovernanceState {
  requestId: string;
  originalRequest: GovernanceRequest;
  intent: IntentAnalysis | null;
  evidence: RAGDocument[];
  complianceCheck: ComplianceResult | null;
  riskAssessment: RiskResult | null;
  explainability: string | null;
  transformation: TransformationPlan | null;
  finalDecision: 'APPROVE' | 'REJECT' | 'MODIFY' | 'ESCALATE' | null;
  iterations: number;
  errors: AgentError[];
}
```

## Agent Descriptions

### 1. Planner Agent
- **Purpose**: Initializes state and determines the necessary execution graph based on request complexity.
- **Inputs**: Raw GovernanceRequest.
- **Outputs**: Execution plan.
- **Example**: `{"plan": ["Intent", "RAG", "Compliance", "Risk", "Reviewer"]}`

### 2. Intent & Identity Agent
- **Purpose**: Classifies what the user is actually trying to do and verifies if their role generally allows this domain of action.
- **Inputs**: `request.action`, `request.user`.
- **Outputs**: Standardized intent category (e.g., `DATA_EXPORT`, `MODEL_TRAINING`).
- **Example**: "User intends to export bulk PII data to external storage."

### 3. Compliance Agent
- **Purpose**: Evaluates the action against retrieved policy documents.
- **Inputs**: Intent, RAG Evidence.
- **Outputs**: Pass/Fail flags for specific policies.
- **Example**: `{"policy_id": "POL-01", "status": "FAIL", "reason": "Unencrypted export"}`

### 4. Risk Agent
- **Purpose**: Calculates a quantitative risk score (0-100) based on data sensitivity and destination.
- **Inputs**: Request context, target data metadata.
- **Outputs**: Risk score and risk tier (Low/Med/High/Critical).
- **Example**: `{"score": 85, "tier": "High"}`

### 5. Explainability Agent
- **Purpose**: Translates complex compliance and risk findings into human-readable justifications.
- **Inputs**: Compliance output, Risk output.
- **Outputs**: Clear summary of why a decision is being made.
- **Example**: "Request flags high risk because it exports unmasked PII externally, violating POL-01."

### 6. Transformation Agent
- **Purpose**: If a request violates policy but can be salvaged (e.g., by anonymizing data), proposes a transformation.
- **Inputs**: Compliance failures.
- **Outputs**: Transformation directives (e.g., "Mask SSN field").
- **Example**: `{"transform": "mask", "fields": ["ssn", "phone"]}`

### 7. Reviewer Agent
- **Purpose**: Consolidates all agent outputs to form a final recommendation.
- **Inputs**: Full GovernanceState.
- **Outputs**: Recommended decision (APPROVE, REJECT, MODIFY, ESCALATE).
- **Example**: `{"recommendation": "ESCALATE", "confidence": 0.95}`

## Orchestration Flow & Decision Routing
1. Linear execution: Planner -> Intent -> RAG Retrieval.
2. Parallel execution: Compliance & Risk.
3. Review execution: Explainability -> Reviewer.
4. If Reviewer recommends MODIFY, state loops back through Transformation -> Compliance (Max iterations: 2).
5. Decision Router executes the final recommendation.

## Bounded Autonomy and Error Handling
- **Max Iterations**: The transformation loop is capped at 2 iterations to prevent infinite loops.
- **Error Handling**: If any agent fails or throws an exception, the state immediately transitions to the `Reviewer` with a system error flag, forcing an `ESCALATE` or `REJECT` decision (Fail Closed).
