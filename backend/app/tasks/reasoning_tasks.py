"""Reasoning-related Celery tasks."""
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, or_

from app.agent.decision_maker import reason_for_lead
from app.database import get_db_context
from app.models import Lead
from app.tasks.celery_app import celery_app
from app.tasks.loop_helper import run_async

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.reasoning_tasks.reason_for_lead_task")
def reason_for_lead_task(lead_id: str, auto_execute: bool = False) -> dict:
    """Run reasoning for a single lead in the background."""
    return run_async(_run(lead_id, auto_execute))


async def _run(lead_id: str, auto_execute: bool) -> dict:
    async with get_db_context() as db:
        decision = await reason_for_lead(db, UUID(lead_id), auto_execute=auto_execute)
        return {
            "decision_id": str(decision.id),
            "decision_type": decision.decision_type,
            "confidence": float(decision.confidence_score),
            "summary": decision.reasoning_summary,
        }


@celery_app.task(name="app.tasks.reasoning_tasks.process_due_leads")
def process_due_leads() -> dict:
    """Find leads whose next_action_at has passed and reason about them."""
    return run_async(_process_due())


async def _process_due() -> dict:
    async with get_db_context() as db:
        now = datetime.now(timezone.utc)
        stmt = (
            select(Lead)
            .where(Lead.opted_out == False)  # noqa: E712
            .where(Lead.state.in_(["enriched", "contacted", "engaged", "cold"]))
            .where(or_(Lead.next_action_at == None, Lead.next_action_at <= now))  # noqa: E711
            .limit(50)
        )
        leads = (await db.execute(stmt)).scalars().all()
        processed = 0
        for lead in leads:
            try:
                await reason_for_lead(db, lead.id, auto_execute=False)
                processed += 1
            except Exception as e:
                logger.exception("Failed reasoning for lead %s: %s", lead.id, e)
        logger.info("Processed %d due leads", processed)
        return {"processed": processed}
