"""
Escalations API - Manage escalation requests.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from ...database import get_db
from ...models import Escalation

router = APIRouter()


class EscalationResponse(BaseModel):
    """Schema for escalation responses."""

    escalation_id: str
    record_id: str
    customer_id: Optional[str]
    agent_id: str
    tool_name: str
    params: dict
    reason: str
    status: str
    resolved_by: Optional[str]
    resolution_timestamp: Optional[str]
    created_at: str
    expires_at: str

    class Config:
        from_attributes = True


class ResolveEscalation(BaseModel):
    """Schema for resolving an escalation."""

    resolution: str  # approved or denied
    resolved_by: str


@router.get("/escalations", response_model=List[EscalationResponse])
async def list_escalations(
    customer_id: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    status: str = Query("pending"),
    db: AsyncSession = Depends(get_db),
):
    """List escalations with filters."""
    query = select(Escalation)

    filters = [Escalation.status == status]
    if customer_id:
        filters.append(Escalation.customer_id == customer_id)
    if agent_id:
        filters.append(Escalation.agent_id == agent_id)

    query = query.where(and_(*filters)).order_by(Escalation.created_at.desc())

    result = await db.execute(query)
    escalations = result.scalars().all()

    return [EscalationResponse(**e.to_dict()) for e in escalations]


@router.get("/escalations/{escalation_id}", response_model=EscalationResponse)
async def get_escalation(escalation_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific escalation."""
    result = await db.execute(
        select(Escalation).where(Escalation.escalation_id == escalation_id)
    )
    escalation = result.scalar_one_or_none()

    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    return EscalationResponse(**escalation.to_dict())


@router.post("/escalations/{escalation_id}/resolve", response_model=EscalationResponse)
async def resolve_escalation(
    escalation_id: str, resolution_data: ResolveEscalation, db: AsyncSession = Depends(get_db)
):
    """
    Resolve an escalation (approve or deny).

    This is called by humans via the dashboard UI.
    """
    # Validate resolution
    if resolution_data.resolution not in ("approved", "denied"):
        raise HTTPException(status_code=400, detail="Resolution must be 'approved' or 'denied'")

    # Get escalation
    result = await db.execute(
        select(Escalation).where(Escalation.escalation_id == escalation_id)
    )
    escalation = result.scalar_one_or_none()

    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    if escalation.status != "pending":
        raise HTTPException(
            status_code=409, detail=f"Escalation already {escalation.status}"
        )

    # Check if expired
    if datetime.utcnow() > escalation.expires_at:
        escalation.status = "expired"
        await db.commit()
        raise HTTPException(status_code=410, detail="Escalation has expired")

    # Resolve escalation
    escalation.status = resolution_data.resolution
    escalation.resolved_by = resolution_data.resolved_by
    escalation.resolution_timestamp = datetime.utcnow()

    await db.commit()
    await db.refresh(escalation)

    return EscalationResponse(**escalation.to_dict())
