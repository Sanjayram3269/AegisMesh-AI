"""AegisMesh Orchestrator — Centralized Decision Resolution & Agentic Control Plane."""
import sys, os, logging, uuid
from datetime import datetime, timezone

# Ensure backend & root are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.schemas.governance import (
    GovernResponse, GovernanceDecision, RiskLevel, AgentStatus,
    AuditRecord, AgentExecution, RiskAssessment, TransformationDetail,
    ExecutionStageItem, get_standard_risk_level
)

from agents.planner import run_planner
from agents.intent import run_intent
from agents.identity import run_identity
from agents.compliance import run_compliance
from agents.risk import run_risk, compute_canonical_risk
from agents.explainability import run_explainability
from agents.reviewer import run_reviewer
from agents.transformation import run_transformation
from agents.policy_engine import (
    normalize_governance_input, evaluate_explicit_policies,
    resolve_final_decision, resolve_fallback_decision, MatchedPolicyTrace
)

try:
    from agents.state import GovernanceState
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from state import GovernanceState

try:
    from rag.retrieval.policy_retriever import retrieve_policy_context
except ImportError:
    async def retrieve_policy_context(action, context=None):
        return []

try:
    from app.services.audit_service import AuditService
except ImportError:
    class AuditService:
        _records = {}
        def save_record(self, record): self._records[record.request_id] = record

try:
    from app.database.db import SessionLocal
    from app.database.models import DBPolicy
except ImportError:
    SessionLocal = None
    DBPolicy = None

logger = logging.getLogger('aegismesh.orchestrator')
audit_service = AuditService()

def calculate_dynamic_confidence(state: GovernanceState) -> float:
    """
    Calculate deterministic dynamic confidence score (0.0 - 1.0) based on all pipeline agent outputs and evidence.
    """
    from app.schemas.governance import ComplianceStatus

    signals = []
    weights = []

    # 1. Intent Agent Confidence
    if state.intent and getattr(state.intent, 'confidence', 0) > 0:
        signals.append(min(max(float(state.intent.confidence), 0.0), 1.0))
        weights.append(0.20)

    # 2. Identity & Authorization Certainty
    if state.identity:
        id_conf = 0.98 if getattr(state.identity, 'authorized', True) else 0.92
        signals.append(id_conf)
        weights.append(0.15)

    # 3. Policy Evidence (RAG) Relevance Score
    if state.policy_evidence:
        rel_scores = [ev.relevance_score for ev in state.policy_evidence if getattr(ev, 'relevance_score', 0) > 0]
        avg_rel = (sum(rel_scores) / len(rel_scores)) if rel_scores else 0.88
        signals.append(min(max(float(avg_rel), 0.0), 1.0))
        weights.append(0.25)
    else:
        signals.append(0.60)
        weights.append(0.15)

    # 4. Compliance Agent Assessment
    if state.compliance:
        if state.compliance.status in [ComplianceStatus.COMPLIANT, ComplianceStatus.NON_COMPLIANT]:
            signals.append(0.95)
        else:
            signals.append(0.60)
        weights.append(0.20)

    # 5. LLM Structured Response Confidence (Granite)
    llm_res = state.metadata.get('llm_result', {})
    if isinstance(llm_res, dict):
        raw_llm_conf = llm_res.get('confidence')
        if isinstance(raw_llm_conf, (int, float)):
            if raw_llm_conf > 1.0 and raw_llm_conf <= 100.0:
                raw_llm_conf = raw_llm_conf / 100.0
            if 0.0 <= raw_llm_conf <= 1.0:
                signals.append(float(raw_llm_conf))
                weights.append(0.20)

    # Calculate weighted base
    if signals and sum(weights) > 0:
        total_w = sum(weights)
        base_confidence = sum(s * w for s, w in zip(signals, weights)) / total_w
    else:
        base_confidence = 0.88

    # Penalties & Deductions
    penalty = 0.0

    if state.review:
        if not getattr(state.review, 'evidence_sufficient', True):
            penalty += 0.10
        if not getattr(state.review, 'reasoning_consistent', True):
            penalty += 0.10
        if getattr(state.review, 'requires_human_review', False):
            penalty += 0.12

    if isinstance(llm_res, dict) and llm_res.get('parse_error'):
        penalty += 0.08

    if 'fallback' in state.llm_provider.lower():
        penalty += 0.05

    if state.errors:
        penalty += min(len(state.errors) * 0.05, 0.15)

    final_conf = base_confidence - penalty
    return round(min(max(final_conf, 0.45), 0.99), 2)


