"""
Decision orchestration: runs reasoning, persists the decision, executes the action.

This is the entry point used by API routes and Celery tasks.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.reasoning_engine import run_reasoning
from app.config import settings
from app.models import Lead, EmailEvent, AgentDecision
from app.redis_client import publish_event, push_activity

logger = logging.getLogger(__name__)


def _serialize_lead(lead: Lead) -> dict:
    """Flatten a Lead ORM object into the profile dict the agent expects."""
    company = lead.company
    return {
        "id": str(lead.id),
        "email": lead.email,
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "job_title": lead.job_title,
        "seniority_level": lead.seniority_level,
        "linkedin_url": lead.linkedin_url,
        "phone": lead.phone,
        "opted_out": lead.opted_out,
        "enrichment_score": lead.enrichment_score,
        "linkedin_signals": lead.linkedin_signals,
        "company_news": lead.company_news,
        "tech_stack": lead.tech_stack,
        "intent_signals": lead.intent_signals,
        "state_updated_at": lead.state_updated_at.isoformat() if lead.state_updated_at else None,
        "company_name": company.name if company else None,
        "company_domain": company.domain if company else None,
        "industry": company.industry if company else None,
        "employee_count": company.employee_count if company else None,
        "employee_range": company.employee_range if company else None,
        "icp_fit_score": company.icp_fit_score if company else 0,
        "intent_score": company.intent_score if company else 0,
        "funding_stage": company.funding_stage if company else None,
    }


def _serialize_history(events: list[EmailEvent]) -> list[dict]:
    return [
        {
            "event_type": e.event_type,
            "channel": e.channel,
            "subject": e.subject,
            "ab_variant": e.ab_variant,
            "clicked_url": e.clicked_url,
            "reply_content": e.reply_content,
            "reply_sentiment": e.reply_sentiment,
            "reply_intent": e.reply_intent,
            "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
        }
        for e in sorted(events, key=lambda x: x.occurred_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    ]


async def reason_for_lead(
    db: AsyncSession,
    lead_id: UUID,
    auto_execute: bool = False,
) -> AgentDecision:
    """
    Run reasoning for a lead, persist the decision, and optionally execute.

    Returns the saved AgentDecision row.
    """
    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")

    profile = _serialize_lead(lead)
    history = _serialize_history(lead.email_events or [])

    logger.info("Running reasoning for lead %s state=%s", lead.id, lead.state)
    result = run_reasoning(
        lead_id=str(lead.id),
        lead_profile=profile,
        engagement_history=history,
        current_state=lead.state,
    )

    decision = AgentDecision(
        lead_id=lead.id,
        decision_type=result.get("decision", "escalate_to_human"),
        channel_selected=_channel_for(result.get("decision")),
        confidence_score=float(result.get("confidence", 0.0)),
        reasoning_summary=result.get("reasoning_summary") or "No summary produced.",
        full_reasoning=result.get("full_reasoning"),
        signals_observed=result.get("behavioral_signals"),
        lead_state_at_decision=lead.state,
        was_approved=None,
    )

    auto_threshold = settings.CONFIDENCE_THRESHOLD
    if (
        auto_execute
        and settings.AUTOPILOT_MODE
        and decision.confidence_score >= auto_threshold
        and decision.decision_type not in ("escalate_to_human",)
    ):
        decision.was_approved = True
        decision.approved_by = "autopilot"
        decision.executed_at = datetime.now(timezone.utc)
        await _apply_decision(db, lead, result)

    db.add(decision)

    # Schedule next action time on the lead
    wait_days = int(result.get("next_wait_days", 3))
    if decision.decision_type == "wait":
        lead.next_action_at = datetime.now(timezone.utc) + timedelta(days=wait_days)
    elif decision.decision_type == "close_sequence":
        lead.next_action_at = None
        lead.state = "closed"
        lead.state_updated_at = datetime.now(timezone.utc)

    await db.flush()

    # Live feed
    activity = {
        "type": "agent_decision",
        "lead_id": str(lead.id),
        "lead_name": f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
        "decision": decision.decision_type,
        "confidence": float(decision.confidence_score),
        "summary": decision.reasoning_summary,
        "timestamp": decision.created_at.isoformat() if decision.created_at else datetime.now(timezone.utc).isoformat(),
    }
    try:
        await push_activity(activity)
        await publish_event("agent.decisions", activity)
    except Exception as e:
        logger.warning("Failed to publish activity: %s", e)

    return decision


def _channel_for(decision_type: Optional[str]) -> Optional[str]:
    mapping = {
        "send_email": "email",
        "send_linkedin_dm": "linkedin",
        "suggest_call": "phone",
    }
    return mapping.get(decision_type or "")


async def _apply_decision(db: AsyncSession, lead: Lead, result: dict) -> None:
    """Apply the decision side-effects to the lead's state."""
    decision = result.get("decision")
    now = datetime.now(timezone.utc)
    if decision == "send_email":
        # Defer to outreach.email_sender — here we just mark contacted.
        lead.state = "contacted"
        lead.state_updated_at = now
    elif decision == "send_linkedin_dm":
        lead.state = "contacted"
        lead.state_updated_at = now
    elif decision == "wait":
        wait_days = int(result.get("next_wait_days", 3))
        lead.next_action_at = now + timedelta(days=wait_days)
    elif decision == "close_sequence":
        lead.state = "closed"
        lead.state_updated_at = now
