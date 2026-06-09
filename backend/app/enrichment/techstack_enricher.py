"""Tech stack enrichment via BuiltWith with free fallback via website meta detection."""
import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Common tech stack signatures detectable from homepage HTML/headers
TECH_SIGNATURES = {
    "HubSpot": ["hubspot.com", "hs-scripts", "hbspt"],
    "Salesforce": ["force.com", "salesforce", "sfdc"],
    "Intercom": ["intercom.io", "widget.intercom.io"],
    "Drift": ["drift.com", "js.driftt.com"],
    "Segment": ["analytics.js", "segment.io", "cdn.segment.com"],
    "Google Analytics": ["google-analytics.com", "gtag/js", "UA-"],
    "Mixpanel": ["mixpanel.com", "mixpanel.min.js"],
    "Amplitude": ["amplitude.com", "cdn.amplitude.com"],
    "Hotjar": ["hotjar.com", "static.hotjar"],
    "Stripe": ["stripe.com", "js.stripe.com"],
    "Zendesk": ["zendesk.com", "zopim.com"],
    "Freshdesk": ["freshdesk.com", "freshchat"],
    "Notion": ["notion.so", "notion.site"],
    "Linear": ["linear.app"],
    "Jira": ["atlassian.com", "jira"],
    "GitHub": ["github.com", "github.io"],
    "Vercel": ["vercel.app", "vercel.com"],
    "AWS": ["amazonaws.com", "aws-amplify", "cloudfront.net"],
    "GCP": ["googleapis.com", "googletagmanager"],
    "Azure": ["azure.com", "azureedge.net"],
    "Cloudflare": ["cloudflare.com", "__cf_bm"],
    "Webpack": ["webpack", "bundle.js"],
    "React": ["react", "_react"],
    "Next.js": ["_next/", "next/dist"],
    "Vue.js": ["vue.min.js", "vue.global"],
    "Angular": ["angular.min.js", "ng-version"],
    "WordPress": ["wp-content", "wp-includes", "wordpress"],
    "Shopify": ["shopify.com", "cdn.shopify"],
    "Outreach": ["outreach.io"],
    "SalesLoft": ["salesloft.com"],
    "Apollo": ["apollo.io"],
    "ZoomInfo": ["zoominfo.com"],
}


async def fetch_tech_stack(domain: str) -> list[str]:
    """Return list of technologies the company uses.

    Primary: BuiltWith API (if key present)
    Fallback: Lightweight website scan for known tech signatures
    """
    if not domain:
        return []

    if settings.BUILTWITH_API_KEY:
        result = await _fetch_builtwith(domain)
        if result:
            return result

    # Free fallback: scan the company website
    result = await _detect_from_website(domain)
    return result


async def _fetch_builtwith(domain: str) -> list[str]:
    """Fetch tech stack via BuiltWith API."""
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
        logger.warning("BuiltWith failed for %s: %s", domain, e)
        return []


async def _detect_from_website(domain: str) -> list[str]:
    """Scan website HTML/headers for known tech signatures."""
    # Try https first, then http
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        try:
            async with httpx.AsyncClient(
                timeout=8.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
                follow_redirects=True,
            ) as client:
                r = await client.get(url)
                html = r.text.lower()
                headers_str = str(r.headers).lower()
                combined = html + headers_str

            detected: list[str] = []
            for tech, signatures in TECH_SIGNATURES.items():
                for sig in signatures:
                    if sig.lower() in combined:
                        detected.append(tech)
                        break

            # Also check response headers for common indicators
            server = r.headers.get("server", "").lower()
            if "cloudflare" in server:
                if "Cloudflare" not in detected:
                    detected.append("Cloudflare")
            x_powered = r.headers.get("x-powered-by", "").lower()
            if "php" in x_powered:
                detected.append("PHP")
            if "express" in x_powered:
                detected.append("Node.js / Express")

            if detected:
                logger.info("Website scan detected %d techs for %s", len(detected), domain)
                return sorted(set(detected))[:20]

        except Exception as e:
            logger.debug("Website scan failed for %s://%s: %s", scheme, domain, e)
            continue

    logger.info("Tech stack detection yielded no results for %s", domain)
    return []
