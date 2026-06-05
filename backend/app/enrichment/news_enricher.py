"""Company news enrichment via NewsAPI. Graceful degradation if key missing."""
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def fetch_company_news(company_name: str, limit: int = 5) -> list[dict]:
    """Return list of recent news items for a company. Empty list on failure."""
    if not settings.NEWS_API_KEY:
        logger.info("NEWS_API_KEY missing — skipping news enrichment")
        return []
    if not company_name:
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": f'"{company_name}"',
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": limit,
        "apiKey": settings.NEWS_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        articles = data.get("articles", [])
        return [
            {
                "headline": a.get("title"),
                "source": (a.get("source") or {}).get("name"),
                "url": a.get("url"),
                "published_at": a.get("publishedAt"),
                "summary": a.get("description"),
            }
            for a in articles
        ]
    except Exception as e:
        logger.warning("News enrichment failed for %s: %s", company_name, e)
        return []
