"""Agent decision endpoints."""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent.decision_maker import reason_for_lead
from app.database import get_db
from app.models import AgentDecision, Lead
from app.schemas.analytics import AgentDecisionOut

router = APIRouter(prefix="/api/agent", tags=["agent"])
logger = logging.getLogger(__name__)


def _decision_to_out(decision: AgentDecision) -> AgentDecisionOut:
    """
    Build an AgentDecisionOut from an ORM row, attaching the lead's name,
    company and email so the dashboard / agent feed cards can show
    "Marcus Johnson · Clay" without an N+1 fetch.

    Caller is expected to have eagerly loaded `decision.lead` and
    `decision.lead.company`.
    """
    lead = getattr(decision, "lead", None)
    lead_name = None
    lead_company = None
    lead_email = None
    if lead is not None:
        full_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip()
        lead_name = full_name or lead.email
        lead_email = lead.email
        if getattr(lead, "company", None):
            lead_company = lead.company.name

    return AgentDecisionOut(
        id=decision.id,
        lead_id=decision.lead_id,
        decision_type=decision.decision_type,
        channel_selected=decision.channel_selected,
        confidence_score=float(decision.confidence_score or 0.0),
        reasoning_summary=decision.reasoning_summary,
        full_reasoning=decision.full_reasoning,
        signals_observed=decision.signals_observed,
        lead_state_at_decision=decision.lead_state_at_decision,
        was_approved=decision.was_approved,
        approved_by=decision.approved_by,
        executed_at=decision.executed_at,
        created_at=decision.created_at,
        lead_name=lead_name,
        lead_company=lead_company,
        lead_email=lead_email,
    )


@router.post("/decide/{lead_id}", response_model=AgentDecisionOut)
async def decide(lead_id: UUID, auto_execute: bool = False, db: AsyncSession = Depends(get_db)):
    """Trigger reasoning for one lead. Returns the produced decision."""
    try:
        decision = await reason_for_lead(db, lead_id, auto_execute=auto_execute)
    except ValueError as e:
        raise HTTPException(404, str(e))
    # Reload with the lead + company eagerly loaded so the response carries
    # the display name / company name fields.
    decision = (await db.execute(
        select(AgentDecision)
        .options(selectinload(AgentDecision.lead).selectinload(Lead.company))
        .where(AgentDecision.id == decision.id)
    )).scalar_one()
    return _decision_to_out(decision)


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
        .options(selectinload(AgentDecision.lead).selectinload(Lead.company))
        .order_by(desc(AgentDecision.created_at))
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


