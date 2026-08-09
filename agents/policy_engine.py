"""
Deterministic Policy Engine & Centralized Decision Resolution for AegisMesh AI.

Evaluates explicit policy rules deterministically, normalizes intake attributes,
captures structured policy evaluation traces, and resolves final governance decisions
based on strict severity precedence:
PRIORITY 1: Explicit REJECT policy rules
PRIORITY 2: Explicit ESCALATE policy rules
PRIORITY 3: Explicit MODIFY policy rules
PRIORITY 4: Explicit APPROVE policy rules
PRIORITY 5: Fallback risk score mapping (0-24 -> APPROVE, 25-49 -> MODIFY, 50-74 -> ESCALATE, 75-100 -> REJECT)
"""

from typing import Any, NamedTuple, Optional
from app.schemas.governance import GovernanceDecision


class NormalizedInput(NamedTuple):
    user_id: str
    raw_role: str
    normalized_role: str        # 'ENGINEER', 'MANAGER', 'ADMIN', 'JUNIOR', 'FINANCE_MANAGER', 'ANALYST', 'GENERAL_USER'
    raw_action: str
    action_type: str            # 'DEPLOY', 'MODIFY', 'DELETE', 'CONFIGURE', 'EXPORT', 'TRANSFER', 'READ', 'GENERAL'
    raw_target: str
    target_environment: str     # 'PRODUCTION', 'STAGING', 'TEST', 'QA', 'INTERNAL', 'GENERAL'
    target_trust: str           # 'HIGH', 'MEDIUM', 'LOW'
    is_external: bool
    raw_classification: str
    data_classification: str    # 'PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED'
    raw_authorization: str
    authorization_status: str   # 'VERIFIED', 'PENDING', 'UNVERIFIED'


def normalize_governance_input(
    user_id: str,
    role: str,
    action: str,
    target: str,
    data_classification: str,
    authorization_status: str,
) -> NormalizedInput:
    """Normalize raw request parameters into standardized governance tokens."""
    # 1. Role Normalization
    r_lower = (role or "").lower()
    if any(k in r_lower for k in ["cfo", "finance manager", "controller", "financial manager"]):
        norm_role = "FINANCE_MANAGER"
    elif any(k in r_lower for k in ["ciso", "security manager"]):
        norm_role = "MANAGER"
    elif any(k in r_lower for k in ["intern", "junior engineer", "contractor", "junior analyst", "junior"]):
        norm_role = "JUNIOR"
    elif any(k in r_lower for k in ["senior engineer", "devops engineer", "software engineer", "principal engineer", "lead engineer", "engineer"]):
        norm_role = "ENGINEER"
    elif any(k in r_lower for k in ["system administrator", "sysadmin", "admin"]):
        norm_role = "ADMIN"
    elif any(k in r_lower for k in ["financial analyst", "data analyst", "senior analyst", "analyst", "marketing analyst"]):
        norm_role = "ANALYST"
    elif "manager" in r_lower:
        norm_role = "MANAGER"
    else:
        norm_role = "GENERAL_USER"

    # 2. Action Type Normalization
    a_lower = (action or "").lower()
    if any(k in a_lower for k in ["deploy", "deployment", "release", "approved configuration update"]):
        act_type = "DEPLOY"
    elif any(k in a_lower for k in ["modify", "update", "revise", "edit", "change"]):
        act_type = "MODIFY"
    elif any(k in a_lower for k in ["delete", "drop", "purge", "remove", "truncate"]):
        act_type = "DELETE"
    elif any(k in a_lower for k in ["configure", "config", "firewall", "setting"]):
        act_type = "CONFIGURE"
    elif any(k in a_lower for k in ["export", "dump", "extract"]):
        act_type = "EXPORT"
    elif any(k in a_lower for k in ["send", "transfer", "share"]):
        act_type = "TRANSFER"
    else:
        act_type = "READ"

    # 3. Target Environment & Trust Normalization
    t_lower = (target or "").lower()
    if any(k in t_lower for k in ["production", "prod", "live-payment", "production-api-gateway", "production-database"]):
        target_env = "PRODUCTION"
    elif any(k in t_lower for k in ["staging", "stage"]):
        target_env = "STAGING"
    elif any(k in t_lower for k in ["test", "testing"]):
        target_env = "TEST"
    elif any(k in t_lower for k in ["qa"]):
        target_env = "QA"
    elif "approved-finance-analytics" in t_lower or "approved-internal" in t_lower:
        target_env = "INTERNAL"
    else:
        target_env = "GENERAL"

    if "approved-finance-analytics" in t_lower or "approved-internal" in t_lower or target_env == "PRODUCTION":
        trust = "HIGH"
        external = False
    elif "approved-analytics" in t_lower or "approved-vendor" in t_lower:
        trust = "MEDIUM"
        external = True
    elif "new-business-analytics" in t_lower or "new-external" in t_lower or "vendor" in t_lower:
        trust = "MEDIUM"
        external = True
    elif "public" in t_lower or "unauthorized" in t_lower or "untrusted" in t_lower:
        trust = "LOW"
        external = True
    else:
        trust = "MEDIUM"
        external = "external" in t_lower or "vendor" in t_lower or "public" in t_lower

    # 4. Data Classification Normalization
    c_lower = (data_classification or "Internal").lower()
    if "restricted" in c_lower:
        norm_cls = "RESTRICTED"
    elif "confidential" in c_lower or "pii" in c_lower or "sensitive" in c_lower:
        norm_cls = "CONFIDENTIAL"
    elif "public" in c_lower:
        norm_cls = "PUBLIC"
    else:
        norm_cls = "INTERNAL"

    # 5. Authorization Status Normalization
    auth_lower = (authorization_status or "Verified").lower()
    if "verified" in auth_lower and "not" not in auth_lower and "unverified" not in auth_lower:
        norm_auth = "VERIFIED"
    elif "pending" in auth_lower:
        norm_auth = "PENDING"
    else:
        norm_auth = "UNVERIFIED"

    return NormalizedInput(
        user_id=user_id,
        raw_role=role,
        normalized_role=norm_role,
        raw_action=action,
        action_type=act_type,
        raw_target=target,
        target_environment=target_env,
        target_trust=trust,
        is_external=external,
        raw_classification=data_classification,
        data_classification=norm_cls,
        raw_authorization=authorization_status,
        authorization_status=norm_auth
    )


