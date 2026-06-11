"""
IMAP inbox reader — polls your email inbox for replies to outreach emails.

Matches replies to leads by sender email, classifies tone/intent,
persists as EmailEvent, and triggers the reasoning engine.
"""
import email
import imaplib
import logging
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
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


def _decode_subject(msg) -> str:
    """Decode email subject handling various encodings."""
    raw = msg.get("Subject", "")
    decoded_parts = decode_header(raw)
    parts = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            parts.append(part.decode(encoding or "utf-8", errors="replace"))
        else:
            parts.append(part)
    return " ".join(parts)


def _extract_body(msg) -> str:
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
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


def _get_sent_date(msg) -> Optional[datetime]:
    """Parse the Date header into a timezone-aware datetime."""
    date_str = msg.get("Date")
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return None


def connect_imap() -> imaplib.IMAP4_SSL:
    """Connect to the IMAP server using settings from .env."""
    host = settings.IMAP_HOST
    port = int(settings.IMAP_PORT)
    mail = imaplib.IMAP4_SSL(host, port)
    mail.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
    return mail


def fetch_unread_emails(mail: imaplib.IMAP4_SSL, folder: str = "INBOX") -> list[dict]:
    """Fetch recent reply emails (last 1 day) — handles both read and unread.
    
    Deduplication happens downstream by checking message_id in the DB,
    so it's safe to return already-seen emails here.
    """
    from datetime import date, timedelta

    mail.select(folder)
    since_date = (date.today() - timedelta(days=1)).strftime("%d-%b-%Y")
    status, data = mail.search(None, f'(SINCE "{since_date}")')
    if status != "OK":
        return []

    email_ids = data[0].split()
    # Only process last 20 to avoid overload
    email_ids = email_ids[-20:]
    emails = []

    for eid in email_ids:
        status, msg_data = mail.fetch(eid, "(RFC822)")
        if status != "OK":
            continue

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        from_name, from_email_addr = parseaddr(msg.get("From", ""))
        subject = _decode_subject(msg)
        body = _extract_body(msg)
        sent_date = _get_sent_date(msg)
        message_id = msg.get("Message-ID", "")
        in_reply_to = msg.get("In-Reply-To", "")

        # Only pick up replies (has In-Reply-To or subject starts with Re:)
        is_reply = bool(in_reply_to) or subject.lower().startswith("re:")
        if not is_reply:
            continue

        emails.append({
            "from_email": from_email_addr.lower().strip(),
            "from_name": from_name,
            "subject": subject,
            "body": body,
            "sent_date": sent_date,
            "message_id": message_id,
            "in_reply_to": in_reply_to,
            "imap_id": eid,
        })

    return emails


async def process_inbox_replies() -> dict:
    """
    Main polling function: connects to inbox, fetches unread emails,
    matches them to leads, classifies replies, and triggers reasoning.

    Returns summary of processed emails.
    """
    if not settings.IMAP_HOST or not settings.IMAP_USER:
        logger.warning("IMAP not configured — skipping inbox poll")
        return {"processed": 0, "skipped": 0, "error": "IMAP not configured"}

    try:
        mail = connect_imap()
    except Exception as e:
        logger.exception("IMAP connection failed: %s", e)
        return {"processed": 0, "skipped": 0, "error": str(e)}

    try:
        unread = fetch_unread_emails(mail)
    except Exception as e:
        logger.exception("Failed to fetch emails: %s", e)
        mail.logout()
        return {"processed": 0, "skipped": 0, "error": str(e)}

    processed = 0
    skipped = 0

    async with get_db_context() as db:
        for email_data in unread:
            from_email = email_data["from_email"]

            # Match sender to a lead in our DB
            lead = (
                await db.execute(select(Lead).where(Lead.email == from_email))
            ).scalar_one_or_none()

            if not lead:
                skipped += 1
                continue

            # Skip replies that are older than the lead's creation
            email_date = email_data.get("sent_date")
            if email_date and lead.created_at:
                lead_created = lead.created_at.replace(tzinfo=timezone.utc) if lead.created_at.tzinfo is None else lead.created_at
                email_dt = email_date.replace(tzinfo=timezone.utc) if email_date.tzinfo is None else email_date
                if email_dt < lead_created:
                    skipped += 1
                    continue

            # Check if we already processed this message (dedup by message_id)
            if email_data["message_id"]:
                existing = (
                    await db.execute(
                        select(EmailEvent).where(
                            EmailEvent.message_id == email_data["message_id"]
                        )
                    )
                ).scalar_one_or_none()
                if existing:
                    skipped += 1
                    continue

            # Classify the reply tone and intent
            classification = await classify_reply(email_data["body"])

            # Calculate time since our last email to this lead
            days_since_sent = _days_since_last_sent(lead)

            # Persist as email event
            now = email_data["sent_date"] or datetime.now(timezone.utc)
            event = EmailEvent(
                lead_id=lead.id,
                message_id=email_data["message_id"] or None,
                event_type="replied",
                channel="email",
                subject=email_data["subject"],
                reply_content=email_data["body"],
                reply_sentiment=classification.get("sentiment"),
                reply_intent=classification.get("intent"),
                occurred_at=now,
            )
            lead.email_events.append(event)

            # Update lead state — always set to "replied" and let human decide
            intent = classification.get("intent", "")
            state_now = datetime.now(timezone.utc)
            lead.state = "replied"
            lead.state_updated_at = state_now

            # Recompute buying intent score
            try:
                await recompute_intent_for_lead(db, lead)
            except Exception as e:
                logger.warning("Intent recompute failed for %s: %s", lead.id, e)

            # Push to live activity feed
            try:
                activity = {
                    "type": "reply_detected",
                    "lead_id": str(lead.id),
                    "lead_name": f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
                    "sentiment": classification.get("sentiment"),
                    "intent": classification.get("intent"),
                    "days_since_sent": days_since_sent,
                    "summary": classification.get("summary", ""),
                    "timestamp": state_now.isoformat(),
                }
                await push_activity(activity)
                await publish_event("email.replies", activity)
            except Exception:
                pass

            # Trigger reasoning so agent reacts with full context
            try:
                from app.tasks.reasoning_tasks import reason_for_lead_task
                reason_for_lead_task.delay(str(lead.id), False)
            except Exception:
                pass

            processed += 1
            logger.info(
                "Processed reply from %s | sentiment=%s intent=%s days_since_sent=%s",
                from_email,
                classification.get("sentiment"),
                classification.get("intent"),
                days_since_sent,
            )

        await db.flush()

    mail.logout()
    return {"processed": processed, "skipped": skipped}


def _days_since_last_sent(lead: Lead) -> Optional[int]:
    """Calculate how many days since we last sent an email to this lead."""
    sent_events = [
        e for e in (lead.email_events or [])
        if e.event_type == "sent" and e.occurred_at
    ]
    if not sent_events:
        return None
    latest_sent = max(sent_events, key=lambda e: e.occurred_at)
    delta = datetime.now(timezone.utc) - latest_sent.occurred_at.replace(tzinfo=timezone.utc)
    return delta.days
