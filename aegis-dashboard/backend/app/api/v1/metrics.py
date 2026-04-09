"""
Metrics API - Dashboard statistics and aggregations.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, case, literal_column, text
from typing import Optional
from datetime import datetime, timedelta

from ...database import get_db
from ...models import AuditRecord

router = APIRouter()


INTERVAL_TRUNC_MAP = {
    "1m": "minute",
    "5m": "minute",
    "15m": "minute",
    "1h": "hour",
}

INTERVAL_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
}


def _floor_timestamp(col, interval: str):
    """Build a SQL expression that floors a timestamp to the given interval bucket."""
    trunc_unit = INTERVAL_TRUNC_MAP.get(interval, "minute")
    if interval in ("1m", "1h"):
        return func.date_trunc(trunc_unit, col)
    secs = INTERVAL_SECONDS.get(interval, 60)
    epoch = func.extract("epoch", col)
    floored_epoch = func.floor(epoch / secs) * secs
    return func.to_timestamp(floored_epoch)


@router.get("/metrics/timeseries")
async def get_metrics_timeseries(
    customer_id: str = Query(...),
    start: Optional[str] = Query(None, description="ISO datetime start"),
    end: Optional[str] = Query(None, description="ISO datetime end"),
    interval: str = Query("1m", description="Bucket interval: 1m, 5m, 15m, 1h"),
    agent_id: Optional[str] = Query(None),
    tool_name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Return time-bucketed metrics for charting.

    Each bucket contains counts by outcome and latency percentiles.
    """
    if interval not in INTERVAL_SECONDS:
        interval = "1m"

    now = datetime.utcnow()
    start_time = datetime.fromisoformat(start) if start else now - timedelta(hours=1)
    end_time = datetime.fromisoformat(end) if end else now

    bucket = _floor_timestamp(AuditRecord.timestamp, interval).label("bucket")

    filters = [
        AuditRecord.customer_id == customer_id,
        AuditRecord.timestamp >= start_time,
        AuditRecord.timestamp <= end_time,
    ]
    if agent_id:
        filters.append(AuditRecord.agent_id == agent_id)
    if tool_name:
        filters.append(AuditRecord.tool_name == tool_name)

    query = (
        select(
            bucket,
            func.count().label("total"),
            func.sum(case((AuditRecord.outcome == "allow", 1), else_=0)).label("allows"),
            func.sum(case((AuditRecord.outcome == "deny", 1), else_=0)).label("denies"),
            func.sum(case((AuditRecord.outcome == "escalate", 1), else_=0)).label("escalations"),
            func.coalesce(func.avg(AuditRecord.latency_ms), 0).label("avg_latency"),
            func.coalesce(
                func.percentile_cont(0.95).within_group(AuditRecord.latency_ms), 0
            ).label("p95_latency"),
            func.coalesce(
                func.percentile_cont(0.99).within_group(AuditRecord.latency_ms), 0
            ).label("p99_latency"),
        )
        .where(and_(*filters))
        .group_by(bucket)
        .order_by(bucket)
    )

    result = await db.execute(query)
    rows = result.fetchall()

    buckets = []
    for row in rows:
        buckets.append({
            "time": row.bucket.isoformat() if row.bucket else None,
            "total": row.total,
            "allows": row.allows,
            "denies": row.denies,
            "escalations": row.escalations,
            "avg_latency": round(float(row.avg_latency), 2),
            "p95_latency": round(float(row.p95_latency), 2),
            "p99_latency": round(float(row.p99_latency), 2),
        })

    return {
        "interval": interval,
        "buckets": buckets,
    }


