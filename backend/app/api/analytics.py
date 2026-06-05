"""Analytics endpoints powering the dashboard."""
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    AgentDecision, EmailEvent, Lead, ABTest, SequenceStep,
)
from app.redis_client import get_recent_activity
from app.schemas.analytics import (
    OverviewKPIs, WeeklyReplyRate, FunnelMetrics, ChannelMetrics,
    ABTestResult, AgentPerformance,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewKPIs)
async def overview(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Active leads
    active_total = (await db.execute(
        select(func.count(Lead.id)).where(Lead.state.notin_(["closed", "unsubscribed"]))
    )).scalar() or 0

    week_active = (await db.execute(
        select(func.count(Lead.id))
        .where(Lead.state.notin_(["closed", "unsubscribed"]))
        .where(Lead.created_at >= week_start)
    )).scalar() or 0
    prev_week_active = (await db.execute(
        select(func.count(Lead.id))
        .where(Lead.state.notin_(["closed", "unsubscribed"]))
        .where(Lead.created_at >= prev_week_start)
        .where(Lead.created_at < week_start)
    )).scalar() or 0
    delta = int(week_active) - int(prev_week_active)

    # Reply rate
    sent_week = (await db.execute(
        select(func.count(EmailEvent.id))
        .where(EmailEvent.event_type == "sent")
        .where(EmailEvent.occurred_at >= week_start)
    )).scalar() or 0
    replied_week = (await db.execute(
        select(func.count(EmailEvent.id))
        .where(EmailEvent.event_type == "replied")
        .where(EmailEvent.occurred_at >= week_start)
    )).scalar() or 0
    reply_rate_week = (replied_week / sent_week) if sent_week else 0.0

    sent_prev = (await db.execute(
        select(func.count(EmailEvent.id))
        .where(EmailEvent.event_type == "sent")
        .where(EmailEvent.occurred_at >= prev_week_start)
        .where(EmailEvent.occurred_at < week_start)
    )).scalar() or 0
    replied_prev = (await db.execute(
        select(func.count(EmailEvent.id))
        .where(EmailEvent.event_type == "replied")
        .where(EmailEvent.occurred_at >= prev_week_start)
        .where(EmailEvent.occurred_at < week_start)
    )).scalar() or 0
    reply_rate_prev = (replied_prev / sent_prev) if sent_prev else 0.0
    reply_rate_delta = round(reply_rate_week - reply_rate_prev, 4)

    # Today
    emails_today = (await db.execute(
        select(func.count(EmailEvent.id))
        .where(EmailEvent.event_type == "sent")
        .where(EmailEvent.occurred_at >= today_start)
    )).scalar() or 0
    decisions_today = (await db.execute(
        select(func.count(AgentDecision.id)).where(AgentDecision.created_at >= today_start)
    )).scalar() or 0

    return OverviewKPIs(
        total_active_leads=int(active_total),
        total_active_leads_delta=delta,
        reply_rate_week=round(reply_rate_week, 4),
        reply_rate_delta=reply_rate_delta,
        emails_sent_today=int(emails_today),
        decisions_made_today=int(decisions_today),
    )


@router.get("/reply-rate", response_model=list[WeeklyReplyRate])
async def reply_rate_weekly(weeks: int = 8, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    out: list[WeeklyReplyRate] = []
    for i in range(weeks - 1, -1, -1):
        week_end = now - timedelta(days=7 * i)
        week_start = week_end - timedelta(days=7)
        sent = (await db.execute(
            select(func.count(EmailEvent.id))
            .where(EmailEvent.event_type == "sent")
            .where(and_(EmailEvent.occurred_at >= week_start, EmailEvent.occurred_at < week_end))
        )).scalar() or 0
        replied = (await db.execute(
            select(func.count(EmailEvent.id))
            .where(EmailEvent.event_type == "replied")
            .where(and_(EmailEvent.occurred_at >= week_start, EmailEvent.occurred_at < week_end))
        )).scalar() or 0
        rate = (replied / sent) if sent else 0.0
        out.append(WeeklyReplyRate(
            week_label=f"Week of {week_start.date().isoformat()}",
            week_start=week_start,
            sent=int(sent),
            replied=int(replied),
            reply_rate=round(rate, 4),
        ))
    return out


@router.get("/funnel", response_model=FunnelMetrics)
async def funnel(db: AsyncSession = Depends(get_db)):
    counts: dict[str, int] = {}
    for evt in ("sent", "delivered", "opened", "clicked", "replied"):
        c = (await db.execute(
            select(func.count(EmailEvent.id)).where(EmailEvent.event_type == evt)
        )).scalar() or 0
        counts[evt] = int(c)
    # Delivered defaults to sent if no explicit delivered events
    if counts["delivered"] == 0:
        counts["delivered"] = counts["sent"]
    return FunnelMetrics(**counts)


@router.get("/channels", response_model=list[ChannelMetrics])
async def channels(db: AsyncSession = Depends(get_db)):
    out = []
    for ch in ("email", "linkedin", "phone"):
        sent = (await db.execute(
            select(func.count(EmailEvent.id))
            .where(EmailEvent.channel == ch)
            .where(EmailEvent.event_type.in_(["sent", "opened"]))
        )).scalar() or 0
        replied = (await db.execute(
            select(func.count(EmailEvent.id))
            .where(EmailEvent.channel == ch)
            .where(EmailEvent.event_type == "replied")
        )).scalar() or 0
        rate = (replied / sent) if sent else 0.0
        out.append(ChannelMetrics(channel=ch, sent=int(sent), engagement_rate=round(rate, 4)))
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
    breakdown_rows = (await db.execute(
        select(AgentDecision.decision_type, func.count(AgentDecision.id))
        .group_by(AgentDecision.decision_type)
    )).all()
    breakdown = {r[0]: int(r[1]) for r in breakdown_rows}

    avg_conf = float((await db.execute(
        select(func.avg(AgentDecision.confidence_score))
    )).scalar() or 0.0)

    total = (await db.execute(select(func.count(AgentDecision.id)))).scalar() or 0
    overrides = (await db.execute(
        select(func.count(AgentDecision.id)).where(AgentDecision.approved_by == "human_override")
    )).scalar() or 0
    override_rate = (overrides / total) if total else 0.0

    # Daily confidence trend (last 14 days)
    now = datetime.now(timezone.utc)
    trend = []
    for i in range(13, -1, -1):
        day_end = now - timedelta(days=i)
        day_start = day_end - timedelta(days=1)
        avg = (await db.execute(
            select(func.avg(AgentDecision.confidence_score))
            .where(AgentDecision.created_at >= day_start)
            .where(AgentDecision.created_at < day_end)
        )).scalar()
        trend.append({
            "date": day_start.date().isoformat(),
            "avg_confidence": round(float(avg or 0.0), 3),
        })

    return AgentPerformance(
        decision_breakdown=breakdown,
        avg_confidence=round(avg_conf, 3),
        avg_confidence_trend=trend,
        human_override_rate=round(override_rate, 4),
        total_decisions=int(total),
    )


@router.get("/activity-feed")
async def activity_feed(limit: int = 50) -> list[dict[str, Any]]:
    """Live activity feed pulled from Redis."""
    return await get_recent_activity(limit)
