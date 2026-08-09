"""FastAPI Endpoints for Dynamic Policy Management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.db import get_db
from app.schemas.policy import (
    PolicyCreate,
    PolicyUpdate,
    PolicyStatusUpdate,
    PolicyResponse,
    PolicyListResponse
)
from app.services import policy_service

router = APIRouter(prefix="/policies", tags=["Policies"])


@router.get("", response_model=PolicyListResponse)
def get_all_policies(db: Session = Depends(get_db)):
    """Retrieve all enterprise policies stored in persistent database."""
    policies = policy_service.get_all_policies(db)
    return PolicyListResponse(total=len(policies), policies=policies)


@router.get("/active", response_model=PolicyListResponse)
def get_active_policies(db: Session = Depends(get_db)):
    """Retrieve only ACTIVE policies used for RAG evidence retrieval and governance evaluation."""
    policies = policy_service.get_active_policies(db)
    return PolicyListResponse(total=len(policies), policies=policies)


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy_by_id(policy_id: str, db: Session = Depends(get_db)):
    """Retrieve a single policy by policy_id."""
    policy = policy_service.get_policy_by_id(db, policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found."
        )
    return policy


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(data: PolicyCreate, db: Session = Depends(get_db)):
    """Create a new enterprise policy."""
    try:
        policy = policy_service.create_policy(db, data)
        return policy
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create policy: {err}"
        )


@router.put("/{policy_id}", response_model=PolicyResponse)
def update_policy(policy_id: str, data: PolicyUpdate, db: Session = Depends(get_db)):
    """Update an existing enterprise policy and increment version."""
    try:
        policy = policy_service.update_policy(db, policy_id, data)
        return policy
    except KeyError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update policy: {err}"
        )


@router.patch("/{policy_id}/status", response_model=PolicyResponse)
def update_policy_status(policy_id: str, data: PolicyStatusUpdate, db: Session = Depends(get_db)):
    """Activate, deactivate, or set draft status for a policy."""
    try:
        policy = policy_service.update_policy_status(db, policy_id, data.status.value)
        return policy
    except KeyError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update policy status: {err}"
        )


@router.delete("/{policy_id}", status_code=status.HTTP_200_OK)
def delete_policy(policy_id: str, db: Session = Depends(get_db)):
    """Delete an enterprise policy."""
    try:
        policy_service.delete_policy(db, policy_id)
        return {"status": "success", "message": f"Policy '{policy_id}' deleted successfully."}
    except KeyError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete policy: {err}"
        )
