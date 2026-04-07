"""
Metrics API - Dashboard statistics and aggregations.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import Optional
from datetime import datetime, timedelta

from ...database import get_db
from ...models import AuditRecord

router = APIRouter()


@router.get("/metrics/summary")
async def get_metrics_summary(
    customer_id: str = Query(...),
    period: str = Query("7d", description="Time period: 1d, 7d, 30d"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get summary metrics for dashboard overview.

    Returns counts by outcome, top tools, top denied rules, and latency percentiles.
    """
    # Parse period
    period_map = {"1d": 1, "7d": 7, "30d": 30}
    days = period_map.get(period, 7)
    start_time = datetime.utcnow() - timedelta(days=days)

    # Total calls
    total_query = select(func.count(AuditRecord.record_id)).where(
        and_(
            AuditRecord.customer_id == customer_id, AuditRecord.timestamp >= start_time
        )
    )
    total_result = await db.execute(total_query)
    total_calls = total_result.scalar() or 0

    # Counts by outcome
    outcome_query = (
        select(AuditRecord.outcome, func.count(AuditRecord.record_id))
        .where(
            and_(
                AuditRecord.customer_id == customer_id,
                AuditRecord.timestamp >= start_time,
            )
        )
        .group_by(AuditRecord.outcome)
    )
    outcome_result = await db.execute(outcome_query)
    outcomes = {row[0]: row[1] for row in outcome_result.fetchall()}

    # Top tools
    tool_query = (
        select(
            AuditRecord.tool_name,
            func.count(AuditRecord.record_id).label("count"),
            func.sum(
                func.cast(AuditRecord.outcome == "deny", func.INTEGER)
            ).label("denies"),
        )
        .where(
            and_(
                AuditRecord.customer_id == customer_id,
                AuditRecord.timestamp >= start_time,
            )
        )
        .group_by(AuditRecord.tool_name)
        .order_by(desc("count"))
        .limit(10)
    )
    tool_result = await db.execute(tool_query)
    top_tools = [
        {
            "tool": row[0],
            "count": row[1],
            "deny_rate": round(row[2] / row[1], 3) if row[1] > 0 else 0,
        }
        for row in tool_result.fetchall()
    ]

    # Top denied rules
    denied_query = (
        select(AuditRecord.matched_rule, func.count(AuditRecord.record_id))
        .where(
            and_(
                AuditRecord.customer_id == customer_id,
                AuditRecord.timestamp >= start_time,
                AuditRecord.outcome == "deny",
            )
        )
        .group_by(AuditRecord.matched_rule)
        .order_by(desc(func.count(AuditRecord.record_id)))
        .limit(10)
    )
    denied_result = await db.execute(denied_query)
    top_denied_rules = [
        {"rule": row[0], "count": row[1]} for row in denied_result.fetchall()
    ]

    # Latency percentiles (simplified - would use percentile_cont in production)
    latency_query = select(
        func.avg(AuditRecord.latency_ms),
        func.max(AuditRecord.latency_ms),
    ).where(
        and_(
            AuditRecord.customer_id == customer_id,
            AuditRecord.timestamp >= start_time,
            AuditRecord.latency_ms.isnot(None),
        )
    )
    latency_result = await db.execute(latency_query)
    avg_latency, max_latency = latency_result.fetchone()

    return {
        "total_calls": total_calls,
        "allows": outcomes.get("allow", 0),
        "denies": outcomes.get("deny", 0),
        "escalations": outcomes.get("escalate", 0),
        "top_tools": top_tools,
        "top_denied_rules": top_denied_rules,
        "latency": {
            "avg": round(avg_latency, 2) if avg_latency else 0,
            "max": round(max_latency, 2) if max_latency else 0,
        },
    }
