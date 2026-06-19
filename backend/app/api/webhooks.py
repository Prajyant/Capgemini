"""SendGrid webhook receiver + inbound reply handler."""
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.enrichment.enrichment_agent import recompute_intent_for_lead
from app.models import EmailEvent, Lead
from app.nlp.reply_classifier import classify_reply
from app.redis_client import publish_event, push_activity

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


# SendGrid event names → our internal event types
_EVENT_MAP = {
    "delivered": "delivered",
    "open": "opened",
    "click": "clicked",
    "bounce": "bounced",
    "spamreport": "spam",
    "unsubscribe": "unsubscribed",
    "dropped": "bounced",
    "deferred": "deferred",
    "processed": "processed",
}

# Buyer-side actions that should refresh the buying-intent score
_INTENT_REFRESH_EVENTS = {"opened", "clicked", "replied", "bounced", "unsubscribed"}


@router.post("/sendgrid")
async def sendgrid_events(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive SendGrid event webhook payload (array of events)."""
    payload: list[dict[str, Any]] = await request.json()
    if not isinstance(payload, list):
        payload = [payload]

    processed = 0
    affected_leads: dict[UUID, Lead] = {}
    needs_intent_refresh: set[UUID] = set()

    for evt in payload:
        sg_event = evt.get("event")
        message_id = evt.get("sg_message_id") or evt.get("smtp-id")
        to_email = evt.get("email")
        clicked_url = evt.get("url")

        if not to_email:
            continue

        lead = (await db.execute(select(Lead).where(Lead.email == to_email))).scalar_one_or_none()
        if not lead:
            continue

        event_type = _EVENT_MAP.get(sg_event, sg_event)

        new_event = EmailEvent(
            lead_id=lead.id,
            message_id=message_id,
            event_type=event_type,
            channel="email",
            clicked_url=clicked_url,
            occurred_at=datetime.now(timezone.utc),
        )
        # Append to the relationship so the in-memory list stays in sync for
        # the intent recompute below — db.add alone wouldn't update it.
        lead.email_events.append(new_event)

        # State machine update
        now = datetime.now(timezone.utc)
        if event_type == "opened" and lead.state == "contacted":
            lead.state = "engaged"
            lead.state_updated_at = now
        elif event_type == "clicked" and lead.state in ("contacted", "engaged"):
            lead.state = "engaged"
            lead.state_updated_at = now
        elif event_type == "unsubscribed":
            lead.opted_out = True
            lead.opted_out_at = now
            lead.state = "unsubscribed"
            lead.state_updated_at = now
        elif event_type == "bounced":
            lead.state = "closed"
            lead.state_updated_at = now

        processed += 1
        affected_leads[lead.id] = lead
        if event_type in _INTENT_REFRESH_EVENTS:
            needs_intent_refresh.add(lead.id)

        try:
            activity = {
                "type": "email_event",
                "lead_id": str(lead.id),
                "lead_name": f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
                "event": event_type,
                "timestamp": now.isoformat(),
            }
            await push_activity(activity)
            await publish_event("email.events", activity)
        except Exception:
            pass

    # Re-derive buying intent for leads with new engagement
    for lead_id in needs_intent_refresh:
        lead = affected_leads.get(lead_id)
        if lead is not None:
            try:
                await recompute_intent_for_lead(db, lead)
            except Exception as e:
                logger.warning("Intent recompute failed for %s: %s", lead_id, e)

    await db.flush()
    return {"processed": processed}


@router.post("/reply")
async def inbound_reply(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receive an inbound email reply, classify it, persist as event, update state.

    Expected payload:
    { "from_email": "...", "subject": "...", "body": "...", "in_reply_to": "..." }
    """
    body_data = await request.json()
    from_email = body_data.get("from_email")
    reply_text = body_data.get("body", "")
    subject = body_data.get("subject")

    if not from_email:
        raise HTTPException(status_code=400, detail="from_email required")

    lead = (await db.execute(select(Lead).where(Lead.email == from_email))).scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")

    classification = await classify_reply(reply_text)

    now = datetime.now(timezone.utc)
    event = EmailEvent(
        lead_id=lead.id,
        event_type="replied",
        channel="email",
        subject=subject,
        reply_content=reply_text,
        reply_sentiment=classification.get("sentiment"),
        reply_intent=classification.get("intent"),
        occurred_at=now,
    )
    # Keep the in-memory relationship in sync for the intent recompute.
    lead.email_events.append(event)

    # Update lead state
    intent = classification.get("intent", "")
    if intent == "unsubscribe":
        lead.opted_out = True
        lead.opted_out_at = now
        lead.state = "unsubscribed"
    elif intent in ("interested", "meeting_requested"):
        lead.state = "replied"
    else:
        lead.state = "replied"
    lead.state_updated_at = now

    # Reply is the strongest possible buying-intent signal — refresh score.
    try:
        await recompute_intent_for_lead(db, lead)
    except Exception as e:
        logger.warning("Intent recompute on reply failed for %s: %s", lead.id, e)

    await db.flush()

    try:
        activity = {
            "type": "reply",
            "lead_id": str(lead.id),
            "lead_name": f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
            "sentiment": classification.get("sentiment"),
            "intent": classification.get("intent"),
            "timestamp": now.isoformat(),
        }
        await push_activity(activity)
        await publish_event("email.replies", activity)
    except Exception:
        pass

    # Trigger reasoning so agent reacts to the reply
    try:
        from app.tasks.reasoning_tasks import reason_for_lead_task
        reason_for_lead_task.delay(str(lead.id), False)
    except Exception:
        pass

    return {"status": "processed", "classification": classification}


@router.post("/check-inbox")
async def check_inbox():
    """
    Manually trigger an IMAP inbox check.
    Reads unread emails, matches them to leads, and processes as replies.
    """
    from app.inbox.imap_reader import check_inbox_for_replies
    result = await check_inbox_for_replies()
    return result
