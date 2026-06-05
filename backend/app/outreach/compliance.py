"""GDPR / CAN-SPAM compliance layer."""
from app.config import settings


def inject_unsubscribe_footer(body: str, lead_id: str) -> str:
    """Append a CAN-SPAM compliant footer to email body."""
    unsubscribe_url = f"{settings.UNSUBSCRIBE_BASE_URL}/{lead_id}"
    footer = (
        "\n\n---\n"
        "If you'd prefer not to hear from us, you can unsubscribe here: "
        f"{unsubscribe_url}\n"
        f"{settings.SENDGRID_FROM_NAME} • {settings.COMPANY_PHYSICAL_ADDRESS}\n"
    )
    return body + footer


def can_send_to_lead(opted_out: bool, state: str) -> tuple[bool, str]:
    """Return (allowed, reason)."""
    if opted_out:
        return False, "Lead has opted out (CAN-SPAM)"
    if state in ("unsubscribed", "closed"):
        return False, f"Lead is in terminal state: {state}"
    return True, ""
