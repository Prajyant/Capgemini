"""A/B test winner selection."""
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ABTest


async def decide_winners(db: AsyncSession) -> int:
    """Mark winners for tests past their observation window. Returns count decided."""
    now = datetime.now(timezone.utc)
    stmt = select(ABTest).where(ABTest.winner.is_(None))
    tests = (await db.execute(stmt)).scalars().all()
    decided = 0

    for t in tests:
        if not t.created_at:
            continue
        window_end = t.created_at + timedelta(hours=t.observation_window_hours)
        if window_end > now:
            continue

        a_score = t.variant_a_replies * 3 + t.variant_a_opens
        b_score = t.variant_b_replies * 3 + t.variant_b_opens

        if a_score == 0 and b_score == 0:
            continue

        if a_score > b_score:
            t.winner = "A"
        elif b_score > a_score:
            t.winner = "B"
        else:
            continue

        t.decided_at = now
        decided += 1

    await db.flush()
    return decided