@router.post("/decisions/{decision_id}/approve", response_model=AgentDecisionOut)
async def approve_decision(
    decision_id: UUID,
    payload: Optional[dict] = Body(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve an agent decision *and execute it*.

    Until now Approve was a metadata-only flip — `was_approved=True` was
    written but the recommended action (e.g. `send_email`) never ran.
    From the operator's POV that looked like "I clicked Approve and
    nothing happened". Now Approve actually carries out the action:

    - `send_email`: drafts the email server-side via the same logic as
      the Compose Email modal (intro for fresh leads, reply for threads)
      and sends it through SendGrid. Optional `to_email` in the JSON
      payload overrides the recipient for demos.
    - `send_linkedin_dm` / `suggest_call`: marked approved; the human
      executes these out-of-band so we just record the approval.
    - `wait`: re-affirms the wait timer that reasoning already set.
    - `close_sequence`: closes the lead's sequence and marks state.
    - `escalate_to_human`: just records approval.

    Idempotent: if the decision has already been approved/overridden,
    the endpoint returns the existing row without re-executing.
    """
    from app.agent.decision_maker import _serialize_lead, _serialize_history
    from app.outreach.email_sender import send_email
    from app.outreach.sequence_generator import (
        generate_personalised_email,
        generate_reply_email,
    )

    decision = (await db.execute(
        select(AgentDecision)
        .options(selectinload(AgentDecision.lead).selectinload(Lead.company))
        .where(AgentDecision.id == decision_id)
    )).scalar_one_or_none()
    if not decision:
        raise HTTPException(404, "Decision not found")

    # Idempotency — don't re-execute an already-actioned decision.
    if decision.was_approved is not None or decision.executed_at is not None:
        return _decision_to_out(decision)

    lead = decision.lead
    if lead is None:
        raise HTTPException(404, "Lead for this decision is missing")

    body_payload = payload or {}
    to_email_override = (body_payload.get("to_email") or "").strip() or None

    now = datetime.now(timezone.utc)
    decision.was_approved = True
    decision.approved_by = "human"
    decision.executed_at = now

    # ── Side effects per decision type ────────────────────────────────
    if decision.decision_type == "send_email":
        # Draft the email — intro for fresh leads, reply for active threads.
        profile = _serialize_lead(lead)
        events = list(lead.email_events or [])
        history = _serialize_history(events)
        has_outbound = any(
            e.event_type == "sent" and (e.channel or "email") == "email"
            for e in events
        )
        hooks = []
        if decision.full_reasoning:
            hooks = decision.full_reasoning.get("email_personalisation_hooks", []) or []

        try:
            if not has_outbound:
                draft = await generate_personalised_email(
                    lead=profile,
                    step_number=1,
                    sequence_type="intro",
                    personalisation_hooks=hooks,
                    ab_variant="A",
                )
            else:
                draft = await generate_reply_email(profile, history, hooks)
        except Exception as e:
            logger.exception("Approve: email generation failed for decision %s: %s", decision.id, e)
            decision.was_approved = False
            decision.approved_by = "approval_error"
            await db.flush()
            raise HTTPException(500, f"Failed to draft email: {e}")

        subject = (draft.get("subject") or "").strip()
        body = (draft.get("body") or "").strip()
        if not subject or not body:
            raise HTTPException(500, "LLM returned an empty draft; cannot send")

        event = await send_email(
            db,
            lead,
            subject,
            body,
            to_email_override=to_email_override,
        )
        if event is None:
            decision.was_approved = False
            decision.approved_by = "compliance_block"
            await db.flush()
            raise HTTPException(
                400,
                "Email blocked by compliance (lead opted out or invalid state)",
            )

    elif decision.decision_type == "send_linkedin_dm":
        # We don't have a LinkedIn integration; just mark contacted.
        if lead.state in ("new", "enriched"):
            lead.state = "contacted"
            lead.state_updated_at = now

    elif decision.decision_type == "close_sequence":
        lead.state = "closed"
        lead.state_updated_at = now
        lead.next_action_at = None
        lead.current_sequence_id = None

    # `wait`, `suggest_call`, `escalate_to_human` — no automatic side
    # effect, the approval itself is the record.

    await db.flush()
    return _decision_to_out(decision)


@router.post("/decisions/{decision_id}/override", response_model=AgentDecisionOut)
async def override_decision(
    decision_id: UUID,
    new_action: str,
    db: AsyncSession = Depends(get_db),
):
    decision = (await db.execute(
        select(AgentDecision)
        .options(selectinload(AgentDecision.lead).selectinload(Lead.company))
        .where(AgentDecision.id == decision_id)
    )).scalar_one_or_none()
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
        .options(selectinload(AgentDecision.lead).selectinload(Lead.company))
        .where(AgentDecision.lead_id == lead_id)
        .order_by(desc(AgentDecision.created_at))
    )
    decisions = (await db.execute(stmt)).scalars().all()
    return [_decision_to_out(d) for d in decisions]


@router.post("/draft-email/{lead_id}")
async def draft_email(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Generate a personalised draft email for a lead.

    - When the lead has no prior outbound email → uses the intro generator
      (`generate_personalised_email`) so the agent writes the first touch
      straight from the dashboard, replacing the old `demo_send.py` flow.
    - When there's an active conversation → uses the reply generator so the
      draft reflects the full thread.
    """
    from app.agent.decision_maker import _serialize_lead, _serialize_history
    from app.outreach.sequence_generator import (
        generate_personalised_email,
        generate_reply_email,
    )

    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")

    profile = _serialize_lead(lead)
    events = list(lead.email_events or [])
    history = _serialize_history(events)
    has_outbound = any(
        e.event_type == "sent" and (e.channel or "email") == "email"
        for e in events
    )

    # Pull the latest decision's personalisation hooks if available
    latest_decision = (await db.execute(
        select(AgentDecision)
        .where(AgentDecision.lead_id == lead_id)
        .order_by(desc(AgentDecision.created_at))
        .limit(1)
    )).scalar_one_or_none()

    hooks: list[str] = []
    if latest_decision and latest_decision.full_reasoning:
        hooks = latest_decision.full_reasoning.get("email_personalisation_hooks", []) or []

    if not has_outbound:
        # First-touch intro — use the dedicated intro generator with rich context
        draft = await generate_personalised_email(
            lead=profile,
            step_number=1,
            sequence_type="intro",
            personalisation_hooks=hooks,
            ab_variant="A",
        )
    else:
        draft = await generate_reply_email(profile, history, hooks)

    return draft


@router.post("/send-email/{lead_id}")
async def send_email_to_lead(lead_id: UUID, payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Send an email to a lead with the (possibly edited) subject/body.
    Records the event and updates lead state.

    Optional `to_email` in the payload routes the actual delivery to a
    different recipient (useful during demos / pitches when the operator
    wants the email to land in their own inbox). The EmailEvent is still
    stored against the lead either way.
    """
    from app.outreach.email_sender import send_email

    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")

    subject = payload.get("subject", "").strip()
    body = payload.get("body", "").strip()
    to_email_override = (payload.get("to_email") or "").strip() or None
    if not subject or not body:
        raise HTTPException(400, "subject and body are required")

    event = await send_email(
        db,
        lead,
        subject,
        body,
        to_email_override=to_email_override,
    )
    if event is None:
        raise HTTPException(400, "Email blocked by compliance (lead opted out or invalid state)")

    return {
        "status": "sent",
        "message_id": event.message_id,
        "subject": subject,
        "lead_state": lead.state,
        "delivered_to": to_email_override or lead.email,
    }
