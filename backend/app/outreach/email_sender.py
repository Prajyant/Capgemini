"""SendGrid email sending integration."""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import EmailEvent, Lead
from app.outreach.compliance import inject_unsubscribe_footer, can_send_to_lead

logger = logging.getLogger(__name__)


_STEP_TO_TYPE = {1: "intro", 2: "follow_up", 3: "breakup"}


def _sequence_type_for_step(step_number: int) -> str:
    """Map a sequence step number to its email type. Anything past 3 falls back to follow_up."""
    return _STEP_TO_TYPE.get(step_number, "follow_up")


async def generate_and_send(
    db: AsyncSession,
    lead: Lead,
    ab_variant: str = "A",
    personalisation_hooks: Optional[list[str]] = None,
) -> Optional[EmailEvent]:
    """
    Generate a personalised email for this lead's next sequence step and send it.

    If the lead has replied, generates a contextual response to their reply
    instead of following the cold outreach sequence.
    """
    from app.agent.decision_maker import _serialize_lead
    from app.outreach.sequence_generator import generate_personalised_email, generate_reply_email

    allowed, reason = can_send_to_lead(lead.opted_out, lead.state)
    if not allowed:
        logger.info("generate_and_send blocked for lead %s: %s", lead.id, reason)
        return None

    profile = _serialize_lead(lead)

    # If lead has replied, generate a contextual response instead of cold follow-up
    last_reply = None
    for evt in sorted(lead.email_events or [], key=lambda e: e.occurred_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True):
        if evt.event_type == "replied" and evt.reply_content:
            last_reply = evt
            break

    if last_reply:
        email_data = await generate_reply_email(
            lead=profile,
            reply_content=last_reply.reply_content,
            reply_intent=last_reply.reply_intent,
            personalisation_hooks=personalisation_hooks,
        )
    else:
        next_step = max(1, (lead.current_step or 0) + 1)
        sequence_type = _sequence_type_for_step(next_step)
        email_data = await generate_personalised_email(
            lead=profile,
            step_number=next_step,
            sequence_type=sequence_type,
            personalisation_hooks=personalisation_hooks,
            ab_variant=ab_variant,
        )

    event = await send_email(
        db=db,
        lead=lead,
        subject=email_data.get("subject", ""),
        body=email_data.get("body", ""),
        ab_variant=email_data.get("ab_variant", ab_variant),
    )
    if event is not None:
        lead.current_step = (lead.current_step or 0) + 1
    return event


async def send_email(
    db: AsyncSession,
    lead: Lead,
    subject: str,
    body: str,
    ab_variant: str = "A",
) -> Optional[EmailEvent]:
    """
    Send an email via SendGrid and record the event.
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
    """Send via SendGrid. Returns message ID. In dev mode without API key, returns mock ID."""
    if not settings.SENDGRID_API_KEY:
        logger.info("SENDGRID_API_KEY missing — mock send to %s", to_email)
        return f"mock-{datetime.now(timezone.utc).timestamp()}"

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, From, To

        message = Mail(
            from_email=From(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
            to_emails=To(to_email, to_name),
            subject=subject,
            plain_text_content=body,
        )
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        message_id = response.headers.get("X-Message-Id", f"sg-{datetime.now(timezone.utc).timestamp()}")
        logger.info("Sent email to %s via SendGrid (msg=%s)", to_email, message_id)
        return message_id
    except Exception as e:
        logger.exception("SendGrid send failed: %s", e)
        return f"failed-{datetime.now(timezone.utc).timestamp()}"
