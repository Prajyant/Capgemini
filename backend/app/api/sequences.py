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


@router.post("/{sequence_id}/approve-email")
async def approve_email():
    """Stub — in production this would mark a generated email approved for send."""
    return {"status": "approved"}
