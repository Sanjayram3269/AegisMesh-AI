"""Base LLM Provider Interface for AegisMesh AI."""
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class LLMResult:
    """Standardized result returned by LLM Providers."""
    provider: str                      # "granite" or "mock"
    model: str                         # Model ID string
    generated_text: str                # Raw or generated text output
    structured_output: Optional[dict[str, Any]] = None  # Validated JSON dict if requested
    success: bool = True               # Execution status
    latency_ms: int = 0               # Call duration in milliseconds
    error_message: Optional[str] = None # Error details if failed

class BaseLLMProvider:
    """Abstract Base Class for AegisMesh LLM Providers."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        structured: bool = False,
        schema: Optional[dict[str, Any]] = None
    ) -> LLMResult:
        raise NotImplementedError("Subclasses must implement generate()")
