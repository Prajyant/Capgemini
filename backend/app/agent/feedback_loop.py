"""
Feedback loop — updates prompt strategy reply rates based on observed engagement.

Runs as a periodic Celery task. Every email event refines the agent's understanding
of which patterns work for which segments. This is the self-improving layer.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PromptStrategy, EmailEvent, Lead, Company

logger = logging.getLogger(__name__)


async def update_strategy_metrics(
    db: AsyncSession,
    window_days: int = 30,
) -> dict:
    """
    Re-compute avg_reply_rate for each strategy based on recent email events.

    A strategy is matched to events via vertical (industry) + seniority_level.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    strategies = (await db.execute(select(PromptStrategy))).scalars().all()
    updated = 0

    for strategy in strategies:
        # Count sent and replied events for leads matching this segment
        sent_query = (
            select(func.count(EmailEvent.id))
            .join(Lead, Lead.id == EmailEvent.lead_id)
            .outerjoin(Company, Company.id == Lead.company_id)
            .where(EmailEvent.event_type == "sent")
            .where(EmailEvent.occurred_at >= cutoff)
        )
        replied_query = (
            select(func.count(EmailEvent.id))
            .join(Lead, Lead.id == EmailEvent.lead_id)
            .outerjoin(Company, Company.id == Lead.company_id)
            .where(EmailEvent.event_type == "replied")
            .where(EmailEvent.occurred_at >= cutoff)
        )
        if strategy.vertical:
            sent_query = sent_query.where(Company.industry == strategy.vertical)
            replied_query = replied_query.where(Company.industry == strategy.vertical)
        if strategy.seniority_level:
            sent_query = sent_query.where(Lead.seniority_level == strategy.seniority_level)
            replied_query = replied_query.where(Lead.seniority_level == strategy.seniority_level)

        sent_count = (await db.execute(sent_query)).scalar() or 0
        replied_count = (await db.execute(replied_query)).scalar() or 0

        if sent_count > 0:
            new_rate = replied_count / sent_count
            strategy.avg_reply_rate = round(new_rate, 4)
            strategy.sample_size = sent_count
            updated += 1

    await db.flush()
    logger.info("Updated %d prompt strategies", updated)
    return {"updated": updated}
