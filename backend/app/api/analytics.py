"""
Analytics endpoints powering the dashboard.

These endpoints used to issue dozens of small sequential `COUNT(*)` queries
per request (8+ for `/overview`, 16 for `/reply-rate`, 14+ for
`/agent-performance`). Each round-trip to Postgres added latency that the
dashboard hit several times per page load. They've been rewritten to use
single grouped queries where possible and Python-side bucketing for time
series, which is the dominant reason the dashboard now loads quickly.
"""
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    ABTest,
    AgentDecision,
    EmailEvent,
    Lead,
)
from app.redis_client import get_recent_activity
from app.schemas.analytics import (
    ABTestResult,
    AgentPerformance,
    ChannelMetrics,
    FunnelMetrics,
    OverviewKPIs,
    WeeklyReplyRate,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewKPIs)
async def overview(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # All email-event counters in a single grouped query.
    email_row = (await db.execute(
        select(
            func.count(EmailEvent.id).filter(
                EmailEvent.event_type == "sent",
                EmailEvent.occurred_at >= week_start,
            ).label("sent_week"),
            func.count(EmailEvent.id).filter(
                EmailEvent.event_type == "sent",
                EmailEvent.occurred_at >= prev_week_start,
                EmailEvent.occurred_at < week_start,
            ).label("sent_prev"),
            func.count(EmailEvent.id).filter(
                EmailEvent.event_type == "replied",
                EmailEvent.occurred_at >= week_start,
            ).label("replied_week"),
            func.count(EmailEvent.id).filter(
                EmailEvent.event_type == "replied",
                EmailEvent.occurred_at >= prev_week_start,
                EmailEvent.occurred_at < week_start,
            ).label("replied_prev"),
            func.count(EmailEvent.id).filter(
                EmailEvent.event_type == "sent",
                EmailEvent.occurred_at >= today_start,
            ).label("emails_today"),
        ).select_from(EmailEvent)
    )).one()

    # All lead-state counters in a single grouped query.
    excluded_states = ("closed", "unsubscribed")
    lead_row = (await db.execute(
        select(
            func.count(Lead.id).filter(
                Lead.state.notin_(excluded_states)
            ).label("active_total"),
            func.count(Lead.id).filter(
                Lead.state.notin_(excluded_states),
                Lead.created_at >= week_start,
            ).label("active_week"),
            func.count(Lead.id).filter(
                Lead.state.notin_(excluded_states),
                Lead.created_at >= prev_week_start,
                Lead.created_at < week_start,
            ).label("active_prev"),
        ).select_from(Lead)
    )).one()

    decisions_today = (await db.execute(
        select(func.count(AgentDecision.id)).where(
            AgentDecision.created_at >= today_start
        )
    )).scalar() or 0

    sent_week = int(email_row.sent_week or 0)
    sent_prev = int(email_row.sent_prev or 0)
    replied_week = int(email_row.replied_week or 0)
    replied_prev = int(email_row.replied_prev or 0)

    reply_rate_week = (replied_week / sent_week) if sent_week else 0.0
    reply_rate_prev = (replied_prev / sent_prev) if sent_prev else 0.0

    return OverviewKPIs(
        total_active_leads=int(lead_row.active_total or 0),
        total_active_leads_delta=int((lead_row.active_week or 0) - (lead_row.active_prev or 0)),
        reply_rate_week=round(reply_rate_week, 4),
        reply_rate_delta=round(reply_rate_week - reply_rate_prev, 4),
        emails_sent_today=int(email_row.emails_today or 0),
        decisions_made_today=int(decisions_today),
    )


@router.get("/reply-rate", response_model=list[WeeklyReplyRate])
async def reply_rate_weekly(weeks: int = 8, db: AsyncSession = Depends(get_db)):
    """
    Reply-rate trend by week.

    Old impl issued 2 COUNT queries per week (16 for the default 8 weeks).
    New impl issues a single query for the full window, then buckets in
    Python — 16x fewer round-trips and the bucketing is cheap.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7 * weeks)

    rows = (await db.execute(
        select(EmailEvent.event_type, EmailEvent.occurred_at)
        .where(EmailEvent.occurred_at >= start)
        .where(EmailEvent.event_type.in_(["sent", "replied"]))
    )).all()

    out: list[WeeklyReplyRate] = []
    for i in range(weeks - 1, -1, -1):
        week_end = now - timedelta(days=7 * i)
        week_start = week_end - timedelta(days=7)
        sent = 0
        replied = 0
        for r in rows:
            ts = r.occurred_at
            if ts is None or ts < week_start or ts >= week_end:
                continue
            if r.event_type == "sent":
                sent += 1
            elif r.event_type == "replied":
                replied += 1
        rate = (replied / sent) if sent else 0.0
        out.append(WeeklyReplyRate(
            week_label=f"Week of {week_start.date().isoformat()}",
            week_start=week_start,
            sent=sent,
            replied=replied,
            reply_rate=round(rate, 4),
        ))
    return out


@router.get("/funnel", response_model=FunnelMetrics)
async def funnel(db: AsyncSession = Depends(get_db)):
    """Single GROUP BY replaces five sequential count queries."""
    rows = (await db.execute(
        select(EmailEvent.event_type, func.count(EmailEvent.id))
        .where(EmailEvent.event_type.in_(["sent", "delivered", "opened", "clicked", "replied"]))
        .group_by(EmailEvent.event_type)
    )).all()
    counts = {r[0]: int(r[1]) for r in rows}
    if not counts.get("delivered"):
        counts["delivered"] = counts.get("sent", 0)
    return FunnelMetrics(
        sent=counts.get("sent", 0),
        delivered=counts.get("delivered", 0),
        opened=counts.get("opened", 0),
        clicked=counts.get("clicked", 0),
        replied=counts.get("replied", 0),
    )


@router.get("/channels", response_model=list[ChannelMetrics])
async def channels(db: AsyncSession = Depends(get_db)):
    """Single grouped query per channel × bucket replaces 6 sequential queries."""
    rows = (await db.execute(
        select(
            EmailEvent.channel,
            func.count(EmailEvent.id).filter(
                EmailEvent.event_type.in_(["sent", "opened"])
            ).label("sent"),
            func.count(EmailEvent.id).filter(
                EmailEvent.event_type == "replied"
            ).label("replied"),
        )
        .where(EmailEvent.channel.in_(["email", "linkedin", "phone"]))
        .group_by(EmailEvent.channel)
    )).all()

    by_channel = {
        r.channel: (int(r.sent or 0), int(r.replied or 0))
        for r in rows
    }
    out: list[ChannelMetrics] = []
    for ch in ("email", "linkedin", "phone"):
        sent, replied = by_channel.get(ch, (0, 0))
        rate = (replied / sent) if sent else 0.0
        out.append(ChannelMetrics(
            channel=ch,
            sent=sent,
            engagement_rate=round(rate, 4),
        ))
    return out


@router.get("/ab-tests", response_model=list[ABTestResult])
async def ab_tests(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(ABTest).order_by(desc(ABTest.created_at)).limit(20)
    )).scalars().all()
    out: list[ABTestResult] = []
    for t in rows:
        a_sent = max(t.variant_a_opens, 1)
        b_sent = max(t.variant_b_opens, 1)
        out.append(ABTestResult(
            sequence_step=str(t.sequence_step_id) if t.sequence_step_id else "step",
            variant_a_subject=t.variant_a_subject or "",
            variant_b_subject=t.variant_b_subject or "",
            variant_a_open_rate=round(t.variant_a_opens / max(t.variant_a_opens + t.variant_a_replies, 1), 4),
            variant_b_open_rate=round(t.variant_b_opens / max(t.variant_b_opens + t.variant_b_replies, 1), 4),
            variant_a_reply_rate=round(t.variant_a_replies / a_sent, 4),
            variant_b_reply_rate=round(t.variant_b_replies / b_sent, 4),
            winner=t.winner,
        ))
    return out


@router.get("/agent-performance", response_model=AgentPerformance)
async def agent_performance(db: AsyncSession = Depends(get_db)):
    """
    Agent KPI summary.

    Old impl issued 14 sequential queries for the daily confidence trend
    plus the breakdown / total / overrides queries. New impl uses 4
    grouped queries and buckets the trend in Python.
    """
    breakdown_rows = (await db.execute(
        select(AgentDecision.decision_type, func.count(AgentDecision.id))
        .group_by(AgentDecision.decision_type)
    )).all()
    breakdown = {r[0]: int(r[1]) for r in breakdown_rows}

    summary_row = (await db.execute(
        select(
            func.coalesce(func.avg(AgentDecision.confidence_score), 0.0).label("avg_conf"),
            func.count(AgentDecision.id).label("total"),
            func.count(AgentDecision.id).filter(
                AgentDecision.approved_by == "human_override"
            ).label("overrides"),
        ).select_from(AgentDecision)
    )).one()
    avg_conf = float(summary_row.avg_conf or 0.0)
    total = int(summary_row.total or 0)
    overrides = int(summary_row.overrides or 0)
    override_rate = (overrides / total) if total else 0.0

    # Daily confidence trend in one query, bucketed in Python.
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=14)
    rows = (await db.execute(
        select(AgentDecision.created_at, AgentDecision.confidence_score)
        .where(AgentDecision.created_at >= window_start)
    )).all()

    trend: list[dict[str, Any]] = []
    for i in range(13, -1, -1):
        day_end = now - timedelta(days=i)
        day_start = day_end - timedelta(days=1)
        same_day = [
            float(r.confidence_score or 0.0)
            for r in rows
            if r.created_at and day_start <= r.created_at < day_end
        ]
        avg = sum(same_day) / len(same_day) if same_day else 0.0
        trend.append({
            "date": day_start.date().isoformat(),
            "avg_confidence": round(avg, 3),
        })

    return AgentPerformance(
        decision_breakdown=breakdown,
        avg_confidence=round(avg_conf, 3),
        avg_confidence_trend=trend,
        human_override_rate=round(override_rate, 4),
        total_decisions=total,
    )


@router.get("/activity-feed")
async def activity_feed(limit: int = 50) -> list[dict[str, Any]]:
    """Live activity feed pulled from Redis."""
    return await get_recent_activity(limit)
