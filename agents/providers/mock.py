"""Mock LLM Provider for AegisMesh AI — Offline Demo Mode."""
import time
from typing import Any, Optional
from .base import BaseLLMProvider, LLMResult

class MockProvider(BaseLLMProvider):
    """Deterministic Mock LLM Provider for offline demo and safe fallback."""

    def __init__(self, model_name: str = "mock-granite-3-8b"):
        self.model_name = model_name

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        structured: bool = False,
        schema: Optional[dict[str, Any]] = None
    ) -> LLMResult:
        start_time = time.time()
        p_lower = prompt.lower()

        if 'confidential' in p_lower or 'unauthorized' in p_lower:
            findings = ["Prohibited transfer of confidential data to untrusted endpoint."]
            reasoning = "Action violates enterprise data transfer policy POL-TRN-002. Confidential data export to unauthorized endpoint is strictly prohibited."
            rec = ["Block execution immediately."]
            confidence = 0.95
        elif 'pii' in p_lower or 'email' in p_lower or 'phone' in p_lower or 'records' in p_lower:
            findings = ["Customer PII detected in export action."]
            reasoning = "Action contains unmasked PII. Policy POL-PII-003 mandates anonymization or field stripping prior to transfer."
            rec = ["Anonymize customer email and phone fields before export.", "Use approved analytics proxy."]
            confidence = 0.91
        elif 'new' in p_lower or 'vendor' in p_lower:
            findings = ["Transfer to unapproved external vendor."]
            reasoning = "Target endpoint is a new external vendor. Policy POL-HUM-001 requires CISO or executive authorization."
            rec = ["Escalate for human review and CISO sign-off."]
            confidence = 0.88
        else:
            findings = ["Compliant internal analytics query."]
            reasoning = "Action is grounded in active enterprise policies and operates on internal data."
            rec = ["Authorize execution."]
            confidence = 0.98

        structured_data = {
            "intent_summary": "Parsed governance request",
            "policy_findings": findings,
            "risk_analysis": reasoning,
            "modification_recommendations": rec,
            "reasoning": reasoning,
            "confidence": confidence,
            "insufficient_evidence": False
        }

        text = f"Mock LLM Governance Analysis: {reasoning}"
        latency = int((time.time() - start_time) * 1000) + 8

        return LLMResult(
            provider="mock",
            model=self.model_name,
            generated_text=text,
            structured_output=structured_data if structured else None,
            success=True,
            latency_ms=latency
        )
