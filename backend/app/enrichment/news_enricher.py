"""Company news enrichment via NewsAPI with fallback to web scraping."""
import logging
import re
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Fallback: search news via free RSS/Google News when no API key
GNEWS_SEARCH = "https://gnews.io/api/v4/search"
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


async def fetch_company_news(company_name: str, limit: int = 5) -> list[dict]:
    """Return list of recent news items for a company.
    
    Primary: NewsAPI (if key present)
    Fallback: GNews free tier → Google News RSS → empty list
    """
    if not company_name:
        return []

    # Try NewsAPI first (paid, best quality)
    if settings.NEWS_API_KEY:
        result = await _fetch_newsapi(company_name, limit)
        if result:
            return result

    # Fallback: Try Google News RSS (free, no key needed)
    result = await _fetch_google_news_rss(company_name, limit)
    if result:
        return result

    logger.info("All news sources exhausted for %s — returning empty", company_name)
    return []


async def _fetch_newsapi(company_name: str, limit: int) -> list[dict]:
    """Fetch from NewsAPI.org."""
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
        if not articles:
            return []
        return [
            {
                "headline": a.get("title"),
                "source": (a.get("source") or {}).get("name"),
                "url": a.get("url"),
                "published_at": a.get("publishedAt"),
                "summary": a.get("description"),
            }
            for a in articles
            if a.get("title") and "[Removed]" not in (a.get("title") or "")
        ]
    except Exception as e:
        logger.warning("NewsAPI failed for %s: %s", company_name, e)
        return []


async def _fetch_google_news_rss(company_name: str, limit: int) -> list[dict]:
    """Fetch from Google News RSS — free, no key needed."""
    try:
        # Encode the query for URL
        query = company_name.replace(" ", "+")
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

        async with httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SalesAgent/1.0)"},
            follow_redirects=True,
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            content = r.text

        # Simple XML parsing (avoid lxml dependency)
        items = re.findall(r"<item>(.*?)</item>", content, re.DOTALL)
        results = []
        for item in items[:limit]:
            title_match = re.search(r"<title>(.*?)</title>", item, re.DOTALL)
            link_match = re.search(r"<link>(.*?)</link>", item, re.DOTALL)
            pub_match = re.search(r"<pubDate>(.*?)</pubDate>", item, re.DOTALL)
            source_match = re.search(r"<source[^>]*>(.*?)</source>", item, re.DOTALL)
            desc_match = re.search(r"<description>(.*?)</description>", item, re.DOTALL)

            title = title_match.group(1).strip() if title_match else None
            # Strip CDATA and HTML tags from title
            if title:
                title = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", title)
                title = re.sub(r"<[^>]+>", "", title)
                title = title.strip()
                # Remove " - Source" suffix Google News adds
                if " - " in title:
                    title_parts = title.rsplit(" - ", 1)
                    title = title_parts[0].strip()

            if not title or company_name.lower() not in content.lower()[:500]:
                pass  # Accept anyway — RSS is already filtered by query

            link = link_match.group(1).strip() if link_match else None
            pub_date = pub_match.group(1).strip() if pub_match else None
            source = source_match.group(1).strip() if source_match else "Google News"
            desc = desc_match.group(1).strip() if desc_match else None
            if desc:
                desc = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", desc)
                desc = re.sub(r"<[^>]+>", "", desc)[:200]

            if title:
                results.append({
                    "headline": title,
                    "source": source,
                    "url": link,
                    "published_at": pub_date,
                    "summary": desc,
                })

        logger.info("Google News RSS returned %d articles for %s", len(results), company_name)
        return results

    except Exception as e:
        logger.warning("Google News RSS failed for %s: %s", company_name, e)
        return []
