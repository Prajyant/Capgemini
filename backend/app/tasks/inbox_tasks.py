"""Celery tasks for IMAP inbox polling."""
import logging

from app.tasks.celery_app import celery_app
from app.tasks.loop_helper import run_async

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.inbox_tasks.poll_inbox")
def poll_inbox() -> dict:
    """Poll the configured IMAP inbox for new replies and process them."""
    from app.inbox.imap_reader import process_inbox_replies
    result = run_async(process_inbox_replies())
    logger.info("Inbox poll result: %s", result)
    return result
