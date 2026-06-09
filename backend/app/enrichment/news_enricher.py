"""Company news enrichment using free, open-source news sources.

Sources (in priority order):
  1. NewsAPI       — only if ``NEWS_API_KEY`` is configured (legacy / optional).
  2. Google News RSS — free, no API key required. Default open-source path.
  3. GDELT 2.0 Doc API — free, no API key. Fallback if Google News fails.

Designed for graceful degradation: any failure falls through to the next
source, and an empty list is returned only if all sources fail. This module
never raises — the enrichment pipeline must keep moving.
"""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

USER_AGENT = "SalesAgentAI/1.0 (+enrichment)"
HTTP_TIMEOUT = 10.0
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: Optional[str]) -> Optional[str]:
    """Remove HTML tags and decode entities (Google News wraps in <a>...</a>)."""
    if not text:
        return None
    cleaned = _HTML_TAG_RE.sub("", text)
    cleaned = html.unescape(cleaned)
    # Collapse repeated whitespace introduced by entity decoding (&nbsp; etc.)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None


def _rfc822_to_iso(date_str: Optional[str]) -> Optional[str]:
    """Convert RSS RFC-822 date (e.g. 'Mon, 15 Jan 2024 12:00:00 GMT') to ISO-8601."""
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return date_str


def _gdelt_date_to_iso(date_str: Optional[str]) -> Optional[str]:
    """Convert GDELT seendate ('20240115T120000Z') to ISO-8601."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return date_str


async def _fetch_google_news_rss(
    client: httpx.AsyncClient, company_name: str, limit: int
) -> list[dict]:
    """Fetch from Google News RSS — free, no key, broad source coverage."""
    query = quote_plus(f'"{company_name}"')
    url = (
        f"https://news.google.com/rss/search?"
        f"q={query}&hl=en-US&gl=US&ceid=US:en"
    )
    r = await client.get(url, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()

    # RSS 2.0 — items live at /rss/channel/item
    root = ET.fromstring(r.content)
    items = root.findall("./channel/item")[:limit]

    out: list[dict] = []
    for item in items:
        source_el = item.find("source")
        out.append(
            {
                "headline": (item.findtext("title") or "").strip() or None,
                "source": source_el.text if source_el is not None else None,
                "url": (item.findtext("link") or "").strip() or None,
                "published_at": _rfc822_to_iso(item.findtext("pubDate")),
                "summary": _strip_html(item.findtext("description")),
            }
        )
    return out


async def _fetch_gdelt(
    client: httpx.AsyncClient, company_name: str, limit: int
) -> list[dict]:
    """Fetch from GDELT 2.0 Doc API — free, no key. Used as fallback."""
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": f'"{company_name}"',
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(limit),
        "sort": "DateDesc",
    }
    r = await client.get(url, params=params, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()

    try:
        data = r.json()
    except ValueError:
        # GDELT occasionally returns non-JSON when query is malformed
        return []

    return [
        {
            "headline": a.get("title"),
            "source": a.get("domain"),
            "url": a.get("url"),
            "published_at": _gdelt_date_to_iso(a.get("seendate")),
            "summary": None,
        }
        for a in (data.get("articles") or [])[:limit]
    ]


async def _fetch_newsapi(
    client: httpx.AsyncClient, company_name: str, limit: int
) -> list[dict]:
    """Legacy NewsAPI source — only invoked if NEWS_API_KEY is configured."""
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": f'"{company_name}"',
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": limit,
        "apiKey": settings.NEWS_API_KEY,
    }
    r = await client.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    return [
        {
            "headline": a.get("title"),
            "source": (a.get("source") or {}).get("name"),
            "url": a.get("url"),
            "published_at": a.get("publishedAt"),
            "summary": a.get("description"),
        }
        for a in data.get("articles", [])
    ]


async def fetch_company_news(company_name: str, limit: int = 5) -> list[dict]:
    """Return recent news items for a company.

    Tries (in order): NewsAPI (if key set) → Google News RSS → GDELT.
    Always returns a list (possibly empty); never raises.
    """
    if not company_name:
        return []

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        # 1. NewsAPI — only if the user has a key configured.
        if settings.NEWS_API_KEY:
            try:
                items = await _fetch_newsapi(client, company_name, limit)
                if items:
                    return items
                logger.info(
                    "NewsAPI returned no results for %s — trying open sources",
                    company_name,
                )
            except Exception as e:
                logger.warning(
                    "NewsAPI failed for %s: %s — falling back to open sources",
                    company_name,
                    e,
                )

        # 2. Google News RSS — primary open-source path.
        try:
            items = await _fetch_google_news_rss(client, company_name, limit)
            if items:
                return items
            logger.info(
                "Google News RSS returned no results for %s — trying GDELT",
                company_name,
            )
        except Exception as e:
            logger.warning(
                "Google News RSS failed for %s: %s — trying GDELT", company_name, e
            )

        # 3. GDELT fallback.
        try:
            return await _fetch_gdelt(client, company_name, limit)
        except Exception as e:
            logger.warning("GDELT also failed for %s: %s", company_name, e)
            return []
