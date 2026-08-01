"""
Audit API - Query audit records.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models import AuditRecord
from ...schemas import AuditRecordResponse

router = APIRouter()


@router.get("/audit", response_model=list[AuditRecordResponse])
async def query_audit_records(
    customer_id: str | None = Query(None),
    agent_id: str | None = Query(None),
    tool_name: str | None = Query(None),
    outcome: str | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Query audit records with filters.

    Returns paginated list of audit records matching the filters.
    """
    # Build query
    query = select(AuditRecord)

    # Apply filters
    filters = []
    if customer_id:
        filters.append(AuditRecord.customer_id == customer_id)
    if agent_id:
        filters.append(AuditRecord.agent_id == agent_id)
    if tool_name:
        filters.append(AuditRecord.tool_name == tool_name)
    if outcome:
        filters.append(AuditRecord.outcome == outcome)
    if start_time:
        filters.append(AuditRecord.timestamp >= start_time)
    if end_time:
        filters.append(AuditRecord.timestamp <= end_time)

    if filters:
        query = query.where(and_(*filters))

    # Order by timestamp descending (most recent first)
    query = query.order_by(AuditRecord.timestamp.desc())

    # Pagination
    query = query.limit(limit).offset(offset)

    # Execute
    result = await db.execute(query)
    records = result.scalars().all()

    # Convert to response schema
    return [AuditRecordResponse(**record.to_dict()) for record in records]


@router.get("/audit/{record_id}", response_model=AuditRecordResponse)
async def get_audit_record(record_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single audit record by ID."""
    result = await db.execute(select(AuditRecord).where(AuditRecord.record_id == record_id))
    record = result.scalar_one_or_none()

    if not record:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Audit record not found")

    return AuditRecordResponse(**record.to_dict())
