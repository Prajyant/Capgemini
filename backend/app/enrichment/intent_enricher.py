"""
Buying intent signals.

Scores 0-100 with explainable reasons. Inputs are best-effort; missing data
just means lower score, never an error.

Score buckets (capped, summed, then min(100)):
  • Recent funding/IPO news    → up to 30 (recency-weighted)
  • Hiring activity            → up to 25 (count-weighted)
  • Tech replacement signals   → up to 30 (per competitor tool present)
  • Senior decision-maker      → up to 10
  • Buyer engagement           → up to 35 (replies > clicks > opens)

The engagement bucket is the most important signal — what the buyer is
*actually doing* with our outreach beats anything we infer about the company.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)

# ── Tunables ──────────────────────────────────────────────────────────────
_CAP_FUNDING = 30
_CAP_HIRING = 25
_CAP_TECH = 30
_CAP_SENIORITY = 10
_CAP_ENGAGEMENT = 35

COMPETITOR_TECHS = {
    "outreach", "salesloft", "apollo", "lemlist",
    "reply.io", "mailshake", "lusha", "zoominfo",
}

FUNDING_KEYWORDS = (
    "raised", "raises", "series a", "series b", "series c", "series d",
    "funding round", "seed round", "ipo", "secures funding", "closes round",
)
HIRING_KEYWORDS = (
    "hiring", "we're hiring", "expanding team", "growing team",
    "headcount", "now hiring", "open roles", "scaling the team",
)


# ── Helpers ───────────────────────────────────────────────────────────────
def _to_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _days_ago(value: Any) -> Optional[int]:
    dt = _to_dt(value)
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    return max(0, int(delta.total_seconds() // 86400))


def _attr(obj: Any, key: str) -> Any:
    """Read a field from either a dict or an ORM object."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


# ── Public API ────────────────────────────────────────────────────────────
async def derive_intent_signals(
    company_name: Optional[str],
    company_news: Optional[list],
    tech_stack: Optional[list],
    *,
    seniority_level: Optional[str] = None,
    engagement_events: Optional[Iterable[Any]] = None,
) -> dict:
    """Compute buying intent. ``engagement_events`` items may be ORM rows or dicts."""
    intent: dict[str, Any] = {
        "funding_recent": False,
        "hiring_count": 0,
        "tech_replacement_signals": [],
        "engagement_signals": [],
        "reasons": [],
        "intent_score": 0,
    }
    score = 0

    news = company_news or []
    techs = tech_stack or []
    events = list(engagement_events or [])

    # Funding — fire once, weighted by recency
    for item in news:
        headline = (item.get("headline") or "").lower()
        if any(kw in headline for kw in FUNDING_KEYWORDS):
            intent["funding_recent"] = True
            recency = _days_ago(item.get("published_at"))
            boost = _CAP_FUNDING if (recency is not None and recency <= 90) else 18
            score += boost
            intent["reasons"].append(f"Funding/IPO news: {item.get('headline')}")
            break

    # Hiring — count actual matches, not a hardcoded constant
    hires = sum(
        1
        for item in news
        if any(kw in (item.get("headline") or "").lower() for kw in HIRING_KEYWORDS)
    )
    if hires:
        intent["hiring_count"] = hires
        score += min(5 + hires * 5, _CAP_HIRING)
        intent["reasons"].append(f"Hiring activity: {hires} signal(s) in news")

    # Tech replacement — competitor tooling already in their stack
    tech_score = 0
    for tech in techs:
        if (tech or "").strip().lower() in COMPETITOR_TECHS:
            intent["tech_replacement_signals"].append(tech)
            tech_score += 10
    if intent["tech_replacement_signals"]:
        score += min(tech_score, _CAP_TECH)
        intent["reasons"].append(
            "Using replaceable tech: "
            + ", ".join(intent["tech_replacement_signals"])
        )

    # Seniority — decision-makers carry more intent weight
    if seniority_level in ("C-Level", "VP", "Director", "Founder"):
        score += _CAP_SENIORITY
        intent["reasons"].append(f"Senior decision-maker: {seniority_level}")

    # Buyer engagement — strongest signal we have
    eng_score = _engagement_score(events, intent)
    score += min(eng_score, _CAP_ENGAGEMENT)

    intent["intent_score"] = max(0, min(int(score), 100))
    return intent


def _engagement_score(events: list, intent: dict) -> int:
    """Score what the buyer has *actually done* with our outreach."""
    if not events:
        return 0

    has_replied_pos = False
    replied = False
    clicked = 0
    opened = 0
    bounced = False
    most_recent: Optional[int] = None

    for e in events:
        et = _attr(e, "event_type")
        days = _days_ago(_attr(e, "occurred_at"))
        if days is not None:
            most_recent = days if most_recent is None else min(most_recent, days)

        if et == "replied":
            replied = True
            sentiment = (_attr(e, "reply_sentiment") or "").lower()
            rintent = (_attr(e, "reply_intent") or "").lower()
            if sentiment == "positive" or rintent in ("interested", "meeting_requested"):
                has_replied_pos = True
        elif et == "clicked":
            clicked += 1
        elif et == "opened":
            opened += 1
        elif et in ("bounced", "spam"):
            bounced = True

    score = 0
    if has_replied_pos:
        score += 25
        intent["engagement_signals"].append("positive_reply")
        intent["reasons"].append("Buyer replied with positive intent")
    elif replied:
        score += 15
        intent["engagement_signals"].append("replied")
        intent["reasons"].append("Buyer replied")

    if clicked:
        score += min(6 + clicked * 3, 12)
        intent["engagement_signals"].append(f"clicked_{clicked}x")
        intent["reasons"].append(f"Buyer clicked link {clicked} time(s)")

    if opened >= 3:
        score += 10
        intent["engagement_signals"].append(f"opened_{opened}x")
        intent["reasons"].append(f"Multiple opens ({opened})")
    elif opened:
        score += 5
        intent["engagement_signals"].append(f"opened_{opened}x")
        intent["reasons"].append(f"Email opened ({opened})")

    if most_recent is not None and most_recent <= 14 and score > 0:
        score += 5
        intent["reasons"].append("Recent buyer activity (≤14 days)")

    if bounced:
        # Bounce/spam indicates a bad address — not a real intent signal.
        score = max(0, score - 10)
        intent["engagement_signals"].append("bounced")

    return score
