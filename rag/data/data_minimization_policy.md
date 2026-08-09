# Data Minimization & Purpose Limitation Policy

**Policy ID:** POL-DM-005
**Version:** 1.1
**Effective Date:** 2026-02-10
**Responsible Department:** Data Privacy Office

## 1. Purpose
To ensure that the enterprise collects, processes, and transfers only the minimum amount of data necessary to achieve specific, legitimate business purposes, thereby reducing privacy risks and ensuring regulatory compliance.

## 2. Scope
Applies to all systems, human users, and AI agents involved in data querying, extraction, reporting, and transfer.

## 3. Purpose Specification & Use Limitation
**3.1 Specification:** The purpose for any data extraction or transfer must be explicitly documented and approved prior to the action.
**3.2 Limitation:** Data collected or extracted for one purpose must not be repurposed for another without a separate approval process.

## 4. Data Collection Minimization
**4.1 Minimum Fields:** Any export, transfer, or report must include only the minimum required data fields necessary to fulfill the stated purpose.
**4.2 PII Stripping:** PII fields MUST be removed or redacted from all datasets unless their inclusion is specifically required, justified, and explicitly approved for the task.

## 5. Prohibitions on Full Exports
**5.1 Full Database Exports:** Full database exports or unconstrained SELECT * queries on sensitive tables are strictly prohibited.
**5.2 Filtered Views:** Users and AI agents must utilize filtered, parameterized, or aggregated views to restrict the data volume and scope to the absolute minimum needed.

## 6. Aggregation Requirements
Whenever possible, data should be transferred or reported in an aggregated or statistical format rather than at the individual record level, especially when sharing insights with external partners.

## 7. Retention Limits
Data extracted for temporary processing or analysis must be securely deleted immediately upon completion of the task. Temporary data stores must have automated deletion policies enforcing a maximum retention period of 30 days.

## 8. Enforcement and Review
**8.1 Automated Checks:** AI governance agents must review queries and transfer requests to enforce minimization rules (e.g., rejecting requests that pull excessive columns or rows).
**8.2 Violations:** Failure to minimize data extraction will result in the cancellation of the transfer and a mandatory review by the Data Privacy Office.
