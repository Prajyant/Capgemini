"""
Buying intent signals — derived from news, hiring signals, tech stack, and web scraping.

Analyses real news headlines to extract meaningful buying signals for B2B sales.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Keywords that signal buying intent for sales tools
FUNDING_KEYWORDS = [
    "raised", "series a", "series b", "series c", "seed round", "funding round",
    "secures funding", "investment", "venture capital", "vc-backed", "million",
    "closed a round", "pre-seed",
]

HIRING_KEYWORDS = [
    "hiring", "expanding team", "growing", "new hires", "recruiting",
    "looking for", "open positions", "head of sales", "vp of sales",
    "sales director", "account executive", "sdr", "bdr",
]

GROWTH_KEYWORDS = [
    "launches", "expands", "announces", "new product", "new feature",
    "partnership", "acquisition", "acquires", "merges", "going public", "ipo",
    "doubling down", "scaling",
]

PAIN_KEYWORDS = [
    "struggling", "missed targets", "revenue decline", "layoffs", "restructuring",
    "pivot", "under pressure", "challenges",
]

COMPETITOR_TECHS = {
    "outreach", "salesloft", "apollo", "lemlist", "mailshake",
    "reply.io", "zoominfo", "groove", "yesware", "mixmax",
}


async def derive_intent_signals(
    company_name: Optional[str],
    company_news: list,
    tech_stack: list,
) -> dict:
    """Derive buying intent signals from enrichment data.
    
    Analyses real news headlines and tech stack to produce an actionable
    intent score and breakdown of signals for the reasoning agent.
    """
    intent = {
        "funding_recent": False,
        "funding_details": None,
        "hiring_sales_team": False,
        "hiring_count": 0,
        "growth_signal": False,
        "growth_details": None,
        "pain_signal": False,
        "tech_replacement_signals": [],
        "competitor_using": [],
        "intent_score": 0,
        "signal_breakdown": [],
    }

    # ── Analyse each news headline ────────────────────────────────────────────
    for item in company_news or []:
        headline = (item.get("headline") or "").lower()
        summary = (item.get("summary") or "").lower()
        text = headline + " " + summary

        # Funding signals (highest intent — companies buying tools after raising)
        if any(kw in text for kw in FUNDING_KEYWORDS):
            if not intent["funding_recent"]:
                intent["funding_recent"] = True
                intent["funding_details"] = item.get("headline")
                intent["intent_score"] += 35
                intent["signal_breakdown"].append({
                    "type": "funding",
                    "detail": item.get("headline"),
                    "score_added": 35,
                })

        # Hiring signals (expanding team = buying tools to support them)
        if any(kw in text for kw in HIRING_KEYWORDS):
            sales_hiring = any(
                k in text for k in ["sales", "sdr", "bdr", "revenue", "account executive"]
            )
            if sales_hiring:
                intent["hiring_sales_team"] = True
                intent["hiring_count"] = _extract_hiring_count(text)
                intent["intent_score"] += 25
                intent["signal_breakdown"].append({
                    "type": "sales_hiring",
                    "detail": item.get("headline"),
                    "score_added": 25,
                })
            else:
                intent["hiring_count"] = max(intent["hiring_count"], 2)
                intent["intent_score"] += 10
                intent["signal_breakdown"].append({
                    "type": "hiring",
                    "detail": item.get("headline"),
                    "score_added": 10,
                })

        # Growth signals
        if any(kw in text for kw in GROWTH_KEYWORDS) and not intent["growth_signal"]:
            intent["growth_signal"] = True
            intent["growth_details"] = item.get("headline")
            intent["intent_score"] += 15
            intent["signal_breakdown"].append({
                "type": "growth",
                "detail": item.get("headline"),
                "score_added": 15,
            })

        # Pain signals (negative — may indicate budget pressure)
        if any(kw in text for kw in PAIN_KEYWORDS):
            intent["pain_signal"] = True
            intent["intent_score"] -= 10
            intent["signal_breakdown"].append({
                "type": "pain",
                "detail": item.get("headline"),
                "score_added": -10,
            })

    # ── Tech stack replacement signals ────────────────────────────────────────
    for tech in tech_stack or []:
        tech_lower = tech.lower()
        if tech_lower in COMPETITOR_TECHS:
            if tech not in intent["tech_replacement_signals"]:
                intent["tech_replacement_signals"].append(tech)
                intent["competitor_using"].append(tech)
                intent["intent_score"] += 12
                intent["signal_breakdown"].append({
                    "type": "competitor_tech",
                    "detail": f"Currently using {tech}",
                    "score_added": 12,
                })

    # ── Clamp score to 0-100 ─────────────────────────────────────────────────
    intent["intent_score"] = max(0, min(intent["intent_score"], 100))

    logger.debug(
        "Intent signals for %s: score=%d signals=%d",
        company_name, intent["intent_score"], len(intent["signal_breakdown"])
    )
    return intent


def _extract_hiring_count(text: str) -> int:
    """Try to extract a headcount number from hiring news text."""
    patterns = [
        r"hiring\s+(\d+)",
        r"adding\s+(\d+)",
        r"(\d+)\s+new\s+hires",
        r"(\d+)\s+open\s+positions",
        r"(\d+)\s+roles",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return int(m.group(1))
    return 3  # Default assumption when we know hiring is happening but count is unclear
