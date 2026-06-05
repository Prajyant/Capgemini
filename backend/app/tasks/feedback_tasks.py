"""Feedback / self-improvement tasks."""
import logging

from app.agent.feedback_loop import update_strategy_metrics
from app.database import get_db_context
from app.outreach.ab_testing import decide_winners
from app.tasks.celery_app import celery_app
from app.tasks.loop_helper import run_async

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.feedback_tasks.refresh_strategy_metrics")
def refresh_strategy_metrics() -> dict:
    return run_async(_refresh())


async def _refresh() -> dict:
    async with get_db_context() as db:
        return await update_strategy_metrics(db)


@celery_app.task(name="app.tasks.feedback_tasks.decide_ab_winners")
def decide_ab_winners() -> dict:
    return run_async(_decide())


async def _decide() -> dict:
    async with get_db_context() as db:
        decided = await decide_winners(db)
        return {"decided": decided}
