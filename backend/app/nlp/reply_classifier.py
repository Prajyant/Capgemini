"""
Classify inbound replies. Uses Claude for accurate intent + sentiment detection.
"""
import json
import logging
from typing import Optional

from langchain_anthropic import ChatAnthropic

from app.config import settings

logger = logging.getLogger(__name__)


SYSTEM = """You classify inbound sales email replies.

Return JSON only:
{
  "sentiment": "positive | negative | neutral | objection | out_of_office",
  "intent": "interested | not_now | wrong_person | competitor | unsubscribe | meeting_requested | needs_more_info | already_customer | unknown",
  "confidence": 0.0 to 1.0,
  "summary": "one sentence summary of what they said"
}"""


async def classify_reply(reply_text: str) -> dict:
    """Classify a reply. Falls back to neutral/unknown on error."""
    if not reply_text or not reply_text.strip():
        return {"sentiment": "neutral", "intent": "unknown", "confidence": 0.0, "summary": ""}

    try:
        llm = ChatAnthropic(
            model=settings.CLAUDE_MODEL,
            max_tokens=400,
            temperature=0.1,
            api_key=settings.ANTHROPIC_API_KEY,
        )
        response = llm.invoke([
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Reply text:\n\n{reply_text}"},
        ])
        content = response.content
        if isinstance(content, list):
            content = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
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
    if any(k in t for k in ["unsubscribe", "remove me", "stop emailing"]):
        return {"sentiment": "negative", "intent": "unsubscribe", "confidence": 0.9, "summary": "Unsubscribe request"}
    if any(k in t for k in ["out of office", "ooo", "on vacation", "out of the office"]):
        return {"sentiment": "neutral", "intent": "unknown", "confidence": 0.95, "summary": "Auto-reply OOO"}
    if any(k in t for k in ["interested", "yes", "sounds good", "let's chat", "tell me more", "book"]):
        return {"sentiment": "positive", "intent": "interested", "confidence": 0.7, "summary": "Expressed interest"}
    if any(k in t for k in ["already use", "we use", "we have"]):
        return {"sentiment": "objection", "intent": "competitor", "confidence": 0.7, "summary": "Mentioned existing solution"}
    if any(k in t for k in ["not now", "later", "next quarter"]):
        return {"sentiment": "neutral", "intent": "not_now", "confidence": 0.6, "summary": "Deferred"}
    return {"sentiment": "neutral", "intent": "unknown", "confidence": 0.3, "summary": ""}
