"""Lead CRUD + ingestion endpoints."""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Lead, Company
from app.schemas.lead import (
    LeadCreate, LeadOut, LeadUpdate, LeadStateChange, CSVImportResult,
)
from app.utils.csv_parser import parse_csv, validate_row

router = APIRouter(prefix="/api/leads", tags=["leads"])
logger = logging.getLogger(__name__)


async def _get_or_create_company(
    db: AsyncSession,
    name: Optional[str],
    domain: Optional[str],
    industry: Optional[str] = None,
    employee_count: Optional[int] = None,
) -> Optional[Company]:
    if not name and not domain:
        return None
    if domain:
        existing = (await db.execute(
            select(Company).where(Company.domain == domain)
        )).scalar_one_or_none()
        if existing:
            return existing
    if name:
        existing = (await db.execute(
            select(Company).where(Company.name == name)
        )).scalar_one_or_none()
        if existing:
            return existing
    company = Company(
        name=name or domain,
        domain=domain,
        industry=industry,
        employee_count=employee_count,
        employee_range=_employee_range(employee_count),
    )
    db.add(company)
    await db.flush()
    return company


def _employee_range(count: Optional[int]) -> Optional[str]:
    if not count:
        return None
    if count < 50:
        return "1-49"
    if count < 200:
        return "50-199"
    if count < 500:
        return "200-499"
    if count < 1000:
        return "500-999"
    return "1000+"


