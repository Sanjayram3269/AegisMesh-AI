"""Mock LLM Provider for AegisMesh AI — Demo Mode & Fallback."""
from typing import Any, Optional
from .base import LLMProvider

class MockProvider(LLMProvider):
    def __init__(self, name_override: Optional[str] = None):
        self.name_override = name_override or 'Mock Demo'

    async def generate_structured(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
        schema: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        p_lower = prompt.lower()
        if 'confidential' in p_lower or 'unauthorized' in p_lower:
            reasoning = "Action violates enterprise data transfer policy POL-TRN-002. Confidential data export to unauthorized endpoint is strictly prohibited."
            rec = ["Block execution immediately."]
        elif 'pii' in p_lower or 'email' in p_lower or 'phone' in p_lower or 'records' in p_lower:
            reasoning = "Action contains unmasked PII. Policy POL-PII-003 mandates anonymization or field stripping prior to transfer."
            rec = ["Anonymize customer email and phone fields before export.", "Use approved analytics proxy."]
        elif 'new' in p_lower or 'vendor' in p_lower:
            reasoning = "Target endpoint is a new external vendor. Policy POL-HUM-001 requires CISO or executive authorization."
            rec = ["Escalate for human review and CISO sign-off."]
        else:
            reasoning = "Action is grounded in active enterprise policies and operates on internal data."
            rec = ["Authorize execution."]

        return {
            'provider': self.get_provider_name(),
            'status': 'processed',
            'reasoning': reasoning,
            'policy_findings': [reasoning],
            'modification_recommendations': rec,
            'confidence': 0.95,
            'insufficient_evidence': False,
        }

    def get_provider_name(self) -> str:
        return self.name_override

    def is_available(self) -> bool:
        return True
