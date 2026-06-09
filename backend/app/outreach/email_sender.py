"""SendGrid email sending integration with dev-mode logging."""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import EmailEvent, Lead
from app.outreach.compliance import inject_unsubscribe_footer, can_send_to_lead

logger = logging.getLogger(__name__)


async def send_email(
    db: AsyncSession,
    lead: Lead,
    subject: str,
    body: str,
    ab_variant: str = "A",
) -> Optional[EmailEvent]:
    """
    Send an email via SendGrid and record the event.
    In dev mode (no API key), logs the email content so it's visible in docker logs.
    Returns the EmailEvent or None if blocked by compliance.
    """
    allowed, reason = can_send_to_lead(lead.opted_out, lead.state)
    if not allowed:
        logger.info("Send blocked for lead %s: %s", lead.id, reason)
        return None

    body_with_footer = inject_unsubscribe_footer(body, str(lead.id))

    message_id = await _send_via_sendgrid(
        to_email=lead.email,
        to_name=f"{lead.first_name or ''} {lead.last_name or ''}".strip() or None,
        subject=subject,
        body=body_with_footer,
    )

    event = EmailEvent(
        lead_id=lead.id,
        message_id=message_id,
        event_type="sent",
        channel="email",
        subject=subject,
        body=body_with_footer,
        ab_variant=ab_variant,
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(event)

    if lead.state in ("new", "enriched"):
        lead.state = "contacted"
        lead.state_updated_at = datetime.now(timezone.utc)

    await db.flush()
    return event


async def _send_via_sendgrid(
    to_email: str,
    subject: str,
    body: str,
    to_name: Optional[str] = None,
) -> str:
    """Send via SendGrid. Falls back to dev-mode logging if no API key."""
    if not settings.SENDGRID_API_KEY or settings.SENDGRID_API_KEY in (
        "your_sendgrid_key_here", ""
    ):
        # Dev mode: log the full email so it's visible / verifiable
        separator = "=" * 60
        logger.info(
            "\n%s\n📧 DEV MODE EMAIL (would be sent via SendGrid)\n%s\n"
            "TO:      %s <%s>\n"
            "FROM:    %s <%s>\n"
            "SUBJECT: %s\n"
            "%s\n"
            "%s\n"
            "%s",
            separator, separator,
            to_name or "", to_email,
            settings.SENDGRID_FROM_NAME, settings.SENDGRID_FROM_EMAIL,
            subject,
            "-" * 60,
            body,
            separator,
        )
        return f"dev-{datetime.now(timezone.utc).timestamp():.0f}"

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, From, To, Content

        message = Mail()
        message.from_email = From(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME)
        message.to = [To(to_email, to_name)]
        message.subject = subject
        message.content = [Content("text/plain", body)]

        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        message_id = response.headers.get(
            "X-Message-Id",
            f"sg-{datetime.now(timezone.utc).timestamp():.0f}"
        )
        logger.info("✅ Email sent to %s via SendGrid (id=%s)", to_email, message_id)
        return message_id
    except Exception as e:
        logger.exception("❌ SendGrid send failed for %s: %s", to_email, e)
        return f"failed-{datetime.now(timezone.utc).timestamp():.0f}"