async def run_governance_pipeline(request_id, user_id, role, action, target,
                                    data_classification="Internal", business_purpose="",
                                    authorization_status="Verified", metadata=None):
    """Execute the deterministic policy governance pipeline and return GovernResponse."""
    execution_id = f"EXEC-{uuid.uuid4().hex[:8].upper()}"

    # 1. Normalize Input Parameters
    norm_inp = normalize_governance_input(
        user_id=user_id, role=role, action=action, target=target,
        data_classification=data_classification, authorization_status=authorization_status
    )

    state = GovernanceState.from_request(
        request_id=request_id, user_id=user_id, role=role,
        action=action, target=target,
        data_classification=data_classification,
        business_purpose=business_purpose,
        authorization_status=authorization_status,
        metadata=metadata or {}
    )
    state.execution_id = execution_id
    state.metadata["normalized_input"] = norm_inp._asdict()
    lifecycle_history = []

    try:
        # 2. Planning
        logger.info(f'[{request_id}] Starting governance pipeline (Execution: {execution_id})')
        state = await run_planner(state)
        
        # 3. Intent + Identity
        state = await run_intent(state)
        state = await run_identity(state)
        
        # 4. Policy RAG Retrieval
        state.add_agent_execution('policy_retrieval')
        try:
            evidence = await retrieve_policy_context(
                action,
                {
                    'target': target,
                    'role': role,
                    'user_id': user_id,
                    'data_classification': data_classification,
                    'authorization_status': authorization_status
                }
            )
            state.policy_evidence = evidence
            state.complete_agent_execution('policy_retrieval', AgentStatus.COMPLETED)
        except Exception as e:
            logger.error(f'RAG retrieval failed: {e}')
            state.errors.append(f'RAG retrieval failed: {e}')
            state.complete_agent_execution('policy_retrieval', AgentStatus.FAILED, str(e))
        
        # 5. LLM Provider Contextual Reasoning (IBM Granite via Hugging Face Router or Mock)
        state.add_agent_execution('llm_reasoning')
        granite_succeeded = False
        try:
            from rag.granite.factory import get_llm_provider
            from rag.granite.huggingface_provider import HuggingFaceProvider, HuggingFaceCallFailedError

            llm_provider = get_llm_provider()

            policy_texts = "\n".join([f"- [{ev.policy_name} ({ev.section})]: {ev.text}" for ev in (state.policy_evidence or [])])
            prompt = (
                f"Proposed AI Action: {action}\n"
                f"Target Endpoint: {target} (Env: {norm_inp.target_environment}, Trust: {norm_inp.target_trust}, External: {norm_inp.is_external})\n"
                f"Requester Role: {role} (Normalized: {norm_inp.normalized_role}, ID: {user_id})\n"
                f"Data Classification: {data_classification} (Normalized: {norm_inp.data_classification})\n"
                f"Authorization Status: {authorization_status} (Normalized: {norm_inp.authorization_status})\n"
                f"Business Purpose: {business_purpose}\n\n"
                f"Authoritative Enterprise Policy Evidence from RAG Retrieval:\n"
                f"{policy_texts if policy_texts else 'No specific policy evidence found.'}\n\n"
                f"Analyze the proposed action against the supplied enterprise policy evidence. Provide policy_findings, risk_analysis, reasoning, and modification_recommendations."
            )

            try:
                granite_res = await llm_provider.generate_structured(
                    prompt=prompt,
                    context=state.to_dict() if hasattr(state, 'to_dict') else None
                )
                state.metadata['llm_result'] = granite_res
                state.llm_provider = llm_provider.get_provider_name()
                granite_succeeded = True
                state.complete_agent_execution('llm_reasoning', AgentStatus.COMPLETED)

            except (HuggingFaceCallFailedError, Exception) as llm_err:
                reason = str(llm_err)
                logger.warning(f"[LLM] Falling back to MockProvider: reason: {reason}")
                
                from rag.granite.mock_provider import MockProvider
                fallback_provider = MockProvider(name_override="Mock Fallback")
                mock_res = await fallback_provider.generate_structured(prompt=prompt)
                
                state.metadata['llm_result'] = mock_res
                state.metadata['llm_fallback_reason'] = reason
                
                state.llm_provider = "IBM Granite 7B (Mock Engine)"

                state.errors.append(f"Granite API failure: {reason}")
                state.complete_agent_execution('llm_reasoning', AgentStatus.COMPLETED, f"Fallback: {reason}")

        except Exception as outer_err:
            logger.error(f"[LLM] LLM Reasoning execution error: {outer_err}")
            state.llm_provider = "IBM Granite 7B (Mock Engine)"
            state.complete_agent_execution('llm_reasoning', AgentStatus.SKIPPED, str(outer_err))

        # 6. Compliance & Inherent Risk Assessment
        state = await run_compliance(state)
        state = await run_risk(state)
        
        calculated_confidence = calculate_dynamic_confidence(state)
        state.confidence = calculated_confidence
        conf_pct = int(round(calculated_confidence * 100))

        # Stage 1: Inherent & Effective Risk Assessment
        score_inh = state.risk.inherent_risk_score if state.risk else 50
        score_eff = state.risk.effective_risk if state.risk else 50
        red_pts = state.risk.risk_reduction if state.risk else 0
        level_inh = get_standard_risk_level(score_inh)
        level_eff = state.risk.risk_level if state.risk else get_standard_risk_level(score_eff)
        signals_inh = {f.factor: f.score for f in state.risk.risk_factors} if state.risk else {}
        rationale_inh = [f.description for f in state.risk.risk_factors] if state.risk else []

        inherent_risk = RiskAssessment(
            score=score_inh,
            level=level_inh,
            confidence=conf_pct,
            signals=signals_inh,
            rationale=rationale_inh
        )
        state.inherent_risk = inherent_risk
        state.risk_reduction = red_pts
        
        lifecycle_history.append(ExecutionStageItem(
            stage="INHERENT_RISK",
            details={"inherent_score": score_inh, "level": level_inh.value, "confidence": conf_pct}
        ))

        # 7. Deterministic Policy Evaluation & Centralized Decision Resolution
        active_db_policies = []
        if SessionLocal and DBPolicy:
            try:
                db = SessionLocal()
                try:
                    active_db_policies = [{
                        "policy_id": p.policy_id,
                        "name": p.name,
                        "description": p.description,
                        "rule_definition": p.rule_definition,
                        "decision_action": p.decision_action,
                        "priority": p.priority
                    } for p in db.query(DBPolicy).filter(DBPolicy.status == "ACTIVE").all()]
                finally:
                    db.close()
            except Exception as dberr:
                logger.warning(f"Failed to fetch active policies from DB: {dberr}")

        policy_traces = evaluate_explicit_policies(
            norm_inp, active_policies=active_db_policies
        )

        winning_decision, decision_source, risk_derived_decision, decision_summary = resolve_final_decision(
            policy_traces, score_eff
        )

        state.decision = winning_decision
        state.policy_decision = winning_decision
        state.final_decision = winning_decision.value

        # Ensure Policy-Risk Score Alignment: If explicit policy REJECTs/ESCALATEs, risk score reflects severity
        if winning_decision == GovernanceDecision.REJECT and score_eff < 75:
            score_eff = max(score_eff, 85)
            level_eff = get_standard_risk_level(score_eff)
            red_pts = 0
        elif winning_decision == GovernanceDecision.ESCALATE and score_eff < 50:
            score_eff = max(score_eff, 60)
            level_eff = get_standard_risk_level(score_eff)

        if state.risk:
            state.risk.risk_score = score_eff
            state.risk.effective_risk = score_eff
            state.risk.risk_level = level_eff
            state.risk.risk_reduction = red_pts

        matched_active_traces = [t for t in policy_traces if t.matched]
        state.metadata["decision_source"] = decision_source
        state.metadata["matched_policies"] = [t.policy_id for t in matched_active_traces]
        
        lifecycle_history.append(ExecutionStageItem(
            stage="POLICY_DECISION",
            details={
                "decision": winning_decision.value,
                "source": decision_source,
                "matched_policy_ids": [t.policy_id for t in matched_active_traces]
            }
        ))

        state = await run_explainability(state)
        state = await run_reviewer(state)
        
        # Apply reviewer escalation check ONLY when explicit reviewer evidence demands it
        if state.review and state.review.requires_human_review and winning_decision not in [GovernanceDecision.REJECT]:
            if not matched_active_traces or winning_decision == GovernanceDecision.APPROVE and not matched_active_traces:
                winning_decision = GovernanceDecision.ESCALATE
                state.human_review_required = True

        # 8. Workflows based on Winning Decision
        if winning_decision == GovernanceDecision.MODIFY:
            state = await run_transformation(state)
            
            # SAFETY GATE: If transformation was blocked (dangerous/prohibited action), REJECT
            if state.transformation and getattr(state.transformation, 'transformation_blocked', False):
                state.decision = GovernanceDecision.REJECT
                state.final_decision = "REJECT"
                lifecycle_history.append(ExecutionStageItem(
                    stage="TRANSFORMATION",
                    details={
                        "applied": False,
                        "blocked": True,
                        "block_reason": getattr(state.transformation, 'block_reason', 'Dangerous action'),
                        "summary": state.transformation.transformation_summary
                    }
                ))
                lifecycle_history.append(ExecutionStageItem(
                    stage="FINAL_DECISION",
                    details={"decision": "REJECT", "reason": "Transformation blocked: action is prohibited"}
                ))

            elif state.transformation and state.transformation.transformation_applied and \
               state.transformation.modified_request != state.transformation.original_request:
                
                lifecycle_history.append(ExecutionStageItem(
                    stage="TRANSFORMATION",
                    details={
                        "applied": True,
                        "changes_count": len(state.transformation.changes),
                        "summary": state.transformation.transformation_summary
                    }
                ))

                # Re-run Canonical Risk Engine on modified request
                mod_req = state.transformation.modified_request
                mod_inh, mod_eff, mod_red, mod_level, mod_factors, mod_mitigations, mod_signals = compute_canonical_risk(
                    data_classification=mod_req.get('data_classification'),
                    target=mod_req.get('target'),
                    authorization_status=mod_req.get('authorization_status'),
                    role=mod_req.get('role'),
                    action=mod_req.get('action'),
                    identity=state.identity
                )

                # Include transformation risk reduction points
                trans_red = 35 if (state.transformation and state.transformation.transformation_applied) else 0
                total_reduction = red_pts + trans_red
                final_effective_score = max(0, min(99, score_inh - total_reduction))
                final_effective_level = get_standard_risk_level(final_effective_score)

                final_risk = RiskAssessment(
                    score=final_effective_score,
                    level=final_effective_level,
                    confidence=conf_pct,
                    signals=mod_signals,
                    rationale=[f.description for f in mod_factors] + mod_mitigations
                )
                state.final_risk = final_risk
                state.risk_reduction = total_reduction
                
                if state.risk:
                    state.risk.effective_risk = final_effective_score
                    state.risk.risk_score = final_effective_score
                    state.risk.risk_level = final_effective_level
                    state.risk.risk_reduction = total_reduction
                
                lifecycle_history.append(ExecutionStageItem(
                    stage="FINAL_RISK",
                    details={"score": final_effective_score, "level": final_effective_level.value, "reduction": total_reduction}
                ))

                # Gate final decision on RE-EVALUATED risk score (not hardcoded)
                if final_effective_score <= 24:
                    state.final_decision = "APPROVED AFTER MODIFICATION"
                    state.decision = GovernanceDecision.MODIFY
                elif final_effective_score <= 49:
                    state.final_decision = "APPROVED AFTER MODIFICATION"
                    state.decision = GovernanceDecision.MODIFY
                else:
                    # Transformation wasn't sufficient to reduce risk — escalate
                    state.final_decision = "ESCALATE"
                    state.decision = GovernanceDecision.ESCALATE
                    state.human_review_required = True

                lifecycle_history.append(ExecutionStageItem(
                    stage="FINAL_DECISION",
                    details={"decision": state.final_decision, "post_transformation_risk": final_effective_score}
                ))
            else:
                state.final_decision = "MODIFY"
                state.decision = GovernanceDecision.MODIFY

        elif winning_decision == GovernanceDecision.ESCALATE:
            state.human_review_required = True
            state.decision = GovernanceDecision.ESCALATE
            state.final_decision = "ESCALATE"
            lifecycle_history.append(ExecutionStageItem(
                stage="FINAL_DECISION",
                details={"decision": "ESCALATE"}
            ))

        elif winning_decision == GovernanceDecision.REJECT:
            state.decision = GovernanceDecision.REJECT
            state.final_decision = "REJECT"
            lifecycle_history.append(ExecutionStageItem(
                stage="FINAL_DECISION",
                details={"decision": "REJECT"}
            ))

        else:
            state.decision = GovernanceDecision.APPROVE
            state.final_decision = "APPROVE"
            lifecycle_history.append(ExecutionStageItem(
                stage="FINAL_DECISION",
                details={"decision": "APPROVE"}
            ))

        state.lifecycle_history = lifecycle_history
        state.pipeline_completed_at = datetime.now(timezone.utc)
        
        # Refresh Explainability & Reviewer summaries with finalized decision
        state = await run_explainability(state)
        state = await run_reviewer(state)

        # Calculate provider status badge
        if 'fallback' in state.llm_provider.lower() or 'failed' in state.llm_provider.lower():
            provider_status = 'fallback'
        elif 'mock' in state.llm_provider.lower():
            provider_status = 'mock'
        else:
            provider_status = 'active'
        state.provider_status = provider_status

        # Build audit record
        audit = AuditRecord(
            request_id=request_id, user_id=user_id, role=role,
            action=action, target=target,
            intent=state.intent, identity=state.identity,
            compliance=state.compliance, risk=state.risk,
            explainability=state.explainability, review=state.review,
            transformation=state.transformed_action,
            decision=state.decision,
            risk_score=state.inherent_risk.score if state.inherent_risk else 0,
            risk_level=state.inherent_risk.level if state.inherent_risk else RiskLevel.CRITICAL,
            policy_evidence=state.policy_evidence,
            agents_executed=state.agents_executed,
            pipeline_duration_ms=state.get_pipeline_duration_ms(),
            human_review_required=state.human_review_required,
            llm_provider=state.llm_provider,
        )
        audit_service.save_record(audit)
        
        # Build 5-point decision rationale clearly explaining matched policy & decision source
        exp_dec = state.final_decision or (state.decision.value if hasattr(state.decision, 'value') else (str(state.decision) if state.decision else "APPROVE"))
        explanation = f"Governance decision: {exp_dec} for action."
        if state.explainability:
            state.explainability.summary = explanation
        recommended = ''
        if state.decision == GovernanceDecision.APPROVE:
            recommended = 'Action is approved for execution.'
        elif state.decision == GovernanceDecision.MODIFY:
            recommended = f'Action modified: {state.transformation.transformation_summary if state.transformation else "apply risk reduction"}'
        elif state.decision == GovernanceDecision.ESCALATE:
            recommended = 'Action requires human review before proceeding.'
        else:
            recommended = 'Action is rejected. Do not proceed.'
        
        # Build 6-point structured decision rationale explicitly explaining 3-stage risk model
        rationale = []
        if matched_active_traces:
            m_primary = matched_active_traces[0]
            rationale.append(f"1. Matched Policy: {m_primary.policy_name} ({m_primary.policy_id}) -> {m_primary.rule_description}")
        else:
            rationale.append("1. Matched Policy: No explicit policy override. Evaluated against baseline enterprise rules.")

        rationale.append(f"2. Inherent Risk: Calculated at {score_inh}/100 ({level_inh.value}) before mitigations.")

        mit_summary = ", ".join(state.risk.mitigating_factors) if (state.risk and state.risk.mitigating_factors) else "None"
        rationale.append(f"3. Mitigating Factors: {mit_summary}")

        if state.transformation and state.transformation.transformation_applied:
            rationale.append(f"4. Transformation: Applied - {state.transformation.transformation_summary}")
        else:
            rationale.append("4. Transformation: No transformation applied.")

        effective_pts = state.final_risk.score if state.final_risk else score_eff
        effective_lvl = state.final_risk.level.value if state.final_risk else level_eff.value
        total_red = state.risk_reduction if state.risk_reduction is not None else red_pts

        rationale.append(f"5. Risk Reduction & Effective Risk: Reduction -{total_red} pts -> Effective Risk: {effective_pts}/100 ({effective_lvl}).")
        rationale.append(f"6. Final Decision Source: Selected via '{decision_source}' -> Decision: {state.final_decision}.")
            
        state.decision_rationale = rationale
        
        debug_info = {
            "selected_provider": state.llm_provider,
            "provider_requested": "IBM Granite 7B via Hugging Face",
            "provider_used": "Mock Provider" if provider_status == "fallback" else state.llm_provider,
            "granite_succeeded": granite_succeeded,
            "fallback_used": provider_status == "fallback",
            "fallback_reason": state.metadata.get("llm_fallback_reason", None),
            "matched_policy_ids": [t.policy_id for t in matched_active_traces],
            "explicit_policy_decisions": [{
                "policy_id": t.policy_id,
                "name": t.policy_name,
                "matched": t.matched,
                "decision": t.decision.value,
                "rule": t.rule_description,
                "matched_conditions": t.matched_conditions
            } for t in policy_traces],
            "normalized_input": norm_inp._asdict(),
            "target_trust_level": norm_inp.target_trust,
            "external_classification": norm_inp.is_external,
            "individual_risk_signals": state.inherent_risk.signals if state.inherent_risk else {},
            "inherent_risk_score": score_inh,
            "risk_reduction_pts": total_red,
            "effective_risk_score": effective_pts,
            "risk_derived_decision": risk_derived_decision.value,
            "final_decision_source": decision_source
        }

        return GovernResponse(
            request_id=request_id,
            execution_id=execution_id,
            decision=state.decision,
            policy_decision=state.policy_decision,
            final_decision=state.final_decision,
            risk_score=effective_pts,
            effective_risk=effective_pts,
            risk_level=state.final_risk.level if state.final_risk else level_eff,
            inherent_risk=state.inherent_risk,
            final_risk=state.final_risk,
            risk_reduction=total_red,
            mitigating_factors=state.risk.mitigating_factors if state.risk else [],
            matched_policy_ids=[t.policy_id for t in matched_active_traces],
            lifecycle_history=state.lifecycle_history,
            intent=state.intent, identity=state.identity,
            compliance=state.compliance, risk=state.risk,
            review=state.review,
            evidence=state.policy_evidence,
            explanation=explanation,
            transformation=state.transformation,
            recommended_action=recommended,
            agents_executed=state.agents_executed,
            pipeline_duration_ms=state.get_pipeline_duration_ms(),
            llm_provider=state.llm_provider,
            provider_status=provider_status,
            audit_id=audit.audit_id,
            human_review_required=state.human_review_required or (state.review.requires_human_review if state.review else False),
            confidence=calculated_confidence,
            decision_rationale=rationale,
            decision_source=decision_source,
            debug_info=debug_info,
            data_classification=data_classification,
            business_purpose=business_purpose,
            authorization_status=authorization_status,
        )
        
    except Exception as e:
        logger.error(f'Pipeline error: {e}', exc_info=True)
        state.errors.append(str(e))
        state.pipeline_completed_at = datetime.now(timezone.utc)
        
        return GovernResponse(
            request_id=request_id,
            execution_id=execution_id,
            decision=GovernanceDecision.ESCALATE,
            policy_decision=GovernanceDecision.ESCALATE,
            final_decision="ESCALATE",
            risk_score=100,
            risk_level=RiskLevel.CRITICAL,
            explanation=f'Governance pipeline error: {str(e)}. Escalating for safety.',
            recommended_action='Pipeline failed. Manual review required.',
            agents_executed=state.agents_executed,
            pipeline_duration_ms=state.get_pipeline_duration_ms(),
            llm_provider=state.llm_provider,
            provider_status="fallback",
            confidence=0.50,
            decision_source="fallback_risk_engine",
            debug_info={"error": str(e)}
        )
