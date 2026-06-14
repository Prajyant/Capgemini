"""
LinkedIn enrichment.

This module integrates with the Scrapingdog LinkedIn Profile API (Freemium).
If no LINKEDIN_API_KEY is configured in the environment settings, it gracefully
degrades to returning plausible synthetic signals to prevent pipeline failure.
"""
import logging
import re
import httpx
from typing import Optional
from datetime import datetime, timezone
from app.config import settings

logger = logging.getLogger(__name__)

USER_AGENT = "SalesAgentAI/1.0 (+enrichment)"
HTTP_TIMEOUT = 12.0


def extract_linkedin_id(url: str) -> Optional[str]:
    """Extract the LinkedIn handle/ID from a profile URL."""
    if not url:
        return None
    # Normalize url: strip query parameters and trailing slashes
    url = url.split("?")[0].rstrip("/")
    match = re.search(r"/in/([^/]+)$", url)
    if match:
        return match.group(1)
    return None


def parse_tenure_months(experience: list) -> int:
    """Estimate tenure at current company in months from Scrapingdog experiences."""
    if not experience:
        return 12
    try:
        first_job = experience[0]
        duration = first_job.get("duration", "")
        if "Present" in duration:
            start_part = duration.split("-")[0].strip()  # e.g., "Jan 2020"
            months_map = {
                "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
            }
            parts = start_part.split()
            if len(parts) == 2:
                month_str = parts[0].lower()[:3]
                year_str = parts[1]
                month = months_map.get(month_str, 1)
                year = int(year_str)
                
                now = datetime.now(timezone.utc)
                total_months = (now.year - year) * 12 + (now.month - month)
                return max(1, total_months)
    except Exception as e:
        logger.debug("Failed parsing tenure from duration: %s", e)
    return 12


def extract_topics(headline: str, about: str) -> list[str]:
    """Infer topics from headline and about text."""
    text = f"{headline or ''} {about or ''}".lower()
    keywords = ["ai", "gtm", "saas", "sales", "marketing", "product", "devops", "cloud", "engineering", "recruiting"]
    found = [k.upper() if k in ("ai", "gtm", "saas") else k.capitalize() for k in keywords if k in text]
    return found[:3] if found else ["GTM", "Sales"]


async def fetch_linkedin_signals(linkedin_url: Optional[str], job_title: Optional[str] = None) -> dict:
    """Return LinkedIn-derived signals for the lead using Scrapingdog (falls back to mock if no key)."""
    if not linkedin_url:
        return {}

    # Check if API Key is configured
    if not settings.LINKEDIN_API_KEY:
        logger.info("LINKEDIN_API_KEY missing — returning mock LinkedIn signals")
        return {
            "tenure_months": 18,
            "post_frequency": "monthly",
            "recent_post_topics": ["sales enablement", "AI in GTM"],
            "connections_count": "500+",
            "is_active": True,
            "source": "synthetic",
        }

    profile_id = extract_linkedin_id(linkedin_url)
    if not profile_id:
        logger.warning("Could not parse profile ID from LinkedIn URL: %s", linkedin_url)
        return {}

    api_url = "https://api.scrapingdog.com/profile/"
    params = {
        "api_key": settings.LINKEDIN_API_KEY,
        "id": profile_id,
        "type": "profile"
    }

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            logger.info("Querying Scrapingdog for LinkedIn ID: %s", profile_id)
            r = await client.get(api_url, params=params, headers={"User-Agent": USER_AGENT})
            
            if r.status_code == 200:
                data = r.json()
                experience = data.get("experience", [])
                headline = data.get("headline", "")
                about = data.get("about", "")
                
                return {
                    "tenure_months": parse_tenure_months(experience),
                    "post_frequency": "weekly" if len(about) > 100 else "monthly",
                    "recent_post_topics": extract_topics(headline, about),
                    "connections_count": data.get("connections", "500+"),
                    "is_active": True,
                    "source": "scrapingdog",
                }
            elif r.status_code == 202:
                logger.info("Scrapingdog accepted request but is scraping (202). Returning fallback.")
            else:
                logger.warning("Scrapingdog failed with status code %s: %s", r.status_code, r.text)
    except Exception as e:
        logger.error("Scrapingdog LinkedIn fetch failed: %s", e)

    # Return safe fallback if the API fails or is rate-limited
    return {
        "tenure_months": 12,
        "post_frequency": "monthly",
        "recent_post_topics": ["GTM", "Sales"],
        "connections_count": "500+",
        "is_active": True,
        "source": "scrapingdog_fallback",
    }

