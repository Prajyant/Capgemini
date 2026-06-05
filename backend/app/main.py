"""FastAPI application entry point."""
import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse

from app.api import agent, analytics, auth, leads, sequences, webhooks
from app.config import settings
from app.database import init_db
from app.redis_client import get_redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SalesAgent AI backend...")
    try:
        await init_db()
        logger.info("Database initialised")
    except Exception as e:
        logger.exception("DB init failed: %s", e)
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="SalesAgent AI",
    description="Autonomous reasoning agent for B2B sales outreach",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — open in dev, tighten in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(leads.router)
app.include_router(agent.router)
app.include_router(sequences.router)
app.include_router(webhooks.router)
app.include_router(analytics.router)


@app.get("/")
async def root():
    return {
        "service": "SalesAgent AI",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/stream/activity")
async def stream_activity(request: Request):
    """Server-Sent Events stream of live agent activity."""
    redis = get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe("agent.decisions", "leads.enriched", "email.events", "email.replies")

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
                if msg and msg.get("type") == "message":
                    data = msg.get("data", "{}")
                    if isinstance(data, bytes):
                        data = data.decode()
                    yield f"data: {data}\n\n"
                else:
                    # heartbeat
                    yield ": ping\n\n"
                await asyncio.sleep(0.05)
        finally:
            await pubsub.unsubscribe()
            await pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/unsubscribe/{lead_id}", response_class=HTMLResponse)
async def unsubscribe(lead_id: str):
    """One-click unsubscribe per CAN-SPAM. Marks the lead opted_out."""
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.database import get_db_context
    from app.models import Lead

    try:
        async with get_db_context() as db:
            lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
            if lead:
                lead.opted_out = True
                lead.opted_out_at = datetime.now(timezone.utc)
                lead.state = "unsubscribed"
                lead.state_updated_at = datetime.now(timezone.utc)
                await db.flush()
    except Exception as e:
        logger.exception("Unsubscribe failed: %s", e)

    return HTMLResponse(
        "<html><body style='font-family:sans-serif;padding:40px;text-align:center;'>"
        "<h2>You've been unsubscribed</h2>"
        "<p>You will no longer receive emails from us.</p>"
        "</body></html>"
    )
