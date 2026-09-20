"""
Ingestion API - Receives audit records from SDK.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import get_settings
from ...database import get_db
from ...models import AuditRecord, Customer
from ...rate_limit import limiter
from ...schemas import AuditRecordCreate
from ...services.auth import hash_api_key

router = APIRouter()
settings = get_settings()


async def verify_api_key(x_api_key: str = Header(...), db: AsyncSession = Depends(get_db)):
    """Verify API key (by its hash) and return customer."""
    result = await db.execute(
        select(Customer).where(Customer.api_key_hash == hash_api_key(x_api_key))
    )
    customer = result.scalar_one_or_none()

    if not customer or not customer.is_active:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return customer


@router.post("/ingest/audit", status_code=202)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def ingest_audit_records(
    request: Request,
    records: list[AuditRecordCreate],
    db: AsyncSession = Depends(get_db),
    customer: Customer = Depends(verify_api_key),
):
    """
    Ingest audit records from SDK.

    Accepts batch of audit records and writes them to the database.
    Returns 202 Accepted immediately (async processing).
    """
    # Validate customer_id matches API key
    for record in records:
        if record.customer_id and record.customer_id != customer.customer_id:
            raise HTTPException(status_code=403, detail="customer_id does not match API key")

    # Convert to ORM models
    audit_records = [
        AuditRecord(
            record_id=record.record_id,
            timestamp=record.timestamp,
            customer_id=record.customer_id or customer.customer_id,
            agent_id=record.agent_id,
            session_id=record.session_id,
            policy_version=record.policy_version,
            tool_name=record.tool_name,
            params=record.params,
            outcome=record.outcome,
            matched_rule=record.matched_rule,
            reason=record.reason,
            escalation_id=record.escalation_id,
            resolved_by=record.resolved_by,
            resolution=record.resolution,
            resolution_timestamp=record.resolution_timestamp,
            execution_result=record.execution_result,
            execution_error=record.execution_error,
            latency_ms=record.latency_ms,
        )
        for record in records
    ]

    # Bulk insert
    db.add_all(audit_records)
    await db.commit()

    # Broadcast to WebSocket connections
    from ...api.websocket import get_connection_manager

    manager = get_connection_manager()
    for record in records:
        await manager.broadcast_audit_record(customer.customer_id, record.dict())

    return {
        "status": "accepted",
        "records_received": len(records),
        "customer_id": customer.customer_id,
    }


@router.post("/ingest/events", status_code=202)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def ingest_observability_events(
    request: Request,
    events: list[dict],
    db: AsyncSession = Depends(get_db),
    customer: Customer = Depends(verify_api_key),
):
    """
    Ingest observability events from SDK.

    For Phase 2 - currently just accepts and logs events.
    """
    return {
        "status": "accepted",
        "events_received": len(events),
        "customer_id": customer.customer_id,
    }
