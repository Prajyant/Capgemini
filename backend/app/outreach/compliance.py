"""GDPR / CAN-SPAM compliance + email body shaping (plain text + HTML)."""
import html
import re

from app.config import settings


# Match http(s) URLs inside plain text bodies so we can wrap them in <a> tags
# for SendGrid click-tracking (click events are only emitted for tracked HTML
# anchors; plain http URLs in plain-text emails are NOT tracked by default).
_URL_RE = re.compile(r"(https?://[^\s<>\"]+)")


def inject_unsubscribe_footer(body: str, lead_id: str) -> str:
    """Append a CAN-SPAM compliant footer to the (plain text) email body."""
    unsubscribe_url = f"{settings.UNSUBSCRIBE_BASE_URL}/{lead_id}"
    footer = (
        "\n\n---\n"
        "If you'd prefer not to hear from us, you can unsubscribe here: "
        f"{unsubscribe_url}\n"
        f"{settings.SENDGRID_FROM_NAME} • {settings.COMPANY_PHYSICAL_ADDRESS}\n"
    )
    return body + footer


def text_to_html(body: str) -> str:
    """
    Convert a plain text email body into a clean HTML version.

    - HTML-escapes user content
    - Preserves paragraphs (blank line) and single newlines (<br>)
    - Auto-linkifies http(s) URLs so SendGrid can rewrite them for click tracking
    """
    if not body:
        return ""

    # Tokenise the body into URL / non-URL chunks so we only escape non-URL text
    parts: list[tuple[str, str]] = []
    last = 0
    for m in _URL_RE.finditer(body):
        if m.start() > last:
            parts.append(("text", body[last:m.start()]))
        parts.append(("url", m.group(1)))
        last = m.end()
    if last < len(body):
        parts.append(("text", body[last:]))

    rendered: list[str] = []
    for kind, content in parts:
        if kind == "url":
            safe = html.escape(content, quote=True)
            rendered.append(f'<a href="{safe}" target="_blank" rel="noopener noreferrer">{safe}</a>')
        else:
            rendered.append(html.escape(content))

    joined = "".join(rendered)
    # Paragraphs separated by blank lines, soft breaks elsewhere
    paragraphs = [p for p in joined.split("\n\n")]
    html_paragraphs = [
        f"<p style=\"margin:0 0 12px 0;\">{p.replace(chr(10), '<br>')}</p>"
        for p in paragraphs
        if p.strip()
    ]

    return (
        '<div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;'
        'font-size:14px;line-height:1.55;color:#1f2937;">'
        + "\n".join(html_paragraphs)
        + "</div>"
    )


def can_send_to_lead(opted_out: bool, state: str) -> tuple[bool, str]:
    """Return (allowed, reason)."""
    if opted_out:
        return False, "Lead has opted out (CAN-SPAM)"
    if state in ("unsubscribed", "closed"):
        return False, f"Lead is in terminal state: {state}"
    return True, ""
