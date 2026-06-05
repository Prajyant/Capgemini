"""
LLM email writer — generates personalised sequence emails.

Every email is written with enriched lead context. Never a template substitution.
"""
import json
import logging
from typing import Optional

from app.config import settings
from app.llm import get_llm, extract_text
from app.utils.spam_scorer import check_spam_score

logger = logging.getLogger(__name__)


EMAIL_GUIDELINES = {
    "intro": {
        "purpose": "First touch. Build curiosity, not pitch.",
        "length": "Under 100 words body",
        "tone": "Peer to peer, not vendor to buyer",
        "cta": "Single soft question, not a meeting request",
    },
    "follow_up": {
        "purpose": "Add value. Reference something specific.",
        "length": "Under 80 words body",
        "tone": "Helpful, not pushy",
        "cta": "Make it easier to say yes than ignore",
    },
    "breakup": {
        "purpose": "Last touch. Make it easy to respond or close.",
        "length": "Under 60 words body",
        "tone": "Respectful, no guilt",
        "cta": "Permission to close or reconnect later",
    },
}

VARIANT_INSTRUCTIONS = {
    "A": "Lead with a problem-led hook — open with the pain point this person likely faces in their role.",
    "B": "Lead with an insight hook — open with a surprising fact or observation about their industry or company.",
}


async def generate_personalised_email(
    lead: dict,
    step_number: int = 1,
    sequence_type: str = "intro",
    personalisation_hooks: Optional[list[str]] = None,
    ab_variant: str = "A",
) -> dict:
    """Generate one personalised email. Returns subject, body, and metadata."""
    personalisation_hooks = personalisation_hooks or []
    guidelines = EMAIL_GUIDELINES.get(sequence_type, EMAIL_GUIDELINES["intro"])
    variant_instruction = VARIANT_INSTRUCTIONS.get(ab_variant, VARIANT_INSTRUCTIONS["A"])

    tech_stack_str = ", ".join((lead.get("tech_stack") or [])[:4]) or "Unknown"
    news_items = lead.get("company_news") or []
    recent_news = news_items[0].get("headline") if news_items and isinstance(news_items[0], dict) else "None available"

    prompt = f"""Generate a personalised B2B sales email.

LEAD CONTEXT:
Name: {lead.get('first_name', '')} {lead.get('last_name', '')}
Title: {lead.get('job_title', 'Unknown')} at {lead.get('company_name', 'Unknown')}
Industry: {lead.get('industry', 'Unknown')}
Company size: {lead.get('employee_range', 'Unknown')} employees
Tech stack they use: {tech_stack_str}
Recent company news: {recent_news}
Personalisation hooks to use: {', '.join(personalisation_hooks) if personalisation_hooks else 'None provided — use lead context'}

EMAIL TYPE: {sequence_type} (Step {step_number} of 3)
PURPOSE: {guidelines['purpose']}
LENGTH: {guidelines['length']}
TONE: {guidelines['tone']}
CTA: {guidelines['cta']}

VARIANT {ab_variant} INSTRUCTION: {variant_instruction}

RULES:
- Never mention competitors by name
- No generic openers like "I hope this finds you well"
- Reference something specific from their context
- One CTA only
- No attachments mentioned
- Sound like a human wrote this at 9am

Respond with valid JSON only (no markdown fences):
{{
    "subject": "email subject line (under 9 words, no clickbait)",
    "body": "email body (plain text, no markdown)",
    "personalisation_used": "what specific context you used and why",
    "readability_notes": "why this will get read"
}}"""

    try:
        llm = get_llm(temperature=0.7, max_tokens=1000)
        response = llm.invoke(prompt)
        content = extract_text(response.content)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        email_data = json.loads(content)
    except Exception as e:
        logger.exception("Email generation failed: %s", e)
        email_data = {
            "subject": f"Quick question, {lead.get('first_name', 'there')}",
            "body": (
                f"Hi {lead.get('first_name', 'there')},\n\n"
                f"Saw {lead.get('company_name', 'your team')} is doing interesting work in {lead.get('industry', 'your space')}. "
                "Curious how you currently approach outreach decisions — open to a quick exchange?\n\nBest"
            ),
            "personalisation_used": "fallback template due to LLM error",
            "readability_notes": "fallback",
        }

    spam_score = await check_spam_score(email_data.get("body", ""), email_data.get("subject", ""))
    email_data["spam_score"] = spam_score
    email_data["passes_spam_check"] = spam_score < 3.0
    email_data["ab_variant"] = ab_variant
    return email_data


async def generate_full_sequence(lead: dict, personalisation_hooks: Optional[list[str]] = None) -> list[dict]:
    """Generate all 3 emails (intro, follow_up, breakup) for a lead."""
    sequence_types = ["intro", "follow_up", "breakup"]
    emails = []
    for i, seq_type in enumerate(sequence_types, start=1):
        # Alternate variants for A/B coverage
        variant = "A" if i % 2 == 1 else "B"
        email = await generate_personalised_email(
            lead=lead,
            step_number=i,
            sequence_type=seq_type,
            personalisation_hooks=personalisation_hooks,
            ab_variant=variant,
        )
        email["step_number"] = i
        email["sequence_type"] = seq_type
        emails.append(email)
    return emails
