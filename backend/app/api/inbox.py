"""API endpoint to trigger inbox polling manually."""
from fastapi import APIRouter

from app.tasks.inbox_tasks import poll_inbox

router = APIRouter(prefix="/api/inbox", tags=["inbox"])


@router.post("/poll")
async def trigger_inbox_poll():
    """Manually trigger an inbox poll. Also runs automatically every 2 minutes via Celery Beat."""
    task = poll_inbox.delay()
    return {"status": "polling", "task_id": str(task.id)}


@router.get("/status")
async def inbox_status():
    """Check if IMAP is configured."""
    from app.config import settings
    return {
        "configured": bool(settings.IMAP_HOST and settings.IMAP_USER and settings.IMAP_PASSWORD),
        "host": settings.IMAP_HOST or None,
        "user": settings.IMAP_USER or None,
    }
