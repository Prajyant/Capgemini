"""
IMAP Inbox Reader — polls the configured mailbox for replies to outreach emails.

Matches incoming emails to leads by sender address, then pushes them through
the existing reply processing pipeline (same as the /api/webhooks/reply endpoint).
"""
import asyncio
import email
import imaplib
import logging
from datetime import datetime, timezone
from email.header import decode_header
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_context
from app.enrichment.enrichment_agent import recompute_intent_for_lead
from app.models import EmailEvent, Lead
from app.nlp.reply_classifier import classify_reply
from app.redis_client import publish_event, push_activity

logger = logging.getLogger(__name__)


def decode_mime_header(header_value: str) -> str:
    """Decode MIME-encoded email header."""
    if not header_value:
        return ""
    decoded_parts = decode_header(header_value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def extract_email_address(from_header: str) -> str:
    """Extract bare email from 'Name <email@example.com>' format."""
    if "<" in from_header and ">" in from_header:
        return from_header.split("<")[1].split(">")[0].strip().lower()
    return from_header.strip().lower()


def get_email_body(msg: email.message.Message) -> str:
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        # Fallback to HTML if no plain text
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def clean_reply_text(raw_body: str) -> str:
    """
    Strip quoted reply thread and signature to extract just the new reply text.
    Removes lines starting with '>' and everything after common reply markers.
    """
    if not raw_body:
        return ""

    lines = raw_body.split("\n")
    clean_lines = []

    # Markers that indicate start of quoted original message
    quote_markers = [
        "on ",  # "On Fri, Jun 19, 2026 at 3:17 PM ... wrote:"
        "-----original message-----",
        "from:",
        "sent:",
        "________________________________",
    ]

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        # Stop at quoted thread markers
        if lower.startswith(">"):
            break
        # "On <date> ... wrote:" pattern
        if lower.startswith("on ") and ("wrote:" in lower or stripped.endswith(":")):
            break
        if any(lower.startswith(m) for m in quote_markers[1:]):
            break

        clean_lines.append(line)

    result = "\n".join(clean_lines).strip()
    # Remove trailing empty lines and collapse multiple blank lines
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")
    return result or raw_body[:500].strip()


async def process_reply(db: AsyncSession, lead: Lead, subject: str, body: str) -> Optional[EmailEvent]:
    """Process a reply for a lead — classify, store, update state."""
    # Check if we already processed this reply (avoid duplicates)
    # Match on lead + cleaned reply content (first 200 chars)
    content_key = body.strip().lower()[:200]
    existing_replies = (await db.execute(
        select(EmailEvent).where(
            EmailEvent.lead_id == lead.id,
            EmailEvent.event_type == "replied",
        )
    )).scalars().all()

    for er in existing_replies:
        if (er.reply_content or "").strip().lower()[:200] == content_key:
            logger.debug("Reply already processed for lead %s, skipping", lead.id)
            return None

    classification = await classify_reply(body)

    now = datetime.now(timezone.utc)
    event = EmailEvent(
        lead_id=lead.id,
        event_type="replied",
        channel="email",
        subject=subject,
        reply_content=body[:5000],  # Truncate very long replies
        reply_sentiment=classification.get("sentiment"),
        reply_intent=classification.get("intent"),
        occurred_at=now,
    )
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

    # Refresh buying intent
    try:
        await recompute_intent_for_lead(db, lead)
    except Exception as e:
        logger.warning("Intent recompute on reply failed for %s: %s", lead.id, e)

    await db.flush()

    # Publish activity
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

    # Trigger agent reasoning
    try:
        from app.tasks.reasoning_tasks import reason_for_lead_task
        reason_for_lead_task.delay(str(lead.id), False)
    except Exception:
        pass

    logger.info(
        "Processed reply from %s — sentiment: %s, intent: %s",
        lead.email, classification.get("sentiment"), classification.get("intent")
    )
    return event


def fetch_unread_emails() -> list[dict]:
    """Connect to IMAP and fetch unread emails. Returns list of parsed messages."""
    if not settings.IMAP_HOST or not settings.IMAP_USER or not settings.IMAP_PASSWORD:
        logger.warning("IMAP not configured — skipping inbox check")
        return []

    messages = []
    try:
        mail = imaplib.IMAP4_SSL(settings.IMAP_HOST, int(settings.IMAP_PORT or 993))
        mail.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
        mail.select("INBOX")

        # Search ALL messages from today (read + unread) to catch replies
        from datetime import date
        today = date.today().strftime("%d-%b-%Y")
        status, data = mail.search(None, f'(SINCE "{today}")')

        if status != "OK":
            logger.warning("IMAP search failed: %s", status)
            mail.logout()
            return []

        email_ids = data[0].split()
        logger.info("Found %d emails to check (today, read+unread)", len(email_ids))

        for eid in email_ids:
            status, msg_data = mail.fetch(eid, "(RFC822)")
            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            from_header = decode_mime_header(msg.get("From", ""))
            from_email = extract_email_address(from_header)
            subject = decode_mime_header(msg.get("Subject", ""))
            body = get_email_body(msg)
            body = clean_reply_text(body)

            # Skip emails from ourselves UNLESS they are a reply (Re: in subject)
            # This handles the case where the lead's email is the same as the sender
            is_reply = subject.lower().startswith("re:")
            if from_email == settings.SENDGRID_FROM_EMAIL.lower() and not is_reply:
                continue

            messages.append({
                "from_email": from_email,
                "subject": subject,
                "body": body,
                "message_id": msg.get("Message-ID", ""),
            })

        mail.logout()
    except Exception as e:
        logger.error("IMAP fetch failed: %s", e)

    return messages


async def check_inbox_for_replies():
    """
    Main function: fetch unread emails from IMAP, match to leads, process replies.
    Call this from a Celery task or directly.
    """
    messages = fetch_unread_emails()
    if not messages:
        logger.info("No new unread emails found")
        return {"processed": 0, "matched": 0}

    processed = 0
    matched = 0

    async with get_db_context() as db:
        for msg in messages:
            from_email = msg["from_email"]

            # Find matching lead
            lead = (await db.execute(
                select(Lead).where(Lead.email == from_email)
            )).scalar_one_or_none()

            if not lead:
                logger.debug("No lead found for sender: %s", from_email)
                processed += 1
                continue

            result = await process_reply(db, lead, msg["subject"], msg["body"])
            processed += 1
            if result:
                matched += 1

    logger.info("Inbox check complete: %d emails processed, %d matched to leads", processed, matched)
    return {"processed": processed, "matched": matched}