@router.get("/metrics/explore")
async def get_metrics_explore(
    customer_id: str = Query(...),
    start: str = Query(..., description="ISO datetime start"),
    end: str = Query(..., description="ISO datetime end"),
    outcome: Optional[str] = Query(None, description="Filter by outcome: allow, deny, escalate"),
    agent_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Return detailed breakdown for a specific time window.

    Used by the /explore drill-down page. Returns:
    - Window summary (counts + latency)
    - Per-agent breakdown
    - Per-tool breakdown
    """
    start_time = datetime.fromisoformat(start.replace("Z", "+00:00")).replace(tzinfo=None)
    end_time = datetime.fromisoformat(end.replace("Z", "+00:00")).replace(tzinfo=None)

    base_filters = [
        AuditRecord.customer_id == customer_id,
        AuditRecord.timestamp >= start_time,
        AuditRecord.timestamp <= end_time,
    ]
    if outcome:
        base_filters.append(AuditRecord.outcome == outcome)
    if agent_id:
        base_filters.append(AuditRecord.agent_id == agent_id)

    # --- Window summary ---
    summary_query = select(
        func.count().label("total"),
        func.sum(case((AuditRecord.outcome == "allow", 1), else_=0)).label("allows"),
        func.sum(case((AuditRecord.outcome == "deny", 1), else_=0)).label("denies"),
        func.sum(case((AuditRecord.outcome == "escalate", 1), else_=0)).label("escalations"),
        func.coalesce(func.avg(AuditRecord.latency_ms), 0).label("avg_latency"),
        func.coalesce(
            func.percentile_cont(0.95).within_group(AuditRecord.latency_ms), 0
        ).label("p95_latency"),
        func.coalesce(
            func.percentile_cont(0.99).within_group(AuditRecord.latency_ms), 0
        ).label("p99_latency"),
    ).where(and_(*base_filters))

    summary_result = await db.execute(summary_query)
    s = summary_result.fetchone()

    summary = {
        "total": s.total or 0,
        "allows": s.allows or 0,
        "denies": s.denies or 0,
        "escalations": s.escalations or 0,
        "avg_latency": round(float(s.avg_latency), 2),
        "p95_latency": round(float(s.p95_latency), 2),
        "p99_latency": round(float(s.p99_latency), 2),
    }

    # --- Per-agent breakdown ---
    agent_query = (
        select(
            AuditRecord.agent_id,
            func.count().label("total"),
            func.sum(case((AuditRecord.outcome == "allow", 1), else_=0)).label("allows"),
            func.sum(case((AuditRecord.outcome == "deny", 1), else_=0)).label("denies"),
            func.sum(case((AuditRecord.outcome == "escalate", 1), else_=0)).label("escalations"),
            func.coalesce(func.avg(AuditRecord.latency_ms), 0).label("avg_latency"),
        )
        .where(and_(*base_filters))
        .group_by(AuditRecord.agent_id)
        .order_by(desc("total"))
    )
    agent_result = await db.execute(agent_query)
    agents = [
        {
            "agent_id": row.agent_id,
            "total": row.total,
            "allows": row.allows,
            "denies": row.denies,
            "escalations": row.escalations,
            "deny_rate": round(row.denies / row.total, 3) if row.total > 0 else 0,
            "avg_latency": round(float(row.avg_latency), 2),
        }
        for row in agent_result.fetchall()
    ]

    # --- Per-tool breakdown ---
    tool_query = (
        select(
            AuditRecord.tool_name,
            func.count().label("total"),
            func.sum(case((AuditRecord.outcome == "allow", 1), else_=0)).label("allows"),
            func.sum(case((AuditRecord.outcome == "deny", 1), else_=0)).label("denies"),
            func.sum(case((AuditRecord.outcome == "escalate", 1), else_=0)).label("escalations"),
            func.coalesce(func.avg(AuditRecord.latency_ms), 0).label("avg_latency"),
        )
        .where(and_(*base_filters))
        .group_by(AuditRecord.tool_name)
        .order_by(desc("total"))
    )
    tool_result = await db.execute(tool_query)
    tools = [
        {
            "tool_name": row.tool_name,
            "total": row.total,
            "allows": row.allows,
            "denies": row.denies,
            "escalations": row.escalations,
            "deny_rate": round(row.denies / row.total, 3) if row.total > 0 else 0,
            "avg_latency": round(float(row.avg_latency), 2),
        }
        for row in tool_result.fetchall()
    ]

    return {
        "window": {"start": start, "end": end, "outcome_filter": outcome},
        "summary": summary,
        "agents": agents,
        "tools": tools,
    }


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
                case((AuditRecord.outcome == "deny", 1), else_=0)
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
