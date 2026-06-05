"""Async enrichment Celery tasks."""
import logging
from uuid import UUID

from app.database import get_db_context
from app.enrichment.enrichment_agent import enrich_lead
from app.tasks.celery_app import celery_app
from app.tasks.loop_helper import run_async

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.enrichment_tasks.enrich_lead_task", bind=True, max_retries=3)
def enrich_lead_task(self, lead_id: str):
    """Enrich a single lead. Retries on transient failures."""
    try:
        return run_async(_run_enrich(lead_id))
    except Exception as exc:
        logger.exception("Enrichment failed for %s", lead_id)
        raise self.retry(exc=exc, countdown=30)


async def _run_enrich(lead_id: str) -> dict:
    async with get_db_context() as db:
        return await enrich_lead(db, UUID(lead_id))
