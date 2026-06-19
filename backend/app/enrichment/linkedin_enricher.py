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


async def fetch_full_profile(linkedin_url: Optional[str]) -> dict:
    """
    Fetch full LinkedIn profile data (name, headline, company, experience, etc.)
    Returns a dict with all available profile fields.
    Falls back to minimal data extracted from the URL if no API key or on failure.
    """
    if not linkedin_url:
        return {}

    profile_id = extract_linkedin_id(linkedin_url)
    if not profile_id:
        logger.warning("Could not parse profile ID from LinkedIn URL: %s", linkedin_url)
        return {}

    if not settings.LINKEDIN_API_KEY:
        logger.info("LINKEDIN_API_KEY missing — returning minimal profile from URL slug")
        # Parse name from URL slug (e.g., "alaguraja-narayanan-459945" -> "Alaguraja Narayanan")
        name_parts = profile_id.split("-")
        # Filter out numeric suffixes
        name_parts = [p.capitalize() for p in name_parts if not p.isdigit()]
        return {
            "first_name": name_parts[0] if name_parts else "Unknown",
            "last_name": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
            "headline": "",
            "job_title": "",
            "company_name": "",
            "industry": "",
            "location": "",
            "about": "",
            "experience": [],
            "connections": "500+",
            "source": "url_parsed",
        }

    api_url = "https://api.scrapingdog.com/profile/"
    params = {
        "api_key": settings.LINKEDIN_API_KEY,
        "type": "profile",
        "id": profile_id,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            logger.info("Fetching full LinkedIn profile for: %s", profile_id)
            logger.info("Using API URL: %s with id=%s", api_url, profile_id)
            # Retry once with a delay if first attempt fails
            for attempt in range(2):
                r = await client.get(api_url, params=params, headers={"User-Agent": USER_AGENT})
                logger.info("Scrapingdog response status: %s", r.status_code)

                if r.status_code == 200:
                    data = r.json()
                    # Scrapingdog may return a list — unwrap if needed
                    if isinstance(data, list):
                        if len(data) > 0:
                            data = data[0]
                        else:
                            logger.warning("Scrapingdog returned empty list")
                            break
                    logger.info("Scrapingdog raw keys: %s", list(data.keys()) if isinstance(data, dict) else type(data))

                    # Scrapingdog field names: fullName, first_name, last_name, headline, location, etc.
                    first_name = data.get("first_name", "") or ""
                    last_name = data.get("last_name", "") or ""
                    # Fallback to fullName if first/last are empty
                    if not first_name and not last_name:
                        full_name = data.get("fullName", "") or data.get("name", "") or ""
                        name_parts = full_name.strip().split(" ", 1)
                        first_name = name_parts[0] if name_parts else ""
                        last_name = name_parts[1] if len(name_parts) > 1 else ""

                    headline = data.get("headline", "") or ""

                    # Extract current company from experience
                    experience = data.get("experience", [])
                    # Filter out empty dicts
                    experience = [e for e in experience if e and isinstance(e, dict) and any(e.values())]
                    current_company = ""
                    current_title = ""
                    if experience:
                        # Scrapingdog experience fields: title, company, company_url, duration, location
                        current_company = experience[0].get("company", "") or experience[0].get("company_name", "") or ""
                        current_title = experience[0].get("title", "") or ""

                    # If no explicit title from experience, try headline
                    if not current_title and headline:
                        if " at " in headline:
                            current_title = headline.split(" at ")[0].strip()
                            if not current_company:
                                current_company = headline.split(" at ")[1].strip()
                        else:
                            current_title = headline

                    # If still no company, try from headline
                    if not current_company and headline and " at " in headline:
                        current_company = headline.split(" at ")[-1].strip()

                    location = data.get("location", "") or ""
                    about = data.get("about", "") or ""
                    connections = data.get("connections", "") or data.get("followers", "") or "500+"

                    logger.info("Parsed: %s %s | %s | %s | %s", first_name, last_name, current_title, current_company, location)

                    return {
                        "first_name": first_name,
                        "last_name": last_name,
                        "headline": headline,
                        "job_title": current_title or headline or "Professional",
                        "company_name": current_company,
                        "industry": data.get("industry", "") or "",
                        "location": location,
                        "about": about,
                        "experience": experience,
                        "connections": connections,
                        "source": "scrapingdog",
                    }
                elif r.status_code == 429:
                    logger.warning("Rate limited (429). Response: %s", r.text)
                    if attempt == 0:
                        logger.info("Waiting 10s before retry...")
                        import asyncio as _asyncio
                        await _asyncio.sleep(10)
                        continue
                    else:
                        logger.warning("Still rate limited after retry.")
                elif r.status_code == 202:
                    logger.info("Scrapingdog accepted (202) but still scraping. Returning URL-parsed fallback.")
                    break
                else:
                    logger.warning("Scrapingdog profile fetch failed (%s): %s", r.status_code, r.text)
                    break
    except Exception as e:
        logger.error("Scrapingdog full profile fetch failed: %s", e)

    # Fallback: parse from URL slug
    name_parts = profile_id.split("-")
    name_parts = [p.capitalize() for p in name_parts if not p.isdigit()]
    return {
        "first_name": name_parts[0] if name_parts else "Unknown",
        "last_name": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
        "headline": "",
        "job_title": "",
        "company_name": "",
        "industry": "",
        "location": "",
        "about": "",
        "experience": [],
        "connections": "500+",
        "source": "scrapingdog_fallback",
    }


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
        "type": "profile",
        "premium": "true"
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

