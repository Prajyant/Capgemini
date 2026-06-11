"""Agent decision endpoints."""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent.decision_maker import reason_for_lead
from app.config import settings
from app.database import get_db
from app.models import AgentDecision, Lead
from app.schemas.analytics import AgentDecisionOut, LeadSummary

router = APIRouter(prefix="/api/agent", tags=["agent"])
logger = logging.getLogger(__name__)


def _lead_summary(lead: Optional[Lead]) -> Optional[LeadSummary]:
    if lead is None:
        return None
    company = getattr(lead, "company", None)
    return LeadSummary(
        id=lead.id,
        email=lead.email,
        first_name=lead.first_name,
        last_name=lead.last_name,
        job_title=lead.job_title,
        company_name=company.name if company else None,
        company_domain=company.domain if company else None,
    )


def _decision_to_out(decision: AgentDecision) -> AgentDecisionOut:
    """Build a response model with the lead summary attached."""
    return AgentDecisionOut(
        id=decision.id,
        lead_id=decision.lead_id,
        decision_type=decision.decision_type,
        channel_selected=decision.channel_selected,
        confidence_score=float(decision.confidence_score),
        reasoning_summary=decision.reasoning_summary,
        full_reasoning=decision.full_reasoning,
        signals_observed=decision.signals_observed,
        lead_state_at_decision=decision.lead_state_at_decision,
        was_approved=decision.was_approved,
        approved_by=decision.approved_by,
        executed_at=decision.executed_at,
        created_at=decision.created_at,
        lead=_lead_summary(getattr(decision, "lead", None)),
    )


