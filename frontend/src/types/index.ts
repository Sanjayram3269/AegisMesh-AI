export type GovernanceDecision = 'APPROVE' | 'MODIFY' | 'ESCALATE' | 'REJECT';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface AgentExecution {
  agentId: string;
  action: string;
  context: string;
}

export interface RiskFactor {
  factor: string;
  severity: RiskLevel;
  description: string;
}

export interface PolicyEvidence {
  policyId: string;
  violation: boolean;
  reason: string;
}

export interface TransformationResult {
  modifiedContext: string;
  appliedTransformations: string[];
}

export interface ReviewResult {
  decision: GovernanceDecision;
  comments: string;
}

export interface GovernRequest {
  agentExecution: AgentExecution;
  dryRun?: boolean;
}

export interface GovernResponse {
  requestId: string;
  decision: GovernanceDecision;
  riskLevel: RiskLevel;
  riskFactors: RiskFactor[];
  policyEvaluations: PolicyEvidence[];
  transformation?: TransformationResult;
  review?: ReviewResult;
  timestamp: string;
}

export interface AuditRecord {
  requestId: string;
  timestamp: string;
  agentExecution: AgentExecution;
  decision: GovernanceDecision;
  riskLevel: RiskLevel;
}

export interface HealthResponse {
  status: string;
  version: string;
}
