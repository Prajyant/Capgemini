"""
Sequence auto-progression.

Once a lead is enrolled in a sequence (set via the /sequences/send-step
endpoint or the agent), this Celery task drives the lead through the rest
of the steps automatically:

  • Find leads with a `current_sequence_id` and a passed `next_action_at`
  • Skip terminal states (replied / converted / closed / unsubscribed) so
    we don't keep blasting people who already engaged
  • Generate the next step's email via the LLM with the full lead context
  • Send it via SendGrid (or queue it for human approval if autopilot is
    off and the confidence threshold isn't met)
  • Bump `current_step` and schedule `next_action_at` from the next step's
    `wait_days`
  • When the last step is reached, leave the lead in `contacted`/`engaged`
    state and clear `next_action_at` so the agent's reasoning loop takes
    over from there

The task is idempotent — running it twice in the same minute won't double-
send anything because `next_action_at` is advanced before the second pass.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent.decision_maker import _serialize_lead
from app.config import settings
from app.database import get_db_context
from app.models import (
    AgentDecision,
    Lead,
    Sequence,
    SequenceStep,
)
from app.outreach.email_sender import send_email
from app.outreach.sequence_generator import generate_personalised_email
from app.redis_client import publish_event, push_activity
from app.tasks.celery_app import celery_app
from app.tasks.loop_helper import run_async

logger = logging.getLogger(__name__)

# Don't keep sending sequence emails to leads in these states.
TERMINAL_STATES = {"replied", "converted", "closed", "unsubscribed"}


@celery_app.task(name="app.tasks.sequence_tasks.progress_sequences")
def progress_sequences() -> dict:
    """Advance every enrolled lead by one step if its wait window has passed."""
    return run_async(_progress())


async def _progress() -> dict:
    async with get_db_context() as db:
        return await _progress_db(db)


async def _progress_db(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)

    stmt = (
        select(Lead)
        .options(selectinload(Lead.company))
        .where(Lead.current_sequence_id.is_not(None))
        .where(Lead.opted_out == False)  # noqa: E712
        .where(Lead.state.notin_(TERMINAL_STATES))
        .where(Lead.next_action_at.is_not(None))
        .where(Lead.next_action_at <= now)
        .limit(50)
    )
    leads = (await db.execute(stmt)).scalars().all()

    advanced = 0
    completed = 0
    blocked = 0

    for lead in leads:
        try:
            outcome = await _advance_one(db, lead, now)
            if outcome == "advanced":
                advanced += 1
            elif outcome == "completed":
                completed += 1
            else:
                blocked += 1
        except Exception:
            logger.exception("Sequence progression failed for lead %s", lead.id)
            blocked += 1

    if advanced or completed:
        logger.info(
            "Sequence progression: %d advanced, %d completed, %d blocked",
            advanced, completed, blocked,
        )
    return {"advanced": advanced, "completed": completed, "blocked": blocked}


async def _advance_one(db: AsyncSession, lead: Lead, now: datetime) -> str:
    if lead.current_sequence_id is None:
        return "blocked"

    seq = (await db.execute(
        select(Sequence)
        .options(selectinload(Sequence.steps))
        .where(Sequence.id == lead.current_sequence_id)
    )).scalar_one_or_none()
    if seq is None or not seq.steps:
        # Sequence was deleted or has no steps — release the lead.
        lead.current_sequence_id = None
        lead.next_action_at = None
        return "blocked"

    steps = sorted(seq.steps, key=lambda s: s.step_number)
    next_step_number = (lead.current_step or 0) + 1
    step = next((s for s in steps if s.step_number == next_step_number), None)
    if step is None:
        # No more steps — graduation. Hand back to the agent's reasoning loop.
        lead.next_action_at = None
        return "completed"

    profile = _serialize_lead(lead)
    sequence_type = _step_type(step.step_number, len(steps))
    ab_variant = "A" if step.step_number % 2 == 1 else "B"

    email = await generate_personalised_email(
        lead=profile,
        step_number=step.step_number,
        sequence_type=sequence_type,
        personalisation_hooks=None,
        ab_variant=ab_variant,
    )
    subject = email.get("subject") or _fallback_subject(step, profile)
    body = email.get("body") or _fallback_body(step, profile)

    # Persist a decision row so this shows up in the live agent feed and
    # in /api/agent/decisions, with company name + lead name for the card.
    decision = AgentDecision(
        lead_id=lead.id,
        decision_type="send_email",
        channel_selected="email",
        confidence_score=0.85,
        reasoning_summary=(
            f"Sequence step {step.step_number}/{len(steps)} for "
            f"{lead.first_name or lead.email} at "
            f"{lead.company.name if lead.company else profile.get('company_name', 'their company')}."
        ),
        full_reasoning={
            "sequence_id": str(seq.id),
            "step_number": step.step_number,
            "wait_days_to_next": _next_wait(steps, step.step_number),
            "subject": subject,
            "body_preview": body[:500],
        },
        lead_state_at_decision=lead.state,
    )
    db.add(decision)

    if settings.AUTOPILOT_MODE:
        # Autopilot — actually send and progress the sequence.
        event = await send_email(db, lead, subject, body, ab_variant=ab_variant)
        if event is None:
            # Compliance blocked the send (opt-out etc.); back off.
            lead.next_action_at = None
            decision.was_approved = False
            decision.approved_by = "compliance_block"
            decision.executed_at = now
            return "blocked"

        decision.was_approved = True
        decision.approved_by = "autopilot"
        decision.executed_at = now

        lead.current_step = step.step_number
        wait_days = _next_wait(steps, step.step_number)
        lead.next_action_at = now + timedelta(days=wait_days) if wait_days else None
    else:
        # Supervised — leave the decision pending; presenter approves from UI.
        # Push next_action_at forward so we don't keep regenerating drafts.
        wait_days = _next_wait(steps, step.step_number)
        lead.next_action_at = now + timedelta(days=max(wait_days, 1))

    await db.flush()

    activity = {
        "type": "agent_decision",
        "lead_id": str(lead.id),
        "lead_name": f"{lead.first_name or ''} {lead.last_name or ''}".strip() or lead.email,
        "decision": decision.decision_type,
        "confidence": float(decision.confidence_score),
        "summary": decision.reasoning_summary,
        "timestamp": (decision.created_at or now).isoformat(),
    }
    try:
        await push_activity(activity)
        await publish_event("agent.decisions", activity)
    except Exception:
        pass

    return "advanced"


def _step_type(step_number: int, total: int) -> str:
    if step_number == 1:
        return "intro"
    if step_number >= total:
        return "breakup"
    return "follow_up"


def _next_wait(steps: list[SequenceStep], current_step_number: int) -> int:
    """Wait days *until the step AFTER the one we just sent*."""
    upcoming = next(
        (s for s in steps if s.step_number == current_step_number + 1),
        None,
    )
    return int(upcoming.wait_days) if upcoming else 0


def _fallback_subject(step: SequenceStep, profile: dict) -> str:
    template = step.subject_template or "Following up"
    return template.replace("{first_name}", profile.get("first_name") or "there") \
                   .replace("{company_name}", profile.get("company_name") or "your team")


def _fallback_body(step: SequenceStep, profile: dict) -> str:
    first = profile.get("first_name") or "there"
    company = profile.get("company_name") or "your team"
    return (
        f"Hi {first},\n\n"
        f"Wanted to circle back on how teams like {company} are using "
        f"{settings.PRODUCT_NAME} to make their outbound smarter. Worth a quick chat?\n\n"
        f"Best,\n{settings.SENDGRID_FROM_NAME}"
    )