async def _load_decision_with_lead(db: AsyncSession, decision_id: UUID) -> Optional[AgentDecision]:
    stmt = (
        select(AgentDecision)
        .where(AgentDecision.id == decision_id)
        .options(selectinload(AgentDecision.lead).selectinload(Lead.company))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


@router.post("/decide/{lead_id}", response_model=AgentDecisionOut)
async def decide(lead_id: UUID, auto_execute: bool = False, db: AsyncSession = Depends(get_db)):
    """Trigger reasoning for one lead. Polls inbox first to pick up any new replies."""
    # Poll inbox before reasoning so we have the latest replies
    try:
        from app.inbox.imap_reader import process_inbox_replies
        await process_inbox_replies()
    except Exception as e:
        logger.warning("Inbox poll before reasoning failed: %s", e)

    try:
        decision = await reason_for_lead(db, lead_id, auto_execute=auto_execute)
    except ValueError as e:
        raise HTTPException(404, str(e))
    # Reload with lead+company so the response includes the summary.
    full = await _load_decision_with_lead(db, decision.id)
    return _decision_to_out(full or decision)


@router.post("/decide/batch")
async def decide_batch(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Trigger reasoning for all leads with a passed next_action_at."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(Lead)
        .where(Lead.opted_out == False)  # noqa: E712
        .where(Lead.state.in_(["enriched", "contacted", "engaged", "cold"]))
        .where((Lead.next_action_at == None) | (Lead.next_action_at <= now))  # noqa: E711
        .limit(limit)
    )
    leads = (await db.execute(stmt)).scalars().all()
    decisions = []
    for lead in leads:
        try:
            d = await reason_for_lead(db, lead.id, auto_execute=False)
            decisions.append({"lead_id": str(lead.id), "decision": d.decision_type, "confidence": float(d.confidence_score)})
        except Exception as e:
            logger.exception("Batch reasoning failed for %s: %s", lead.id, e)
    return {"processed": len(decisions), "decisions": decisions}


@router.get("/decisions", response_model=list[AgentDecisionOut])
async def list_decisions(
    decision_type: Optional[str] = None,
    lead_id: Optional[UUID] = None,
    min_confidence: Optional[float] = None,
    max_confidence: Optional[float] = None,
    awaiting_approval: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(AgentDecision)
        .order_by(desc(AgentDecision.created_at))
        .options(selectinload(AgentDecision.lead).selectinload(Lead.company))
        .limit(limit)
        .offset(offset)
    )
    if decision_type:
        stmt = stmt.where(AgentDecision.decision_type == decision_type)
    if lead_id:
        stmt = stmt.where(AgentDecision.lead_id == lead_id)
    if min_confidence is not None:
        stmt = stmt.where(AgentDecision.confidence_score >= min_confidence)
    if max_confidence is not None:
        stmt = stmt.where(AgentDecision.confidence_score <= max_confidence)
    if awaiting_approval:
        stmt = stmt.where(AgentDecision.was_approved.is_(None)).where(AgentDecision.executed_at.is_(None))
    decisions = (await db.execute(stmt)).scalars().all()
    return [_decision_to_out(d) for d in decisions]


@router.post("/decisions/{decision_id}/preview-email")
async def preview_email(decision_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Generate the email the agent would send WITHOUT actually sending it.
    If the lead has replied, generates a contextual response.
    """
    decision = await _load_decision_with_lead(db, decision_id)
    if not decision:
        raise HTTPException(404, "Decision not found")
    if decision.decision_type != "send_email":
        raise HTTPException(400, "Decision is not a send_email type")
    if not decision.lead:
        raise HTTPException(400, "No lead attached to decision")

    from app.agent.decision_maker import _serialize_lead
    from app.outreach.sequence_generator import generate_personalised_email, generate_reply_email
    from app.models import EmailEvent

    lead = decision.lead
    profile = _serialize_lead(lead)
    hooks = (decision.full_reasoning or {}).get("email_personalisation_hooks") or []

    # Check if lead has replied — if so, generate contextual response
    last_reply = None
    from sqlalchemy import select, desc
    reply_stmt = (
        select(EmailEvent)
        .where(EmailEvent.lead_id == lead.id)
        .where(EmailEvent.event_type == "replied")
        .order_by(desc(EmailEvent.occurred_at))
        .limit(1)
    )
    last_reply = (await db.execute(reply_stmt)).scalar_one_or_none()

    if last_reply and last_reply.reply_content:
        email_data = await generate_reply_email(
            lead=profile,
            reply_content=last_reply.reply_content,
            reply_intent=last_reply.reply_intent,
            personalisation_hooks=hooks,
        )
        sequence_type = "reply"
    else:
        next_step = max(1, (lead.current_step or 0) + 1)
        step_types = {1: "intro", 2: "follow_up", 3: "breakup"}
        sequence_type = step_types.get(next_step, "follow_up")
        email_data = await generate_personalised_email(
            lead=profile,
            step_number=next_step,
            sequence_type=sequence_type,
            personalisation_hooks=hooks,
        )

    return {
        "subject": email_data.get("subject", ""),
        "body": email_data.get("body", ""),
        "sequence_type": sequence_type,
        "personalisation_used": email_data.get("personalisation_used", ""),
        "spam_score": email_data.get("spam_score", 0),
        "ab_variant": email_data.get("ab_variant", "A"),
    }


@router.post("/decisions/{decision_id}/approve", response_model=AgentDecisionOut)
async def approve_decision(decision_id: UUID, db: AsyncSession = Depends(get_db)):
    decision = await _load_decision_with_lead(db, decision_id)
    if not decision:
        raise HTTPException(404, "Decision not found")
    decision.was_approved = True
    decision.approved_by = "human"
    decision.executed_at = datetime.now(timezone.utc)

    # If the approved decision is to send an email, actually send it now.
    if decision.decision_type == "send_email" and decision.lead is not None:
        from app.outreach.email_sender import generate_and_send
        hooks = (decision.full_reasoning or {}).get("email_personalisation_hooks") or []
        try:
            await generate_and_send(
                db,
                decision.lead,
                personalisation_hooks=hooks,
            )
        except Exception as e:
            logger.exception("Send-on-approve failed for decision %s: %s", decision_id, e)

    await db.flush()
    return _decision_to_out(decision)


@router.post("/send-test/{lead_id}")
async def send_test_email(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Generate and send a test email for a single lead. Useful for verifying
    SendGrid setup without waiting for the agent to choose send_email.
    """
    from app.outreach.email_sender import generate_and_send

    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")

    event = await generate_and_send(db, lead)
    await db.flush()

    if event is None:
        return {
            "status": "blocked",
            "reason": "compliance check failed (lead opted out or in terminal state)",
        }

    return {
        "status": "sent",
        "message_id": event.message_id,
        "subject": event.subject,
        "to": lead.email,
        "ab_variant": event.ab_variant,
        "is_real_send": bool(settings.SENDGRID_API_KEY),
    }


@router.post("/decisions/{decision_id}/override", response_model=AgentDecisionOut)
async def override_decision(
    decision_id: UUID,
    new_action: str,
    db: AsyncSession = Depends(get_db),
):
    decision = await _load_decision_with_lead(db, decision_id)
    if not decision:
        raise HTTPException(404, "Decision not found")
    decision.was_approved = False
    decision.approved_by = "human_override"
    decision.executed_at = datetime.now(timezone.utc)
    decision.reasoning_summary = f"[Human override → {new_action}] {decision.reasoning_summary}"
    await db.flush()
    return _decision_to_out(decision)


@router.get("/reasoning/{lead_id}", response_model=list[AgentDecisionOut])
async def reasoning_history(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(AgentDecision)
        .where(AgentDecision.lead_id == lead_id)
        .order_by(desc(AgentDecision.created_at))
        .options(selectinload(AgentDecision.lead).selectinload(Lead.company))
    )
    decisions = (await db.execute(stmt)).scalars().all()
    return [_decision_to_out(d) for d in decisions]
