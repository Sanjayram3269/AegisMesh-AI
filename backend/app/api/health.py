from fastapi import APIRouter
from app.schemas.governance import HealthResponse
from app.config.settings import get_settings
from rag.granite.factory import get_llm_provider
from rag.granite.huggingface_provider import HuggingFaceProvider

router = APIRouter()

@router.get('/health', response_model=HealthResponse)
async def health_check():
    settings = get_settings()
    provider_inst = get_llm_provider()
    
    if hasattr(provider_inst, "get_provider_info"):
        provider_data = provider_inst.get_provider_info()
    else:
        provider_data = {
            "name": provider_inst.get_provider_name(),
            "type": "huggingface" if isinstance(provider_inst, HuggingFaceProvider) else "mock",
            "configured": provider_inst.is_configured()
        }

    return HealthResponse(
        status='healthy',
        version='0.1.0',
        provider=provider_data,
        demo_mode=settings.demo_mode,
        database='connected'
    )
