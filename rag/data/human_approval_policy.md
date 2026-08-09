# Human Approval & Escalation Policy

**Policy ID:** POL-HA-006
**Version:** 1.0
**Effective Date:** 2026-05-15
**Responsible Department:** Risk Management & Security Operations

## 1. Purpose
This policy outlines the conditions under which human review and approval are required for actions initiated within the enterprise, particularly those proposed by autonomous AI agents, and defines the escalation paths for complex decisions.

## 2. Scope
This policy applies to all automated workflows, AI-driven actions, and human-initiated requests that meet defined risk thresholds.

## 3. When Human Approval is Required
Human approval is non-negotiable for actions meeting any of the following criteria:
- **Risk Score:** Any proposed action or workflow evaluated with a risk score of 70 or greater (>= 70) requires mandatory human review.
- **System Alterations:** Modifications to production firewall rules, IAM roles, or core security policies.
- **High-Risk Data Movement:** External transfer of Confidential or Restricted data.
- **Uncertainty:** Any situation where a governance AI agent encounters conflicting policies, ambiguous context, or calculates an uncertainty score above acceptable thresholds.

## 4. Approval Authority Levels
Approval must be obtained from an authority level commensurate with the risk:
- **Manager Level:** Internal transfers of sensitive data, minor configuration changes.
- **Director Level:** Risk scores between 70 and 85, exceptions to standard access controls.
- **VP Level:** Confidential data transfers to external parties, significant architectural changes.
- **CISO Level:** New external vendor transfers, connections to unapproved endpoints, risk scores > 85.

## 5. Escalation Triggers
An escalation must be triggered if:
- A required approver is unavailable for more than 4 hours (SLA breach).
- The AI agent cannot confidently determine the appropriate action based on existing policies.
- A proposed action violates a primary security policy but is deemed critically necessary for business continuity.

## 6. Escalation Paths
1. **Tier 1:** Security Operations Center (SOC) Analyst / On-call Engineer.
2. **Tier 2:** Security Engineering Manager / Risk Management Lead.
3. **Tier 3:** Director of Information Security / CISO.

## 7. Service Level Agreements (SLA) for Approvals
- Standard Requests: 24 business hours.
- High-Risk Requests (Score >= 70): 4 hours.
- Emergency Escalations: 30 minutes.

## 8. Emergency Procedures
In critical emergencies where immediate action is required to prevent catastrophic loss and approvers are unavailable, authorized emergency personnel may use break-glass procedures to bypass standard approvals. All such actions are subject to rigorous post-incident review.
