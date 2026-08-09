from fastapi import APIRouter, HTTPException
from app.schemas.governance import AuditListResponse, AuditRecord
from app.services.audit_service import AuditService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
audit_service = AuditService()

@router.get('/audit', response_model=AuditListResponse)
async def list_audit_records():
    records = audit_service.list_records()
    return AuditListResponse(total=len(records), records=records)

@router.get('/audit/{request_id}', response_model=AuditRecord)
async def get_audit_record(request_id: str):
    record = audit_service.get_record(request_id)
    if not record:
        raise HTTPException(status_code=404, detail=f'Audit record not found: {request_id}')
    return record
