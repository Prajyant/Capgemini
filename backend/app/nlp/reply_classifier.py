"""
Classify inbound replies. Uses Claude for accurate intent + sentiment detection.
"""
import json
import logging
from typing import Optional

from app.config import settings
from app.llm import get_llm, extract_text

logger = logging.getLogger(__name__)


SYSTEM = """You classify inbound sales email replies.

Return JSON only:
{
  "sentiment": "positive | negative | neutral | objection | out_of_office",
  "intent": "interested | not_now | wrong_person | competitor | unsubscribe | meeting_requested | needs_more_info | already_customer | unknown",
  "confidence": 0.0 to 1.0,
  "summary": "one sentence summary of what they said"
}

INTENT DEFINITIONS (be precise):
- "competitor": They use a COMPETING product (e.g., "we already use Outreach/Salesloft/Apollo"). This is an OBJECTION to overcome, NOT a closed deal.
- "already_customer": They are already YOUR customer / already use YOUR product. Only use this if they clearly are an existing customer of the sender.
- "interested": Positive, wants to learn more or move forward.
- "meeting_requested": Explicitly asks to schedule or accepts a meeting/call.
- "needs_more_info": Asks a question before committing.
- "not_now": Interested but timing is wrong (busy, next quarter, later).
- "wrong_person": They are not the right contact; points to someone else.
- "unsubscribe": Asks to be removed / stop emailing.

IMPORTANT: "We already use [competitor] and we're happy" = intent "competitor" (an objection to address), NEVER "already_customer"."""


async def classify_reply(reply_text: str) -> dict:
    """Classify a reply. Falls back to neutral/unknown on error."""
    if not reply_text or not reply_text.strip():
        return {"sentiment": "neutral", "intent": "unknown", "confidence": 0.0, "summary": ""}

    try:
        llm = get_llm(temperature=0.1, max_tokens=400)
        response = llm.invoke([
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Reply text:\n\n{reply_text}"},
        ])
        content = extract_text(response.content)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        return json.loads(content)
    except Exception as e:
        logger.exception("Reply classification failed: %s", e)
        return _heuristic_fallback(reply_text)


def _heuristic_fallback(text: str) -> dict:
    t = text.lower()
    if any(k in t for k in ["unsubscribe", "remove me", "stop emailing", "don't email", "do not email"]):
        return {"sentiment": "negative", "intent": "unsubscribe", "confidence": 0.9, "summary": "Unsubscribe request"}
    if any(k in t for k in ["out of office", "ooo", "on vacation", "out of the office"]):
        return {"sentiment": "neutral", "intent": "unknown", "confidence": 0.95, "summary": "Auto-reply OOO"}
    if any(k in t for k in ["wrong person", "not the right person", "talk to", "reach out to", "you'd want to", "forward this to"]):
        return {"sentiment": "neutral", "intent": "wrong_person", "confidence": 0.75, "summary": "Pointed to a different contact"}
    # Competitor objection — using a competing product
    if any(k in t for k in ["already use", "already using", "we use", "we're using", "happy with", "switch"]):
        return {"sentiment": "objection", "intent": "competitor", "confidence": 0.75, "summary": "Uses a competing solution"}
    if any(k in t for k in ["calendar invite", "schedule", "let's do it", "let's chat", "book a", "set up a call", "meeting"]):
        return {"sentiment": "positive", "intent": "meeting_requested", "confidence": 0.8, "summary": "Wants to schedule a meeting"}
    # Timing deferral — check BEFORE needs_more_info since "next quarter" etc. are strong timing signals
    if any(k in t for k in ["not now", "later", "next quarter", "next year", "heads-down", "heads down", "busy right now", "revisit", "circle back", "reach out in", "touch base in"]):
        return {"sentiment": "neutral", "intent": "not_now", "confidence": 0.75, "summary": "Deferred to later"}
    if any(k in t for k in ["interested", "sounds good", "tell me more", "learn more", "open to"]):
        return {"sentiment": "positive", "intent": "interested", "confidence": 0.7, "summary": "Expressed interest"}
    if any(k in t for k in ["how is", "how are you different", "what makes", "can you tell me", "question", "different from", "pricing", "how does"]):
        return {"sentiment": "neutral", "intent": "needs_more_info", "confidence": 0.7, "summary": "Asked for more information"}
    return {"sentiment": "neutral", "intent": "unknown", "confidence": 0.3, "summary": ""}
