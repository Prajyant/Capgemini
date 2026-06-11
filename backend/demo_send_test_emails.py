"""
Demo Test Email Script
=======================
Creates sample leads and sends intro emails for testing.

Usage:
    python demo_send_test_emails.py <email1> [email2] [email3] ...

Example:
    python demo_send_test_emails.py teammate1@gmail.com teammate2@gmail.com

Each email becomes a separate lead with a unique persona.
The agent will send a personalized intro email to each.

Prerequisites:
    - Backend server running (uvicorn app.main:app --reload --port 8000)
    - Or run directly with: python demo_send_test_emails.py
"""
import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Sample personas for demo leads
PERSONAS = [
    {
        "first_name": "Alex",
        "last_name": "Rivera",
        "job_title": "VP of Marketing",
        "seniority_level": "VP",
        "company_name": "TechScale Inc",
        "industry": "B2B SaaS",
    },
    {
        "first_name": "Jordan",
        "last_name": "Chen",
        "job_title": "Head of Growth",
        "seniority_level": "Director",
        "company_name": "DataForge Analytics",
        "industry": "Enterprise Analytics",
    },
    {
        "first_name": "Sam",
        "last_name": "Patel",
        "job_title": "Director of Operations",
        "seniority_level": "Director",
        "company_name": "CloudNine Solutions",
        "industry": "Cloud Infrastructure",
    },
    {
        "first_name": "Morgan",
        "last_name": "Lee",
        "job_title": "CMO",
        "seniority_level": "C-Level",
        "company_name": "GrowthLoop AI",
        "industry": "Marketing Tech",
    },
    {
        "first_name": "Taylor",
        "last_name": "Kim",
        "job_title": "VP of Product",
        "seniority_level": "VP",
        "company_name": "NexaBridge Systems",
        "industry": "Supply Chain Tech",
    },
]


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("ERROR: Provide at least one email address as argument.")
        print("  python demo_send_test_emails.py teammate@gmail.com")
        sys.exit(1)

    emails = sys.argv[1:]
    logger.info("Starting demo email send for %d recipient(s)", len(emails))

    # Import app modules
    from app.database import init_db, get_db_context
    from app.models import Lead, Company, EmailEvent, AgentDecision
    from app.outreach.email_sender import generate_and_send
    from app.agent.decision_maker import _serialize_lead
    from sqlalchemy import select, delete as sql_delete

    await init_db()

    results = []

    async with get_db_context() as db:
        for i, email_addr in enumerate(emails):
            persona = PERSONAS[i % len(PERSONAS)]
            logger.info("Processing: %s as %s %s (%s)",
                        email_addr, persona["first_name"], persona["last_name"], persona["job_title"])

            # Check if lead already exists
            existing = (await db.execute(
                select(Lead).where(Lead.email == email_addr)
            )).scalar_one_or_none()

            if existing:
                # Clean up old data
                await db.execute(sql_delete(EmailEvent).where(EmailEvent.lead_id == existing.id))
                await db.execute(sql_delete(AgentDecision).where(AgentDecision.lead_id == existing.id))
                await db.delete(existing)
                await db.flush()
                logger.info("  Cleaned up existing lead data")

            # Get or create company
            company = (await db.execute(
                select(Company).where(Company.name == persona["company_name"])
            )).scalar_one_or_none()

            if not company:
                company = Company(
                    name=persona["company_name"],
                    industry=persona["industry"],
                    icp_fit_score=65,
                    intent_score=50,
                )
                db.add(company)
                await db.flush()

            # Create lead
            lead = Lead(
                email=email_addr,
                first_name=persona["first_name"],
                last_name=persona["last_name"],
                job_title=persona["job_title"],
                seniority_level=persona["seniority_level"],
                company_id=company.id,
                source="demo_script",
                state="enriched",
                enrichment_status="complete",
                enrichment_score=55,
            )
            db.add(lead)
            await db.flush()
            logger.info("  Created lead: %s (ID: %s)", lead.email, lead.id)

            # Send intro email
            try:
                event = await generate_and_send(db, lead)
                if event:
                    logger.info("  ✅ Email sent! Subject: %s", event.subject)
                    results.append({"email": email_addr, "status": "sent", "subject": event.subject})
                else:
                    logger.warning("  ⚠️ Email blocked by compliance")
                    results.append({"email": email_addr, "status": "blocked"})
            except Exception as e:
                logger.exception("  ❌ Send failed: %s", e)
                results.append({"email": email_addr, "status": "error", "error": str(e)})

        await db.flush()

    # Summary
    print("\n" + "=" * 60)
    print("DEMO EMAIL SEND SUMMARY")
    print("=" * 60)
    for r in results:
        status_icon = "✅" if r["status"] == "sent" else "❌"
        print(f"  {status_icon} {r['email']} — {r['status']}", end="")
        if r.get("subject"):
            print(f" — \"{r['subject']}\"", end="")
        print()
    print("=" * 60)
    print(f"\nTotal: {len(results)} | Sent: {sum(1 for r in results if r['status'] == 'sent')}")
    print("\nRecipients can now:")
    print("  1. Reply to the email (positive or negative)")
    print("  2. The agent will pick up the reply via IMAP within 2 minutes")
    print("  3. View the agent's decision on the dashboard at http://localhost:3000")


if __name__ == "__main__":
    asyncio.run(main())