class MatchedPolicyTrace(NamedTuple):
    policy_id: str
    policy_name: str
    matched: bool
    matched_conditions: list[str]
    failed_conditions: list[str]
    decision: GovernanceDecision
    priority: str
    rule_description: str


def evaluate_explicit_policies(
    inp: NormalizedInput,
    active_policies: Optional[list[dict[str, Any]]] = None
) -> list[MatchedPolicyTrace]:
    """
    Deterministically evaluates all active policies against normalized intake attributes.
    Returns a complete list of MatchedPolicyTrace records (both matched and non-matched).
    Dynamically respects active database overrides for policy decision actions, priorities, and definitions.
    """
    traces: list[MatchedPolicyTrace] = []
    db_map = {p.get("policy_id"): p for p in active_policies} if active_policies else {}

    def get_db_decision(pid: str, default_dec: GovernanceDecision) -> GovernanceDecision:
        if pid in db_map:
            act_str = db_map[pid].get("decision_action", "").upper()
            try:
                return GovernanceDecision(act_str)
            except ValueError:
                return default_dec
        return default_dec

    def get_db_priority(pid: str, default_prio: str) -> str:
        if pid in db_map:
            return db_map[pid].get("priority", "").upper() or default_prio
        return default_prio

    # ──────────────────────────────────────────────────────────────────────────
    # 1. POL-ACC-006: Production System Access Control Policy
    # ──────────────────────────────────────────────────────────────────────────
    if not active_policies or "POL-ACC-006" in db_map:
        conds_pass = []
        conds_fail = []
        
        if inp.target_environment == "PRODUCTION":
            conds_pass.append("✓ target.environment = PRODUCTION")
        else:
            conds_fail.append(f"✗ target.environment != PRODUCTION (is '{inp.target_environment}')")

        if inp.action_type in ["DELETE", "MODIFY", "DEPLOY", "CONFIGURE"]:
            conds_pass.append(f"✓ action.type = {inp.action_type}")
        else:
            conds_fail.append(f"✗ action.type '{inp.action_type}' not in [DELETE, MODIFY, DEPLOY, CONFIGURE]")

        if inp.authorization_status == "VERIFIED":
            conds_pass.append("✓ authorization.status = VERIFIED")
        else:
            conds_fail.append(f"✗ authorization.status != VERIFIED (is '{inp.authorization_status}')")

        if inp.normalized_role in ["ADMIN", "ENGINEER", "MANAGER"]:
            conds_pass.append(f"✓ requester.role = {inp.normalized_role}")
        else:
            conds_fail.append(f"✗ requester.role '{inp.normalized_role}' not in [ADMIN, ENGINEER, MANAGER]")

        # Check Rule 4 (REJECT): Production + Intern/Junior + [DELETE, MODIFY, DEPLOY, CONFIGURE]
        if inp.target_environment == "PRODUCTION" and inp.normalized_role in ["JUNIOR", "INTERN", "CONTRACTOR"] and inp.action_type in ["DELETE", "MODIFY", "DEPLOY", "CONFIGURE"]:
            traces.append(MatchedPolicyTrace(
                policy_id="POL-ACC-006",
                policy_name="Production System Access Control Policy",
                matched=True,
                matched_conditions=[
                    "✓ target.environment = PRODUCTION",
                    f"✓ action.type = {inp.action_type}",
                    f"✓ requester.role = {inp.normalized_role} (Restricted Role)"
                ],
                failed_conditions=[],
                decision=get_db_decision("POL-ACC-006", GovernanceDecision.REJECT),
                priority=get_db_priority("POL-ACC-006", "HIGH"),
                rule_description="Rule 4: Junior/Intern/Contractor roles are restricted from modifying/deploying/deleting production systems."
            ))

        # Check Rule 3 (ESCALATE): Production + Unverified Authorization + [DELETE, MODIFY, DEPLOY, CONFIGURE]
        elif inp.target_environment == "PRODUCTION" and inp.action_type in ["DELETE", "MODIFY", "DEPLOY", "CONFIGURE"] and inp.authorization_status != "VERIFIED":
            traces.append(MatchedPolicyTrace(
                policy_id="POL-ACC-006",
                policy_name="Production System Access Control Policy",
                matched=True,
                matched_conditions=[
                    "✓ target.environment = PRODUCTION",
                    f"✓ action.type = {inp.action_type}",
                    f"✓ authorization.status = {inp.authorization_status} (Unverified)"
                ],
                failed_conditions=[],
                decision=get_db_decision("POL-ACC-006", GovernanceDecision.ESCALATE),
                priority=get_db_priority("POL-ACC-006", "HIGH"),
                rule_description="Rule 3: Unverified authorization on Production system deployment/modification requires Human Review."
            ))

        # Check Rule 2 (MODIFY): Production + Verified + Engineer/Admin/Manager + MODIFY
        elif inp.target_environment == "PRODUCTION" and inp.authorization_status == "VERIFIED" and inp.normalized_role in ["ADMIN", "ENGINEER", "MANAGER"] and inp.action_type == "MODIFY":
            traces.append(MatchedPolicyTrace(
                policy_id="POL-ACC-006",
                policy_name="Production System Access Control Policy",
                matched=True,
                matched_conditions=conds_pass,
                failed_conditions=[],
                decision=get_db_decision("POL-ACC-006", GovernanceDecision.MODIFY),
                priority=get_db_priority("POL-ACC-006", "HIGH"),
                rule_description="Rule 2: Production modification action requires validation, identifier stripping, and audit logging."
            ))

        # Check Rule 1 (APPROVE): Production + Verified + Engineer/Admin/Manager + [DEPLOY, CONFIGURE]
        elif inp.target_environment == "PRODUCTION" and inp.authorization_status == "VERIFIED" and inp.normalized_role in ["ADMIN", "ENGINEER", "MANAGER"] and inp.action_type in ["DEPLOY", "CONFIGURE"]:
            traces.append(MatchedPolicyTrace(
                policy_id="POL-ACC-006",
                policy_name="Production System Access Control Policy",
                matched=True,
                matched_conditions=conds_pass,
                failed_conditions=[],
                decision=get_db_decision("POL-ACC-006", GovernanceDecision.APPROVE),
                priority=get_db_priority("POL-ACC-006", "HIGH"),
                rule_description="Rule 1: Verified Engineer/Admin/Manager authorized for Production configuration deployment."
            ))
        else:
            if inp.target_environment == "PRODUCTION":
                traces.append(MatchedPolicyTrace(
                    policy_id="POL-ACC-006",
                    policy_name="Production System Access Control Policy",
                    matched=False,
                    matched_conditions=conds_pass,
                    failed_conditions=conds_fail,
                    decision=get_db_decision("POL-ACC-006", GovernanceDecision.APPROVE),
                    priority=get_db_priority("POL-ACC-006", "HIGH"),
                    rule_description="Evaluated against Production Access policy rules."
                ))

    # ──────────────────────────────────────────────────────────────────────────
    # 2. POL-FIN-006: Financial Data Access and Transfer Policy
    # ──────────────────────────────────────────────────────────────────────────
    if not active_policies or "POL-FIN-006" in db_map:
        is_finance_domain = any(kw in (inp.raw_action + " " + inp.raw_classification + " " + inp.raw_role).lower() for kw in ["financial", "finance", "accounting", "bank", "tax", "report"])
        
        if inp.data_classification in ["RESTRICTED", "CONFIDENTIAL"] and is_finance_domain:
            # Rule 4 (REJECT)
            if inp.data_classification == "RESTRICTED" and (
                inp.authorization_status == "UNVERIFIED" or inp.target_trust == "LOW" or "public" in inp.raw_target.lower() or "unauthorized" in inp.raw_target.lower()
            ):
                traces.append(MatchedPolicyTrace(
                    policy_id="POL-FIN-006",
                    policy_name="Financial Data Access and Transfer Policy",
                    matched=True,
                    matched_conditions=["✓ Restricted financial data classification", f"✓ Authorization/Target unverified: {inp.raw_authorization}"],
                    failed_conditions=[],
                    decision=get_db_decision("POL-FIN-006", GovernanceDecision.REJECT),
                    priority=get_db_priority("POL-FIN-006", "HIGH"),
                    rule_description="Rule 4: Restricted financial data access to external/unverified targets is strictly blocked."
                ))

            # Rule 3 (ESCALATE)
            elif inp.authorization_status == "PENDING" or inp.normalized_role in ["ANALYST", "JUNIOR"] or inp.target_trust == "MEDIUM":
                traces.append(MatchedPolicyTrace(
                    policy_id="POL-FIN-006",
                    policy_name="Financial Data Access and Transfer Policy",
                    matched=True,
                    matched_conditions=["✓ Confidential/Restricted financial classification", f"✓ Role/Auth status: {inp.normalized_role}/{inp.authorization_status}"],
                    failed_conditions=[],
                    decision=get_db_decision("POL-FIN-006", GovernanceDecision.ESCALATE),
                    priority=get_db_priority("POL-FIN-006", "MEDIUM"),
                    rule_description="Rule 3: Financial data access by Analyst or Pending authorization requires Human Review."
                ))

            # Rule 2 (MODIFY)
            elif inp.action_type in ["MODIFY", "UPDATE"] and inp.authorization_status == "VERIFIED" and inp.target_trust == "HIGH":
                traces.append(MatchedPolicyTrace(
                    policy_id="POL-FIN-006",
                    policy_name="Financial Data Access and Transfer Policy",
                    matched=True,
                    matched_conditions=["✓ Restricted/Confidential report update action", "✓ Verified clearance & High Trust target endpoint"],
                    failed_conditions=[],
                    decision=get_db_decision("POL-FIN-006", GovernanceDecision.MODIFY),
                    priority=get_db_priority("POL-FIN-006", "MEDIUM"),
                    rule_description="Rule 2: Financial report update requires identifier stripping and audit logging."
                ))

            # Rule 1 (APPROVE)
            elif inp.data_classification == "RESTRICTED" and inp.authorization_status == "VERIFIED" and inp.normalized_role == "FINANCE_MANAGER" and inp.target_trust == "HIGH":
                traces.append(MatchedPolicyTrace(
                    policy_id="POL-FIN-006",
                    policy_name="Financial Data Access and Transfer Policy",
                    matched=True,
                    matched_conditions=["✓ Restricted financial classification", "✓ Verified Finance Manager role clearance", "✓ High Trust target endpoint"],
                    failed_conditions=[],
                    decision=get_db_decision("POL-FIN-006", GovernanceDecision.APPROVE),
                    priority=get_db_priority("POL-FIN-006", "HIGH"),
                    rule_description="Rule 1: Finance Manager authorized for Restricted internal report generation on High Trust target."
                ))

    # ──────────────────────────────────────────────────────────────────────────
    # 3. POL-HUM-001: Human Approval Policy
    # ──────────────────────────────────────────────────────────────────────────
    if not active_policies or "POL-HUM-001" in db_map:
        if inp.authorization_status == "PENDING" and inp.data_classification in ["CONFIDENTIAL", "RESTRICTED"]:
            traces.append(MatchedPolicyTrace(
                policy_id="POL-HUM-001",
                policy_name="Human Approval Policy",
                matched=True,
                matched_conditions=["✓ Authorization status is Pending", f"✓ Data classification: {inp.raw_classification}"],
                failed_conditions=[],
                decision=get_db_decision("POL-HUM-001", GovernanceDecision.ESCALATE),
                priority=get_db_priority("POL-HUM-001", "HIGH"),
                rule_description="Pending authorization on Confidential/Restricted data requires explicit Human Approval."
            ))

    # ──────────────────────────────────────────────────────────────────────────
    # 4. POL-TRN-002: Data Transfer Policy
    # ──────────────────────────────────────────────────────────────────────────
    if not active_policies or "POL-TRN-002" in db_map:
        if inp.data_classification in ["RESTRICTED", "CONFIDENTIAL"] and (inp.target_trust == "LOW" or "public" in inp.raw_target.lower() or "unauthorized" in inp.raw_target.lower()):
            traces.append(MatchedPolicyTrace(
                policy_id="POL-TRN-002",
                policy_name="Data Transfer Policy",
                matched=True,
                matched_conditions=["✓ Confidential/Restricted data classification", "✓ Unauthorized public target endpoint"],
                failed_conditions=[],
                decision=get_db_decision("POL-TRN-002", GovernanceDecision.REJECT),
                priority=get_db_priority("POL-TRN-002", "HIGH"),
                rule_description="Prohibits exporting Confidential or Restricted data to unauthorized public endpoints."
            ))

    # ──────────────────────────────────────────────────────────────────────────
    # 5. POL-PII-003: PII Protection Policy
    # ──────────────────────────────────────────────────────────────────────────
    if not active_policies or "POL-PII-003" in db_map:
        act_cls = (inp.raw_action + " " + inp.raw_classification).lower()
        if any(k in act_cls for k in ["customer email", "customer phone", "pii", "email", "phone", "records"]) and not ("anonymized" in act_cls or "stripped" in act_cls) and (inp.is_external or inp.data_classification in ["CONFIDENTIAL", "RESTRICTED"]):
            traces.append(MatchedPolicyTrace(
                policy_id="POL-PII-003",
                policy_name="PII Protection Policy",
                matched=True,
                matched_conditions=["✓ Raw un-anonymized PII fields present in action or data classification", f"✓ Target destination: {inp.raw_target}"],
                failed_conditions=[],
                decision=get_db_decision("POL-PII-003", GovernanceDecision.MODIFY),
                priority=get_db_priority("POL-PII-003", "MEDIUM"),
                rule_description="Mandates anonymizing customer PII fields before transfer."
            ))

    # ──────────────────────────────────────────────────────────────────────────
    # 6. Dynamic Active Database Policies (Custom & Overriding)
    # ──────────────────────────────────────────────────────────────────────────
    if active_policies:
        for db_pol in active_policies:
            pid = db_pol.get("policy_id", "")
            if pid in ["POL-ACC-006", "POL-FIN-006", "POL-HUM-001", "POL-TRN-002", "POL-PII-003"]:
                continue
            
            p_action_str = db_pol.get("decision_action", "").upper()
            try:
                dec = GovernanceDecision(p_action_str)
            except ValueError:
                dec = GovernanceDecision.MODIFY

            prio = db_pol.get("priority", "HIGH")
            pname = db_pol.get("name", pid)
            rule_def = (db_pol.get("rule_definition") or "").lower()
            desc = db_pol.get("description") or f"Dynamic policy rule {pid}"

            matched = False
            reasons = []

            # General Keyword & Condition Matching against intake attributes
            if "minimization" in rule_def or pid == "POL-MIN-004":
                act_l = inp.raw_action.lower()
                if any(kw in act_l for kw in ["export", "dump", "database", "full"]) and not any(kw in act_l for kw in ["anonymized", "aggregated", "filtered"]):
                    matched = True
                    reasons.append("✓ Matches data minimization requirement for un-aggregated bulk export")

            elif "retention" in rule_def or pid == "POL-RET-007":
                if inp.action_type in ["DELETE", "PURGE"] and inp.data_classification in ["CONFIDENTIAL", "RESTRICTED"]:
                    matched = True
                    reasons.append(f"✓ Matches deletion retention rule for {inp.data_classification} data")

            elif "strictly blocked" in rule_def or pid == "POL-STRICT-REJECT":
                if inp.is_external or inp.target_trust == "LOW":
                    matched = True
                    reasons.append("✓ External/Low-trust endpoint transfer strictly blocked")

            elif "unverified" in rule_def and inp.authorization_status != "VERIFIED":
                matched = True
                reasons.append(f"✓ Unverified authorization status: {inp.authorization_status}")

            elif any(kw in rule_def for kw in [inp.raw_action.lower(), inp.data_classification.lower(), inp.target_environment.lower()]):
                matched = True
                reasons.append(f"✓ Matched intake keywords in rule definition for policy {pid}")

            if matched:
                traces.append(MatchedPolicyTrace(
                    policy_id=pid,
                    policy_name=pname,
                    matched=True,
                    matched_conditions=reasons,
                    failed_conditions=[],
                    decision=dec,
                    priority=prio,
                    rule_description=desc
                ))

    return traces


