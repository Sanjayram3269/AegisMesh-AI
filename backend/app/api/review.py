from fastapi import APIRouter, HTTPException
from app.schemas.governance import (
    HumanReviewRequest, HumanReviewResponse, HumanReviewAction,
    GovernanceDecision
)
from app.services.audit_service import AuditService
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
audit_service = AuditService()

@router.post('/review/{request_id}', response_model=HumanReviewResponse)
async def human_review(request_id: str, review: HumanReviewRequest):
    record = audit_service.get_record(request_id)
    if not record:
        raise HTTPException(status_code=404, detail=f'Request not found: {request_id}')
    
    # Map human action to governance decision
    decision_map = {
        HumanReviewAction.APPROVE: GovernanceDecision.APPROVE,
        HumanReviewAction.REJECT: GovernanceDecision.REJECT,
        HumanReviewAction.REQUEST_MODIFICATION: GovernanceDecision.MODIFY,
    }
    
    previous_decision = record.decision
    updated_decision = decision_map.get(review.action)
    
    # Update audit record
    audit_service.update_human_review(
        request_id=request_id,
        reviewer_id=review.reviewer_id,
        action=review.action,
        comments=review.comments,
        updated_decision=updated_decision,
    )
    
    return HumanReviewResponse(
        request_id=request_id,
        review_action=review.action,
        reviewer_id=review.reviewer_id,
        previous_decision=previous_decision,
        updated_decision=updated_decision,
        comments=review.comments,
    )
