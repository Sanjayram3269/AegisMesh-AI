"""Risk Agent — AegisMesh AI Governance Engine."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.schemas.governance import (
    RiskResult, RiskLevel, RiskFactor, AgentStatus,
    RiskAssessment, get_standard_risk_level
)
from agents.policy_engine import normalize_governance_input


def compute_canonical_risk(
    data_classification: str,
    target: str,
    authorization_status: str,
    role: str,
    action: str,
    identity=None
) -> tuple[int, int, int, RiskLevel, list[RiskFactor], list[str], dict[str, float]]:
    """
    Authoritative 3-Stage Risk Assessment Function:
    STAGE 1: INHERENT RISK (Raw action risk before controls/mitigations)
    STAGE 2: CONTROL & MITIGATION EVALUATION (Risk-reducing factors: auth, role, target trust, policy compliance)
    STAGE 3: EFFECTIVE RISK = max(0, min(99, Inherent Risk - Risk Reduction))
    """
    inp = normalize_governance_input(
        user_id="",
        role=role,
        action=action,
        target=target,
        data_classification=data_classification,
        authorization_status=authorization_status
    )
    
    act_lower = (action or '').lower()
    
    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 1: INHERENT RISK ASSESSMENT (0 - 100)
    # Risk of raw action, data sensitivity, & destination exposure before controls
    # ──────────────────────────────────────────────────────────────────────────
    is_prohibited_op = any(kw in act_lower for kw in [
        'disable authentication', 'delete access logs', 'remove access',
        'bypass', 'format disk', 'wipe', 'exfiltrate'
    ])
    
    if is_prohibited_op:
        action_scope = 95
        action_desc = "Prohibited security operation"
    elif inp.action_type == "DELETE":
        action_scope = 85
        action_desc = f"Destructive action scope ({inp.action_type})"
    elif inp.action_type in ["EXPORT", "TRANSFER"]:
        action_scope = 65
        action_desc = f"Data transfer scope ({inp.action_type})"
    elif inp.action_type in ["MODIFY", "UPDATE"]:
        action_scope = 45
        action_desc = f"Modification scope ({inp.action_type})"
    elif inp.action_type in ["DEPLOY", "CONFIGURE"]:
        action_scope = 40
        action_desc = f"System configuration deployment ({inp.action_type})"
    else:
        action_scope = 15
        action_desc = f"Read/query scope ({inp.action_type})"

    # Data Sensitivity Adjustment (0-30)
    if inp.data_classification == "RESTRICTED":
        data_sens_points = 25
    elif inp.data_classification == "CONFIDENTIAL":
        data_sens_points = 15
    elif inp.data_classification == "INTERNAL":
        data_sens_points = 5
    else:
        data_sens_points = 0

    # Destination Exposure Adjustment (0-20)
    if inp.target_environment == "PRODUCTION" or inp.target_trust == "LOW" or inp.is_external:
        dest_exposure_points = 20
    elif inp.target_environment in ["STAGING", "TEST"] or inp.target_trust == "MEDIUM":
        dest_exposure_points = 10
    else:
        dest_exposure_points = 0

    inherent_risk_score = min(99, max(10, action_scope + data_sens_points + dest_exposure_points))

    # Aggravating Risk Factors List
    risk_factors = [
        RiskFactor(factor='action_scope', score=float(action_scope), weight=0.40, description=action_desc),
        RiskFactor(factor='data_sensitivity', score=float(data_sens_points * 3.33), weight=0.30, description=f'Classification: {data_classification} (+{data_sens_points} pts)'),
        RiskFactor(factor='destination_exposure', score=float(dest_exposure_points * 5.0), weight=0.30, description=f'Destination: {target} (+{dest_exposure_points} pts)'),
    ]

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 2: CONTROL & MITIGATION EVALUATION (Risk-Reducing Factors)
    # ──────────────────────────────────────────────────────────────────────────
    mitigating_factors = []
    risk_reduction_pts = 0

    # Mitigation 1: Verified User Authorization (-15 pts)
    if inp.authorization_status == "VERIFIED":
        risk_reduction_pts += 15
        mitigating_factors.append("Verified user authorization status (-15 pts)")

    # Mitigation 2: Requester Clearance & Seniority (-15 pts / -5 pts)
    if inp.normalized_role in ["ENGINEER", "ADMIN", "MANAGER", "FINANCE_MANAGER"]:
        risk_reduction_pts += 15
        mitigating_factors.append(f"Senior/Lead role clearance ({role}) (-15 pts)")
    elif inp.normalized_role == "ANALYST":
        risk_reduction_pts += 5
        mitigating_factors.append(f"Analyst role clearance ({role}) (-5 pts)")

    # Mitigation 3: Approved / High Trust Target (-15 pts / -10 pts)
    if inp.target_trust == "HIGH" or "approved" in inp.raw_target.lower():
        risk_reduction_pts += 15
        mitigating_factors.append(f"Approved high-trust target endpoint ({target}) (-15 pts)")
    elif inp.target_trust == "MEDIUM" and not inp.is_external:
        risk_reduction_pts += 10
        mitigating_factors.append(f"Approved internal target endpoint ({target}) (-10 pts)")

    # Mitigation 4: Baseline Policy Grounding / Non-Prohibited Action (-15 pts)
    if not is_prohibited_op:
        risk_reduction_pts += 15
        mitigating_factors.append("Enterprise policy baseline compliance (-15 pts)")
    else:
        # Void mitigations for prohibited security operations
        risk_reduction_pts = 0
        mitigating_factors = ["Mitigations VOIDED: Action is a prohibited security operation."]

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 3: EFFECTIVE RISK SCORE CALCULATION & CLAMPING
    # Effective Risk = max(0, min(99, Inherent Risk - Risk Reduction))
    # ──────────────────────────────────────────────────────────────────────────
    if is_prohibited_op:
        effective_score = max(inherent_risk_score, 85)
        risk_reduction_pts = 0
    else:
        effective_score = max(0, min(99, inherent_risk_score - risk_reduction_pts))

    effective_level = get_standard_risk_level(effective_score)

    signals_dict = {
        'inherent_risk': float(inherent_risk_score),
        'risk_reduction': float(risk_reduction_pts),
        'effective_risk': float(effective_score),
        'action_scope': float(action_scope),
        'data_sensitivity': float(data_sens_points * 3.33),
        'destination_exposure': float(dest_exposure_points * 5.0)
    }

    return inherent_risk_score, effective_score, risk_reduction_pts, effective_level, risk_factors, mitigating_factors, signals_dict


async def run_risk(state):
    state.add_agent_execution('risk')
    
    inh_score, eff_score, red_pts, level, factors, mitigations, signals = compute_canonical_risk(
        data_classification=state.data_classification,
        target=state.target,
        authorization_status=state.authorization_status,
        role=state.role,
        action=state.action,
        identity=state.identity
    )

    state.risk = RiskResult(
        risk_score=eff_score,
        risk_level=level,
        inherent_risk_score=inh_score,
        risk_reduction=red_pts,
        effective_risk=eff_score,
        risk_factors=factors,
        mitigating_factors=mitigations,
        rationale=f"Inherent Risk: {inh_score} | Risk Reduction: -{red_pts} pts | Effective Risk: {eff_score}/100 ({level.value})."
    )
    
    state.complete_agent_execution('risk', AgentStatus.COMPLETED)
    return state