def resolve_fallback_decision(risk_score: int) -> GovernanceDecision:
    """
    Deterministic risk-to-decision mapping for fallback decisions (Issue 1 & 6):
    0-24   -> APPROVE
    25-49  -> MODIFY
    50-74  -> ESCALATE
    75-100 -> REJECT
    """
    if risk_score <= 24:
        return GovernanceDecision.APPROVE
    elif risk_score <= 49:
        return GovernanceDecision.MODIFY
    elif risk_score <= 74:
        return GovernanceDecision.ESCALATE
    else:
        return GovernanceDecision.REJECT


def resolve_final_decision(
    policy_traces: list[MatchedPolicyTrace],
    risk_score: int
) -> tuple[GovernanceDecision, str, GovernanceDecision, str]:
    """
    Centralized decision precedence resolution (Issue 2):
    PRIORITY 1: Explicit REJECT policy rules
    PRIORITY 2: Explicit ESCALATE policy rules
    PRIORITY 3: Explicit MODIFY policy rules
    PRIORITY 4: Explicit APPROVE policy rules
    PRIORITY 5: Fallback risk score mapping (0-24 -> APPROVE, 25-49 -> MODIFY, 50-74 -> ESCALATE, 75-100 -> REJECT)

    Returns:
    (winning_decision, decision_source, risk_derived_decision, summary_rationale)
    """
    risk_derived = resolve_fallback_decision(risk_score)
    active_matches = [m for m in policy_traces if m.matched]

    if not active_matches:
        source = "fallback_risk_engine"
        summary = f"No explicit policy decision matched. Final decision derived from risk score ({risk_score}/100 -> {risk_derived.value})."
        return risk_derived, source, risk_derived, summary

    PRECEDENCE_WEIGHTS = {
        GovernanceDecision.REJECT: 4,
        GovernanceDecision.ESCALATE: 3,
        GovernanceDecision.MODIFY: 2,
        GovernanceDecision.APPROVE: 1
    }

    winning_trace = max(active_matches, key=lambda m: PRECEDENCE_WEIGHTS.get(m.decision, 0))
    winning_decision = winning_trace.decision

    unique_decisions = {m.decision for m in active_matches}
    source = "conflict_resolution" if len(unique_decisions) > 1 else "explicit_policy"

    if winning_decision != risk_derived:
        summary = (
            f"Risk Score: {risk_score} (Risk-based Decision: {risk_derived.value}). "
            f"Policy Override: {winning_trace.policy_id} ({winning_trace.policy_name}) requires {winning_decision.value}. "
            f"Final Decision: {winning_decision.value}."
        )
    else:
        summary = (
            f"Matched Policy: {winning_trace.policy_name} ({winning_trace.policy_id}) -> "
            f"{winning_trace.rule_description} Decision: {winning_decision.value}."
        )

    return winning_decision, source, risk_derived, summary
