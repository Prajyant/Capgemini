"""SendGrid email sending integration."""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import EmailEvent, Lead
from app.outreach.compliance import (
    can_send_to_lead,
    inject_unsubscribe_footer,
    text_to_html,
)

logger = logging.getLogger(__name__)


async def send_email(
    db: AsyncSession,
    lead: Lead,
    subject: str,
    body: str,
    ab_variant: str = "A",
    to_email_override: Optional[str] = None,
) -> Optional[EmailEvent]:
    """
    Send an email via SendGrid and record the event.

    `to_email_override` is the demo escape hatch — if set, the email is
    delivered to that address instead of `lead.email`, but the event is
    still recorded against the lead so the dashboard, agent reasoning and
    reply matching all work as if it had been sent to the buyer. Used by
    the Compose Email modal so presenters can route the live email to
    their own inbox during a pitch.

    Returns the EmailEvent, or None if blocked by compliance.
    """
    allowed, reason = can_send_to_lead(lead.opted_out, lead.state)
    if not allowed:
        logger.info("Send blocked for lead %s: %s", lead.id, reason)
        return None

    body_with_footer = inject_unsubscribe_footer(body, str(lead.id))
    target = (to_email_override or "").strip() or lead.email

    message_id = await _send_via_sendgrid(
        to_email=target,
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
    """
    Send via SendGrid as both plain-text and HTML with click + open tracking
    explicitly enabled.

    Click tracking only fires when SendGrid can rewrite an <a href> in the HTML
    payload (and, with `enable_text=True`, plain URLs in the text payload too).
    Sending as text-only meant we never received `click` webhook events — that
    is why client clicks weren't showing up.

    Returns the message ID. In dev mode without an API key, returns a mock ID.
    """
    if not settings.SENDGRID_API_KEY:
        logger.info("SENDGRID_API_KEY missing — mock send to %s", to_email)
        return f"mock-{datetime.now(timezone.utc).timestamp()}"

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import (
            ClickTracking,
            From,
            Mail,
            OpenTracking,
            To,
            TrackingSettings,
        )

        html_body = text_to_html(body)

        message = Mail(
            from_email=From(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
            to_emails=To(to_email, to_name),
            subject=subject,
            plain_text_content=body,
            html_content=html_body,
        )

        # Force click + open tracking on every send so the SendGrid event
        # webhook delivers `click` / `open` events even if the account-level
        # default has them off.
        tracking = TrackingSettings()
        tracking.click_tracking = ClickTracking(enable=True, enable_text=True)
        tracking.open_tracking = OpenTracking(enable=True)
        message.tracking_settings = tracking

        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        message_id = response.headers.get(
            "X-Message-Id", f"sg-{datetime.now(timezone.utc).timestamp()}"
        )
        logger.info("Sent email to %s via SendGrid (msg=%s)", to_email, message_id)
        return message_id
    except Exception as e:
        logger.exception("SendGrid send failed: %s", e)
        return f"failed-{datetime.now(timezone.utc).timestamp()}"
