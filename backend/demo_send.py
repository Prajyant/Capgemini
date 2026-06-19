"""
Demo script:
1. Deletes all existing leads (+ related email events, agent decisions, AB tests)
2. Creates a RICH lead with full context (company news, tech stack, intent signals)
   so the agent reasoning and email generator have substantial data to work with.
3. Generates a personalized intro email via the LLM (not a short template)
4. Sends it via SendGrid to YOUR email (acts as the lead's inbox)
5. Stores everything in the database

Usage (with venv activated):
  python demo_send.py
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import delete

from app.database import get_db_context, init_db
from app.models import Lead, EmailEvent, AgentDecision, ABTest, Company
from app.outreach.sequence_generator import generate_personalised_email
from app.outreach.email_sender import _send_via_sendgrid
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
TARGET_EMAIL = settings.SENDGRID_FROM_EMAIL  # your inbox = the lead's inbox

# Rich, realistic lead persona (edit freely). Gives the agent + LLM real context.
LEAD = {
    "first_name": "Priya",
    "last_name": "Raman",
    "job_title": "Head of Revenue Operations",
    "seniority_level": "Director",
    "linkedin_url": "https://www.linkedin.com/in/priya-raman-demo/",
    "phone": "+1-512-555-0188",
}

COMPANY = {
    "name": "Vertex Cloud",
    "domain": "vertexcloud.io",
    "industry": "Cloud Infrastructure / SaaS",
    "employee_count": 180,
    "employee_range": "50-199",
    "location": "Denver, CO",
    "funding_stage": "Series A",
    "tech_stack": ["AWS", "HubSpot", "Salesloft", "Segment", "Looker"],
    "recent_news": [
        {
            "headline": "Vertex Cloud closes $22M Series A to expand its multi-cloud platform",
            "source": "VentureBeat",
            "url": "https://example.com/vertex-series-a",
            "published_at": "2026-06-12",
        },
        {
            "headline": "Vertex Cloud opens new RevOps team, hiring 6 SDRs and 2 AEs",
            "source": "LinkedIn",
            "url": "https://example.com/vertex-hiring",
            "published_at": "2026-06-16",
        },
    ],
    "intent_score": 86,
    "icp_fit_score": 92,
}


async def main():
    await init_db()

    async with get_db_context() as db:
        # ─── Step 1: Wipe existing data ────────────────────────────────────
        logger.info("Deleting all existing leads and related data...")
        await db.execute(delete(AgentDecision))
        await db.execute(delete(EmailEvent))
        await db.execute(delete(ABTest))
        await db.execute(delete(Lead))
        await db.execute(delete(Company))
        logger.info("✓ Cleared.")

        # ─── Step 2: Create company with rich context ──────────────────────
        company = Company(
            name=COMPANY["name"],
            domain=COMPANY["domain"],
            industry=COMPANY["industry"],
            employee_count=COMPANY["employee_count"],
            employee_range=COMPANY["employee_range"],
            location=COMPANY["location"],
            funding_stage=COMPANY["funding_stage"],
            tech_stack=COMPANY["tech_stack"],
            recent_news=COMPANY["recent_news"],
            intent_score=COMPANY["intent_score"],
            icp_fit_score=COMPANY["icp_fit_score"],
        )
        db.add(company)
        await db.flush()
        logger.info("✓ Company created: %s", COMPANY["name"])

        # ─── Step 3: Create lead with full enrichment ──────────────────────
        lead = Lead(
            email=TARGET_EMAIL,
            first_name=LEAD["first_name"],
            last_name=LEAD["last_name"],
            job_title=LEAD["job_title"],
            seniority_level=LEAD["seniority_level"],
            linkedin_url=LEAD["linkedin_url"],
            phone=LEAD["phone"],
            company_id=company.id,
            source="demo",
            enrichment_status="complete",
            enrichment_score=90,
            state="new",
            state_updated_at=datetime.now(timezone.utc),
            linkedin_signals={
                "tenure_months": 28,
                "post_frequency": "weekly",
                "recent_post_topics": ["data engineering", "scaling teams", "AI in GTM"],
                "connections_count": "500+",
                "is_active": True,
            },
            company_news=COMPANY["recent_news"],
            tech_stack=COMPANY["tech_stack"],
            intent_signals={
                "intent_score": COMPANY["intent_score"],
                "funding_recent": True,
                "hiring_count": 4,
                "tech_replacement_signals": ["Outreach"],
            },
        )
        db.add(lead)
        await db.flush()
        logger.info("✓ Lead created: %s %s (%s)", LEAD["first_name"], LEAD["last_name"], TARGET_EMAIL)

        # ─── Step 4: Generate a personalized intro email via LLM ───────────
        lead_ctx = {
            "first_name": LEAD["first_name"],
            "last_name": LEAD["last_name"],
            "job_title": LEAD["job_title"],
            "company_name": COMPANY["name"],
            "industry": COMPANY["industry"],
            "employee_range": COMPANY["employee_range"],
            "tech_stack": COMPANY["tech_stack"],
            "company_news": COMPANY["recent_news"],
        }
        logger.info("Generating personalized intro email via LLM...")
        email = await generate_personalised_email(
            lead=lead_ctx,
            step_number=1,
            sequence_type="intro",
            personalisation_hooks=["Series A funding", "building a RevOps team", "uses Salesloft"],
            ab_variant="B",
        )
        subject = email.get("subject", f"Quick thought on {COMPANY['name']}")
        body = email.get("body", "")
        logger.info("Generated email (subject: %s, %d chars body)", subject, len(body))

        # ─── Step 5: Send via SendGrid ─────────────────────────────────────
        message_id = await _send_via_sendgrid(
            to_email=TARGET_EMAIL,
            subject=subject,
            body=body,
            to_name=f"{LEAD['first_name']} {LEAD['last_name']}",
        )
        logger.info("✓ Email sent! Message ID: %s", message_id)

        # ─── Step 6: Record email event ────────────────────────────────────
        db.add(EmailEvent(
            lead_id=lead.id,
            message_id=message_id,
            event_type="sent",
            channel="email",
            subject=subject,
            body=body,
            ab_variant="B",
            occurred_at=datetime.now(timezone.utc),
        ))
        lead.state = "contacted"
        lead.state_updated_at = datetime.now(timezone.utc)
        await db.flush()

        logger.info("═══════════════════════════════════════════════")
        logger.info("  DONE — lead created & intro email sent.")
        logger.info("  %s %s · %s at %s", LEAD["first_name"], LEAD["last_name"], LEAD["job_title"], COMPANY["name"])
        logger.info("  Sent to: %s", TARGET_EMAIL)
        logger.info("───────────────────────────────────────────────")
        logger.info("  SUBJECT: %s", subject)
        logger.info("  BODY:\n%s", body)
        logger.info("═══════════════════════════════════════════════")


if __name__ == "__main__":
    asyncio.run(main())