@router.post("", response_model=LeadOut, status_code=201)
async def create_lead(payload: LeadCreate, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(Lead).where(Lead.email == payload.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Lead with this email already exists")

    company = await _get_or_create_company(
        db, payload.company_name, payload.company_domain, payload.industry
    )
    lead = Lead(
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        job_title=payload.job_title,
        seniority_level=payload.seniority_level,
        linkedin_url=payload.linkedin_url,
        phone=payload.phone,
        source=payload.source,
        company_id=company.id if company else None,
    )
    db.add(lead)
    await db.flush()
    # Trigger enrichment async
    try:
        from app.tasks.enrichment_tasks import enrich_lead_task
        enrich_lead_task.delay(str(lead.id))
    except Exception as e:
        logger.warning("Could not queue enrichment: %s", e)

    await db.refresh(lead, ["company"])
    return lead


@router.post("/import/csv", response_model=CSVImportResult)
async def import_csv(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    content = await file.read()
    imported = 0
    failed = 0
    errors: list[dict] = []
    lead_ids: list[UUID] = []

    for idx, row in enumerate(parse_csv(content)):
        valid, err = validate_row(row)
        if not valid:
            failed += 1
            errors.append({"row": idx + 1, "error": err})
            continue

        existing = (await db.execute(
            select(Lead).where(Lead.email == row["email"])
        )).scalar_one_or_none()
        if existing:
            failed += 1
            errors.append({"row": idx + 1, "error": "duplicate email", "email": row["email"]})
            continue

        try:
            employee_count = int(row.get("employee_count")) if row.get("employee_count", "").isdigit() else None
        except (ValueError, AttributeError):
            employee_count = None

        company = await _get_or_create_company(
            db,
            row.get("company_name"),
            row.get("company_domain"),
            row.get("industry"),
            employee_count,
        )
        lead = Lead(
            email=row["email"],
            first_name=row.get("first_name"),
            last_name=row.get("last_name"),
            job_title=row.get("job_title"),
            seniority_level=row.get("seniority_level"),
            linkedin_url=row.get("linkedin_url"),
            phone=row.get("phone"),
            source="csv",
            company_id=company.id if company else None,
        )
        db.add(lead)
        await db.flush()
        lead_ids.append(lead.id)
        imported += 1

        try:
            from app.tasks.enrichment_tasks import enrich_lead_task
            enrich_lead_task.delay(str(lead.id))
        except Exception:
            pass

    return CSVImportResult(
        imported=imported, failed=failed, errors=errors, lead_ids=lead_ids
    )


@router.get("", response_model=list[LeadOut])
async def list_leads(
    state: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Lead).order_by(desc(Lead.created_at)).limit(limit).offset(offset)
    if state:
        stmt = stmt.where(Lead.state == state)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            func.lower(Lead.email).like(like)
            | func.lower(Lead.first_name).like(like)
            | func.lower(Lead.last_name).like(like)
        )
    leads = (await db.execute(stmt)).scalars().all()
    return list(leads)


@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


@router.put("/{lead_id}/state", response_model=LeadOut)
async def update_state(
    lead_id: UUID,
    payload: LeadStateChange,
    db: AsyncSession = Depends(get_db),
):
    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    lead.state = payload.state
    lead.state_updated_at = datetime.now(timezone.utc)
    await db.flush()
    return lead


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    lead.opted_out = True
    lead.opted_out_at = datetime.now(timezone.utc)
    lead.state = "unsubscribed"
    lead.state_updated_at = datetime.now(timezone.utc)
    await db.flush()


@router.post("/{lead_id}/enrich")
async def enrich_now(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    from app.enrichment.enrichment_agent import enrich_lead
    return await enrich_lead(db, lead_id)


@router.post("/{lead_id}/simulate-engagement")
async def simulate_engagement(
    lead_id: UUID,
    scenario: str = Query("opened", description="opened|clicked|replied_positive|replied_objection|replied_interested"),
    db: AsyncSession = Depends(get_db),
):
    """
    Simulate buyer-side engagement for demo/testing purposes.
    This mimics what would happen when a recipient opens, clicks, or replies to an email.
    In production this happens via SendGrid webhooks automatically.
    """
    from app.models import EmailEvent
    from app.nlp.reply_classifier import classify_reply
    from app.redis_client import push_activity, publish_event

    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")

    now = datetime.now(timezone.utc)
    events_added = []

    if scenario == "opened":
        evt = EmailEvent(
            lead_id=lead.id, event_type="opened", channel="email", occurred_at=now
        )
        db.add(evt)
        events_added.append("opened")
        if lead.state == "contacted":
            lead.state = "engaged"
            lead.state_updated_at = now

    elif scenario == "clicked":
        # opened + clicked
        for etype in ("opened", "clicked"):
            evt = EmailEvent(
                lead_id=lead.id, event_type=etype, channel="email",
                clicked_url="https://salesagent.ai/demo" if etype == "clicked" else None,
                occurred_at=now,
            )
            db.add(evt)
            events_added.append(etype)
        if lead.state in ("contacted", "engaged"):
            lead.state = "engaged"
            lead.state_updated_at = now

    elif scenario in ("replied_positive", "replied_interested", "replied_objection"):
        reply_texts = {
            "replied_positive": "Hi, this sounds really interesting. Would love to learn more about how it works.",
            "replied_interested": "Thanks for reaching out. We've been looking for something like this. Can we schedule a call this week?",
            "replied_objection": "Thanks but we already have Outreach. We're pretty happy with it.",
        }
        reply_text = reply_texts.get(scenario, "")
        classification = await classify_reply(reply_text)

        evt = EmailEvent(
            lead_id=lead.id, event_type="replied", channel="email",
            reply_content=reply_text,
            reply_sentiment=classification.get("sentiment"),
            reply_intent=classification.get("intent"),
            occurred_at=now,
        )
        db.add(evt)
        events_added.append(f"replied ({classification.get('intent')})")
        lead.state = "replied"
        lead.state_updated_at = now

    await db.flush()

    try:
        activity = {
            "type": "email_event",
            "lead_id": str(lead.id),
            "lead_name": f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
            "event": scenario,
            "timestamp": now.isoformat(),
        }
        await push_activity(activity)
        await publish_event("email.events", activity)
    except Exception:
        pass

    return {
        "lead_id": str(lead.id),
        "scenario": scenario,
        "events_added": events_added,
        "new_state": lead.state,
        "message": f"Simulated {scenario} for {lead.first_name} {lead.last_name}. "
                   "Run agent reasoning to see how it reacts to this engagement signal.",
    }
