"""Sequence management endpoints."""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.decision_maker import _serialize_lead
from app.database import get_db
from app.models import Lead, Sequence, SequenceStep
from app.outreach.sequence_generator import generate_full_sequence
from app.schemas.sequence import (
    SequenceCreate, SequenceOut, SequenceEmailsOut, GeneratedEmail,
)

router = APIRouter(prefix="/api/sequences", tags=["sequences"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[SequenceOut])
async def list_sequences(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Sequence).where(Sequence.is_active == True))).scalars().all()  # noqa: E712
    return list(rows)


@router.post("", response_model=SequenceOut, status_code=201)
async def create_sequence(payload: SequenceCreate, db: AsyncSession = Depends(get_db)):
    seq = Sequence(
        name=payload.name,
        vertical=payload.vertical,
        total_steps=payload.total_steps,
    )
    db.add(seq)
    await db.flush()
    for step_in in payload.steps:
        db.add(SequenceStep(
            sequence_id=seq.id,
            step_number=step_in.step_number,
            channel=step_in.channel,
            subject_template=step_in.subject_template,
            body_template=step_in.body_template,
            wait_days=step_in.wait_days,
        ))
    await db.flush()
    await db.refresh(seq, ["steps"])
    return seq


@router.get("/{sequence_id}/emails/{lead_id}", response_model=SequenceEmailsOut)
async def get_personalised_emails(
    sequence_id: UUID,
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate the 3 personalised emails for this lead+sequence on demand."""
    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    seq = (await db.execute(select(Sequence).where(Sequence.id == sequence_id))).scalar_one_or_none()
    if not seq:
        raise HTTPException(404, "Sequence not found")

    profile = _serialize_lead(lead)
    raw_emails = await generate_full_sequence(profile, personalisation_hooks=None)
    emails = [
        GeneratedEmail(
            subject=e.get("subject", ""),
            body=e.get("body", ""),
            personalisation_used=e.get("personalisation_used"),
            spam_score=e.get("spam_score", 0.0),
            passes_spam_check=e.get("passes_spam_check", True),
            ab_variant=e.get("ab_variant", "A"),
        )
        for e in raw_emails
    ]
    return SequenceEmailsOut(sequence_id=seq.id, lead_id=lead.id, emails=emails)


@router.post("/{sequence_id}/enroll/{lead_id}")
async def enroll_lead(
    sequence_id: UUID,
    lead_id: UUID,
    start_now: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    Enrol a lead in a sequence so the auto-progression task picks it up.

    If `start_now` is true (default), schedules the first step immediately.
    Otherwise schedules it according to step 1's `wait_days`.
    """
    from datetime import datetime, timezone, timedelta

    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    seq = (await db.execute(select(Sequence).where(Sequence.id == sequence_id))).scalar_one_or_none()
    if not seq:
        raise HTTPException(404, "Sequence not found")
    if not seq.steps:
        raise HTTPException(400, "Sequence has no steps")

    first = sorted(seq.steps, key=lambda s: s.step_number)[0]
    now = datetime.now(timezone.utc)

    lead.current_sequence_id = seq.id
    lead.current_step = 0
    lead.next_action_at = now if start_now else now + timedelta(days=first.wait_days)
    await db.flush()
    return {
        "status": "enrolled",
        "lead_id": str(lead.id),
        "sequence_id": str(seq.id),
        "next_action_at": lead.next_action_at.isoformat() if lead.next_action_at else None,
    }


@router.post("/progress/run-now")
async def progress_now(db: AsyncSession = Depends(get_db)):
    """
    Trigger sequence auto-progression immediately rather than waiting for
    the next 2-minute Celery beat. Useful for demos.
    """
    from app.tasks.sequence_tasks import _progress_db
    return await _progress_db(db)


@router.post("/send-step/{lead_id}")
async def send_sequence_step(lead_id: UUID, payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Send a single (possibly edited) sequence email to a lead and enroll them
    in the sequence. Records the event and advances the lead state.

    Schedules `next_action_at` from the *following* step's `wait_days` so
    the auto-progression task picks the lead up at the right time.
    """
    from datetime import datetime, timezone, timedelta
    from app.outreach.email_sender import send_email

    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")

    subject = (payload.get("subject") or "").strip()
    body = (payload.get("body") or "").strip()
    ab_variant = payload.get("ab_variant", "A")
    sequence_id = payload.get("sequence_id")
    step_number = int(payload.get("step_number", 1))
    to_email_override = (payload.get("to_email") or "").strip() or None

    if not subject or not body:
        raise HTTPException(400, "subject and body are required")

    event = await send_email(
        db,
        lead,
        subject,
        body,
        ab_variant=ab_variant,
        to_email_override=to_email_override,
    )
    if event is None:
        raise HTTPException(400, "Email blocked by compliance (lead opted out or invalid state)")

    # Enroll the lead and schedule the next step.
    if sequence_id:
        try:
            seq_uuid = UUID(sequence_id)
        except (ValueError, TypeError):
            seq_uuid = None

        if seq_uuid is not None:
            lead.current_sequence_id = seq_uuid
            lead.current_step = step_number

            seq = (await db.execute(
                select(Sequence).where(Sequence.id == seq_uuid)
            )).scalar_one_or_none()
            now = datetime.now(timezone.utc)
            if seq and seq.steps:
                next_step = next(
                    (s for s in sorted(seq.steps, key=lambda s: s.step_number)
                     if s.step_number == step_number + 1),
                    None,
                )
                if next_step is not None:
                    lead.next_action_at = now + timedelta(days=int(next_step.wait_days))
                else:
                    # No more steps — let the agent's reasoning loop take over.
                    lead.next_action_at = None
    await db.flush()

    return {
        "status": "sent",
        "message_id": event.message_id,
        "subject": subject,
        "lead_state": lead.state,
        "delivered_to": to_email_override or lead.email,
        "next_action_at": lead.next_action_at.isoformat() if lead.next_action_at else None,
    }
