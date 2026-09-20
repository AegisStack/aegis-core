"""
Escalations API - Manage escalation requests.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models import Escalation, User
from ...services.auth import get_current_active_user, require_role

router = APIRouter()


class EscalationResponse(BaseModel):
    """Schema for escalation responses."""

    escalation_id: str
    record_id: str
    customer_id: str | None
    agent_id: str
    tool_name: str
    params: dict
    reason: str
    status: str
    resolved_by: str | None
    resolution_timestamp: str | None
    created_at: str
    expires_at: str

    class Config:
        from_attributes = True


class ResolveEscalation(BaseModel):
    """Schema for resolving an escalation."""

    resolution: str  # approved or denied


@router.get("/escalations", response_model=list[EscalationResponse])
async def list_escalations(
    agent_id: str | None = Query(None),
    status: str = Query("pending"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List escalations for the caller's own tenant, with filters."""
    query = select(Escalation)

    filters = [Escalation.status == status, Escalation.customer_id == current_user.customer_id]
    if agent_id:
        filters.append(Escalation.agent_id == agent_id)

    query = query.where(and_(*filters)).order_by(Escalation.created_at.desc())

    result = await db.execute(query)
    escalations = result.scalars().all()

    return [EscalationResponse(**e.to_dict()) for e in escalations]


@router.get("/escalations/{escalation_id}", response_model=EscalationResponse)
async def get_escalation(
    escalation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific escalation (scoped to the caller's own tenant)."""
    result = await db.execute(select(Escalation).where(Escalation.escalation_id == escalation_id))
    escalation = result.scalar_one_or_none()

    if not escalation or escalation.customer_id != current_user.customer_id:
        raise HTTPException(status_code=404, detail="Escalation not found")

    return EscalationResponse(**escalation.to_dict())


@router.post("/escalations/{escalation_id}/resolve", response_model=EscalationResponse)
async def resolve_escalation(
    escalation_id: str,
    resolution_data: ResolveEscalation,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("operator")),
):
    """
    Resolve an escalation (approve or deny).

    Called by humans via the dashboard UI. `resolved_by` is taken from the
    authenticated user rather than the request body, so it can't be spoofed.
    """
    # Validate resolution
    if resolution_data.resolution not in ("approved", "denied"):
        raise HTTPException(status_code=400, detail="Resolution must be 'approved' or 'denied'")

    # Get escalation, scoped to the caller's own tenant
    result = await db.execute(select(Escalation).where(Escalation.escalation_id == escalation_id))
    escalation = result.scalar_one_or_none()

    if not escalation or escalation.customer_id != current_user.customer_id:
        raise HTTPException(status_code=404, detail="Escalation not found")

    if escalation.status != "pending":
        raise HTTPException(status_code=409, detail=f"Escalation already {escalation.status}")

    # Check if expired. expires_at may come back naive (SQLite) or
    # timezone-aware (PostgreSQL) depending on the DB backend - normalize
    # before comparing so this doesn't crash on either.
    expires_at = escalation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        escalation.status = "expired"
        await db.commit()
        raise HTTPException(status_code=410, detail="Escalation has expired")

    # Resolve escalation
    escalation.status = resolution_data.resolution
    escalation.resolved_by = current_user.email
    escalation.resolution_timestamp = datetime.utcnow()

    await db.commit()
    await db.refresh(escalation)

    return EscalationResponse(**escalation.to_dict())
