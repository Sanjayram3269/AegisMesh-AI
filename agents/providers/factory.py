"""Bridge factory in agents/providers delegating to rag.granite.factory."""
from rag.granite.factory import get_llm_provider
from rag.granite.base import LLMProvider

__all__ = ['get_llm_provider', 'LLMProvider']
