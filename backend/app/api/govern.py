import traceback
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.schemas.governance import (
    GovernRequest, GovernResponse, GovernanceDecision, RiskLevel,
    ErrorResponse
)
from app.config.settings import get_settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post('/govern', response_model=GovernResponse)
async def govern_action(request: GovernRequest):
    """Submit a proposed AI action for governance evaluation."""
    settings = get_settings()
    try:
        # Import orchestrator
        import sys, os, importlib
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        import agents.orchestrator as orch_mod
        importlib.reload(orch_mod)
        from agents.orchestrator import run_governance_pipeline
        logger.info(f"Loaded orchestrator from: {orch_mod.__file__}")
        
        result = await run_governance_pipeline(
            request_id=request.request_id,
            user_id=request.user_id,
            role=request.role,
            action=request.action,
            target=request.target,
            data_classification=request.data_classification,
            business_purpose=request.business_purpose,
            authorization_status=request.authorization_status,
            metadata=request.metadata,
        )
        logger.info(f"[GOVERN API] Decision: {result.decision}, Explanation: {result.explanation}")
        return result
    except ImportError as e:
        logger.error(f'Orchestrator not available: {e}')
        raise HTTPException(status_code=503, detail=f'Governance pipeline not available: {e}')
    except Exception as e:
        logger.error(f'Governance error: {e}\n{traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=f'Governance evaluation failed: {str(e)}')
