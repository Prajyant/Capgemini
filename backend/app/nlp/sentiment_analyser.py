"""Lightweight sentiment scoring (re-uses reply_classifier output)."""
from app.nlp.reply_classifier import classify_reply


async def analyse_sentiment(text: str) -> str:
    """Return positive | negative | neutral | objection | out_of_office."""
    result = await classify_reply(text)
    return result.get("sentiment", "neutral")
