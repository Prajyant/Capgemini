"""
Prompt strategy manager — selects the best subject/body pattern based on
historical performance for a given vertical + seniority + hook type combo.
"""
import logging
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PromptStrategy

logger = logging.getLogger(__name__)


async def best_strategy_for(
    db: AsyncSession,
    vertical: Optional[str],
    seniority: Optional[str],
) -> Optional[PromptStrategy]:
    """Return the active strategy with the highest reply rate for this segment."""
    stmt = (
        select(PromptStrategy)
        .where(PromptStrategy.is_active == True)  # noqa: E712
        .order_by(desc(PromptStrategy.avg_reply_rate))
    )
    if vertical:
        stmt = stmt.where(PromptStrategy.vertical == vertical)
    if seniority:
        stmt = stmt.where(PromptStrategy.seniority_level == seniority)

    result = await db.execute(stmt.limit(1))
    return result.scalar_one_or_none()


async def list_top_strategies(db: AsyncSession, limit: int = 10) -> list[PromptStrategy]:
    stmt = (
        select(PromptStrategy)
        .where(PromptStrategy.is_active == True)  # noqa: E712
        .order_by(desc(PromptStrategy.avg_reply_rate))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
