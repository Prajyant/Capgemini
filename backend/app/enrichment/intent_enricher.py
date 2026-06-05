"""
Buying intent signals — derived from news, hiring signals, and product searches.

This is a heuristic layer. In production it would integrate with intent providers
like Bombora or G2 buyer intent.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def derive_intent_signals(
    company_name: Optional[str],
    company_news: list,
    tech_stack: list,
) -> dict:
    """Derive intent signals from already-fetched enrichment data."""
    intent = {
        "funding_recent": False,
        "hiring_count": 0,
        "tech_replacement_signals": [],
        "intent_score": 0,
    }

    # Funding signal
    for item in company_news or []:
        headline = (item.get("headline") or "").lower()
        if any(kw in headline for kw in ["raised", "series a", "series b", "funding round", "seed round"]):
            intent["funding_recent"] = True
            intent["intent_score"] += 30
            break

    # Hiring signal (heuristic — real impl would check job boards)
    for item in company_news or []:
        headline = (item.get("headline") or "").lower()
        if any(kw in headline for kw in ["hiring", "expanding team", "growing"]):
            intent["hiring_count"] = 3
            intent["intent_score"] += 15
            break

    # Tech replacement signals
    competitor_techs = {"outreach", "salesloft", "apollo", "lemlist"}
    for tech in tech_stack or []:
        if tech.lower() in competitor_techs:
            intent["tech_replacement_signals"].append(tech)
            intent["intent_score"] += 10

    intent["intent_score"] = min(intent["intent_score"], 100)
    return intent
