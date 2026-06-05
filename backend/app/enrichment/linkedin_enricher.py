"""
LinkedIn enrichment.

This is a stub — real LinkedIn API access requires partner status. In production
this would integrate with a provider like Proxycurl or Apollo. For the demo,
this returns plausible synthetic signals based on the lead's job title.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def fetch_linkedin_signals(linkedin_url: Optional[str], job_title: Optional[str] = None) -> dict:
    """Return LinkedIn-derived signals for the lead."""
    if not linkedin_url:
        return {}
    # Synthetic signals so the agent has something to reason about.
    # Real implementation would call Proxycurl / Apollo / similar provider.
    return {
        "tenure_months": 18,
        "post_frequency": "monthly",
        "recent_post_topics": ["sales enablement", "AI in GTM"],
        "connections_count": "500+",
        "is_active": True,
        "source": "synthetic" if not linkedin_url else "linkedin_url_present",
    }
