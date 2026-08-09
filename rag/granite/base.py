from abc import ABC, abstractmethod
from typing import Any, Optional

class LLMProvider(ABC):
    @abstractmethod
    async def generate_structured(self, prompt: str, context: dict[str, Any] = None, schema: Optional[dict] = None) -> dict[str, Any]:
        """Generate structured output from the LLM."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
