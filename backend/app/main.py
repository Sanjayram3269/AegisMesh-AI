"""AegisMesh AI — Backend API Server"""

import logging
import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Add project root to path for agent/rag imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.config.settings import get_settings
from app.database.db import init_db, SessionLocal
from app.services.policy_service import seed_default_policies
from app.api import health, govern, audit, review, policies, policy_evolution

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('aegismesh')

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info('=' * 60)
    logger.info('  AegisMesh AI — Agentic Governance Control Plane')
    logger.info('=' * 60)
    logger.info(f'  Environment:  {settings.app_env}')
    logger.info(f'  Demo Mode:    {settings.demo_mode}')
    logger.info(f'  LLM Provider: {settings.llm_provider}')
    logger.info(f'  Database:     {settings.database_url}')
    logger.info('=' * 60)
    
    # Initialize DB & Seed Baseline Policies
    try:
        init_db()
        db = SessionLocal()
        try:
            seed_default_policies(db)
        finally:
            db.close()
    except Exception as err:
        logger.error(f"Error initializing DB / policies: {err}")

    yield
    logger.info('AegisMesh AI shutting down.')

app = FastAPI(
    title='AegisMesh AI',
    description='Agentic AI Governance Control Plane — Evaluates AI actions before execution.',
    version='0.1.0',
    lifespan=lifespan,
)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Routes
app.include_router(health.router, prefix='/api', tags=['Health'])
app.include_router(govern.router, prefix='/api', tags=['Governance'])
app.include_router(audit.router, prefix='/api', tags=['Audit'])
app.include_router(review.router, prefix='/api', tags=['Human Review'])
app.include_router(policies.router, prefix='/api', tags=['Policies'])
app.include_router(policy_evolution.router)

@app.get('/', response_class=FileResponse)
async def serve_dashboard():
    static_file = os.path.join(os.path.dirname(__file__), 'static', 'index.html')
    if os.path.exists(static_file):
        return FileResponse(static_file)
    return FileResponse(os.path.join(project_root, 'backend', 'app', 'static', 'index.html'))

@app.get('/api')
async def api_info():
    return {
        'name': 'AegisMesh AI',
        'description': 'Agentic AI Governance Control Plane',
        'docs': '/docs',
        'health': '/api/health'
    }
