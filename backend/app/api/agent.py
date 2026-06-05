"""Agent decision endpoints."""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.decision_maker import reason_for_lead
from app.database import get_db
from app.models import AgentDecision, Lead
from app.schemas.analytics import AgentDecisionOut

router = APIRouter(prefix="/api/agent", tags=["agent"])
logger = logging.getLogger(__name__)


@router.post("/decide/{lead_id}", response_model=AgentDecisionOut)
async def decide(lead_id: UUID, auto_execute: bool = False, db: AsyncSession = Depends(get_db)):
    """Trigger reasoning for one lead. Returns the produced decision."""
    try:
        decision = await reason_for_lead(db, lead_id, auto_execute=auto_execute)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return decision


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
    stmt = select(AgentDecision).order_by(desc(AgentDecision.created_at)).limit(limit).offset(offset)
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
    return list(decisions)


@router.post("/decisions/{decision_id}/approve", response_model=AgentDecisionOut)
async def approve_decision(decision_id: UUID, db: AsyncSession = Depends(get_db)):
    decision = (await db.execute(
        select(AgentDecision).where(AgentDecision.id == decision_id)
    )).scalar_one_or_none()
    if not decision:
        raise HTTPException(404, "Decision not found")
    decision.was_approved = True
    decision.approved_by = "human"
    decision.executed_at = datetime.now(timezone.utc)
    await db.flush()
    return decision


@router.post("/decisions/{decision_id}/override", response_model=AgentDecisionOut)
async def override_decision(
    decision_id: UUID,
    new_action: str,
    db: AsyncSession = Depends(get_db),
):
    decision = (await db.execute(
        select(AgentDecision).where(AgentDecision.id == decision_id)
    )).scalar_one_or_none()
    if not decision:
        raise HTTPException(404, "Decision not found")
    decision.was_approved = False
    decision.approved_by = "human_override"
    decision.executed_at = datetime.now(timezone.utc)
    decision.reasoning_summary = f"[Human override → {new_action}] {decision.reasoning_summary}"
    await db.flush()
    return decision


@router.get("/reasoning/{lead_id}", response_model=list[AgentDecisionOut])
async def reasoning_history(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(AgentDecision)
        .where(AgentDecision.lead_id == lead_id)
        .order_by(desc(AgentDecision.created_at))
    )
    decisions = (await db.execute(stmt)).scalars().all()
    return list(decisions)
