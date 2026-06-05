"""Tech stack enrichment via BuiltWith. Graceful degradation if missing."""
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def fetch_tech_stack(domain: str) -> list[str]:
    """Return list of technologies the company uses. Empty list on failure."""
    if not settings.BUILTWITH_API_KEY:
        logger.info("BUILTWITH_API_KEY missing — skipping tech stack enrichment")
        return []
    if not domain:
        return []

    url = "https://api.builtwith.com/free1/api.json"
    params = {"KEY": settings.BUILTWITH_API_KEY, "LOOKUP": domain}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        groups = data.get("groups", [])
        techs: set[str] = set()
        for g in groups:
            for cat in g.get("categories", []):
                for tech in cat.get("technologies", []):
                    name = tech.get("name") if isinstance(tech, dict) else tech
                    if name:
                        techs.add(name)
        return sorted(techs)[:25]
    except Exception as e:
        logger.warning("Tech stack enrichment failed for %s: %s", domain, e)
        return []
