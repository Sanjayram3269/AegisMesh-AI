# Data Transfer & Export Policy

**Policy ID:** POL-DT-002
**Version:** 2.0
**Effective Date:** 2026-03-01
**Responsible Department:** Information Security & Compliance

## 1. Purpose
This policy dictates the rules and procedures governing the movement, export, and transfer of enterprise data across internal boundaries and to external entities.

## 2. Scope
This policy covers all data transfers initiated by human operators, automated scripts, and AI agents.

## 3. Data Classification
Data is classified into four tiers, which dictate transfer restrictions:
- **Public:** Data approved for external release (e.g., marketing materials).
- **Internal:** Data for internal use only; harm from disclosure is minimal.
- **Confidential:** Sensitive business data (e.g., financial reports, source code).
- **Restricted:** Highly sensitive data (e.g., PII, PHI, trade secrets).

## 4. Internal vs. External Transfers
**4.1 Internal Transfers:** Movement of data between approved enterprise systems within the corporate network boundary.
**4.2 External Transfers:** Movement of data outside the corporate network boundary to third parties, public cloud endpoints, or unmanaged devices.

## 5. Approved Endpoints
**5.1 Whitelist:** All external data transfers must be directed only to approved and whitelisted endpoints/domains.
**5.2 Prohibited Endpoints:** New, unrecognized, or unapproved external endpoints are strictly prohibited without explicit authorization from the security team. AI agents must block such requests automatically.

## 6. Authorization & Approval Workflows
**6.1 Public/Internal Data:** Internal transfers of Public or Internal data require standard role-based access. External transfers of Internal data require manager approval.
**6.2 Confidential+ Data:** External transfers of Confidential or Restricted data require senior management approval (Director level or higher).
**6.3 Large Volumes:** Any export exceeding 10,000 records or 5GB requires architectural review, regardless of classification.

## 7. Prohibited Transfers
The following actions are explicitly prohibited:
- Exporting Restricted data to external parties without a legal contract and CISO exception.
- Transferring data to personal email addresses or unauthorized cloud storage services (e.g., personal Dropbox, Google Drive).

## 8. Audit Requirements
**8.1 Transfer Logs:** All data transfers (internal and external) must be audited. Logs must capture the initiator (User ID or Agent ID), timestamp, data classification, source, destination, and transfer volume.
**8.2 Routine Reviews:** Transfer logs are subject to automated behavioral analysis and monthly manual reviews by the Compliance team.
