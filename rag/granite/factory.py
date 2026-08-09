"""Factory for instantiating LLM Providers in AegisMesh AI."""
import os
import logging
from typing import Optional
from .base import LLMProvider
from .mock_provider import MockProvider
from .huggingface_provider import HuggingFaceProvider

logger = logging.getLogger('aegismesh.llm')

def get_llm_provider(mode_override: Optional[str] = None) -> LLMProvider:
    """
    Get the configured LLM provider instance.
    
    Architecture:
    LLMProvider
    ├── HuggingFaceProvider (IBM Granite via Hugging Face Router)
    └── MockProvider        (Offline Demo / Fallback)
    """
    try:
        from backend.app.config.settings import get_settings
    except ImportError:
        try:
            from app.config.settings import get_settings
        except ImportError:
            get_settings = None

    settings = get_settings() if get_settings else None

    token = (getattr(settings, 'hf_token', '') if settings else '') or os.getenv('HF_TOKEN', '')
    router_url = (getattr(settings, 'hf_router_url', '') if settings else '') or os.getenv('HF_ROUTER_URL', 'https://router.huggingface.co/v1')
    model = (getattr(settings, 'hf_model', '') if settings else '') or os.getenv('HF_MODEL', 'ibm-granite/granite-7b-instruct:featherless-ai')

    mode = (mode_override or (getattr(settings, 'llm_provider', '') if settings else None) or os.getenv('LLM_PROVIDER') or 'auto').lower()

    if mode == 'mock' or not token:
        logger.info("[LLM] MockProvider active")
        return MockProvider(name_override="Mock Demo")

    # If HF_TOKEN is present and non-empty -> HuggingFaceProvider
    hf_provider = HuggingFaceProvider(
        api_key=token,
        base_url=router_url,
        model=model
    )

    logger.info(f"[LLM] Provider selected: {hf_provider.get_provider_name()}")
    return hf_provider
