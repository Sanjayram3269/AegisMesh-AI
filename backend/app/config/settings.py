import os
from typing import Optional
from pydantic_settings import BaseSettings

# Absolute path to root .env file
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
env_path = os.path.join(root_dir, ".env")

class Settings(BaseSettings):
    # App
    app_env: str = 'development'
    demo_mode: bool = True
    debug: bool = True
    
    # Backend
    backend_host: str = '0.0.0.0'
    backend_port: int = 8000
    
    # LLM Provider Configuration (Hugging Face Router / IBM Granite)
    llm_provider: str = 'huggingface'
    hf_token: str = ''
    hf_router_url: str = 'https://router.huggingface.co/v1'
    hf_model: str = 'ibm-granite/granite-7b-instruct:featherless-ai'
    llm_allow_mock_fallback: bool = True

    # Database
    database_url: str = 'sqlite:///./aegismesh.db'
    
    # RAG
    rag_provider: str = 'local'
    vector_store_path: str = './rag/vectorstore/data'
    
    # Security
    secret_key: str = 'change-this-in-production'
    allowed_origins: str = 'http://localhost:5173,http://localhost:3000'
    
    # Governance
    max_agent_iterations: int = 5
    default_escalation_threshold: int = 70
    fail_closed: bool = True
    
    @property
    def huggingface_available(self) -> bool:
        return bool(self.hf_token)
    
    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(',')]
    
    class Config:
        env_file = env_path if os.path.exists(env_path) else os.path.join(os.getcwd(), '.env')
        env_file_encoding = 'utf-8'
        extra = 'ignore'

def get_settings() -> Settings:
    return Settings()
