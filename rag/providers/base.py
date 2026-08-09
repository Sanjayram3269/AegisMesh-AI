from abc import ABC, abstractmethod
from typing import Any

class RAGProvider(ABC):
    @abstractmethod
    async def retrieve(self, query: str, context: dict[str, Any] = None, top_k: int = 5) -> list[dict[str, Any]]:
        """Retrieve relevant policy documents."""
        pass
