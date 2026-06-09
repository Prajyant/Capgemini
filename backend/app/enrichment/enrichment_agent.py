"""
Enrichment orchestrator — fans out to all enrichment sources in parallel.

Graceful degradation: if any source fails, we continue with reduced data
and a lower enrichment score, but never block the lead.
"""
import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enrichment.linkedin_enricher import fetch_linkedin_signals
from app.enrichment.news_enricher import fetch_company_news
from app.enrichment.techstack_enricher import fetch_tech_stack
from app.enrichment.intent_enricher import derive_intent_signals
from app.models import Lead, Company
from app.redis_client import publish_event, push_activity

logger = logging.getLogger(__name__)


def _compute_enrichment_score(
    linkedin: dict,
    news: list,
    tech: list,
    intent: dict,
) -> int:
    """0-100 richness score based on how much data we successfully gathered."""
    score = 0
    if linkedin:
        score += 20
    if news:
        score += min(len(news) * 8, 30)
    if tech:
        score += min(len(tech) * 2, 30)
    if intent.get("intent_score", 0) > 0:
        score += 20
    return min(score, 100)


def _compute_icp_fit(company: Company | None, lead: Lead) -> int:
    """Simple ICP fit heuristic: target = SaaS, 50-500 employees, decision-maker."""
    score = 50  # Baseline
    if company:
        if company.employee_count and 50 <= company.employee_count <= 500:
            score += 20
        if company.industry and any(k in (company.industry or "").lower() for k in ["saas", "software", "tech"]):
            score += 15
        if company.funding_stage in ("Series A", "Series B", "Series C"):
            score += 10
    if lead.seniority_level in ("VP", "C-Level", "Director", "Founder"):
        score += 5
    return min(score, 100)


async def enrich_lead(db: AsyncSession, lead_id: UUID) -> dict:
    """
    Run full enrichment for a lead. Updates the Lead and Company rows.
    Returns a summary of the enrichment result.
    """
    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")

    lead.enrichment_status = "running"
    await db.flush()

    company = lead.company
    company_name = company.name if company else None
    company_domain = company.domain if company else None

    # Fan out — all best-effort
    results = await asyncio.gather(
        fetch_linkedin_signals(lead.linkedin_url, lead.job_title),
        fetch_company_news(company_name) if company_name else _empty_list(),
        fetch_tech_stack(company_domain) if company_domain else _empty_list(),
        return_exceptions=True,
    )
    linkedin = results[0] if not isinstance(results[0], Exception) else {}
    news = results[1] if not isinstance(results[1], Exception) else []
    tech = results[2] if not isinstance(results[2], Exception) else []

    intent = await derive_intent_signals(
        company_name,
        news,
        tech,
        seniority_level=lead.seniority_level,
        engagement_events=lead.email_events or [],
    )

    lead.linkedin_signals = linkedin
    lead.company_news = news
    lead.tech_stack = tech
    lead.intent_signals = intent
    lead.enrichment_score = _compute_enrichment_score(linkedin, news, tech, intent)
    lead.enrichment_status = "complete"

    if company:
        if not company.tech_stack:
            company.tech_stack = tech
        if not company.recent_news:
            company.recent_news = news
        company.intent_score = intent.get("intent_score", 0)
        company.icp_fit_score = _compute_icp_fit(company, lead)

    if lead.state == "new":
        lead.state = "enriched"
        lead.state_updated_at = datetime.now(timezone.utc)

    await db.flush()

    activity = {
        "type": "enrichment",
        "lead_id": str(lead.id),
        "lead_name": f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
        "score": lead.enrichment_score,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await push_activity(activity)
        await publish_event("leads.enriched", activity)
    except Exception:
        pass

    return {
        "lead_id": str(lead.id),
        "enrichment_score": lead.enrichment_score,
        "intent_score": intent.get("intent_score", 0),
        "news_count": len(news),
        "tech_count": len(tech),
    }


async def _empty_list():
    return []


async def recompute_intent_for_lead(db: AsyncSession, lead: Lead) -> dict:
    """
    Re-derive intent signals for a lead using the latest engagement history.

    Used by webhooks after a buyer-side event (open/click/reply) so the buying
    intent score reflects what the buyer actually does, not just static news.
    Caller is responsible for committing.
    """
    company = lead.company
    news = lead.company_news or (company.recent_news if company else None) or []
    tech = lead.tech_stack or (company.tech_stack if company else None) or []

    intent = await derive_intent_signals(
        company.name if company else None,
        news,
        tech,
        seniority_level=lead.seniority_level,
        engagement_events=lead.email_events or [],
    )
    lead.intent_signals = intent
    if company:
        company.intent_score = intent.get("intent_score", 0)
    return intent
