"""
Seed script — populates demo data so evaluators see a populated dashboard
within 60 seconds of opening the app.

Usage:
  docker-compose exec backend python seed.py
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import delete, select

from app.database import get_db_context, init_db
from app.models import (
    Lead, Company, Sequence, SequenceStep, EmailEvent,
    AgentDecision, ABTest, PromptStrategy,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


DEMO_COMPANIES = [
    {
        "name": "Acme SaaS", "domain": "acmesaas.com", "industry": "SaaS",
        "employee_count": 120, "employee_range": "50-199",
        "location": "San Francisco, CA", "funding_stage": "Series B",
        "icp_fit_score": 92, "intent_score": 65,
        "tech_stack": ["Salesforce", "Outreach", "Slack", "AWS", "Snowflake"],
        "recent_news": [
            {"headline": "Acme SaaS launches new AI workflow product", "source": "TechCrunch",
             "url": "https://example.com/acme", "published_at": "2026-05-20"},
        ],
    },
    {
        "name": "TechFlow Inc", "domain": "techflow.io", "industry": "SaaS",
        "employee_count": 80, "employee_range": "50-199",
        "location": "Austin, TX", "funding_stage": "Series A",
        "icp_fit_score": 88, "intent_score": 45,
        "tech_stack": ["Outreach", "HubSpot", "Notion"],
    },
    {
        "name": "DataBridge", "domain": "databridge.ai", "industry": "Data Infrastructure",
        "employee_count": 35, "employee_range": "1-49",
        "location": "New York, NY", "funding_stage": "Series A",
        "icp_fit_score": 84, "intent_score": 88,
        "tech_stack": ["Apollo", "Salesforce", "Linear"],
        "recent_news": [
            {"headline": "DataBridge raises $18M Series A to scale data pipelines",
             "source": "VentureBeat", "url": "https://example.com/db",
             "published_at": "2026-05-22"},
            {"headline": "DataBridge hiring 3 SDRs to expand sales team",
             "source": "LinkedIn", "url": "https://example.com/db-jobs",
             "published_at": "2026-05-23"},
        ],
    },
    {
        "name": "CloudMetrics", "domain": "cloudmetrics.io", "industry": "DevOps",
        "employee_count": 200, "employee_range": "200-499",
        "location": "Seattle, WA", "funding_stage": "Series C",
        "icp_fit_score": 78, "intent_score": 30,
        "tech_stack": ["Datadog", "PagerDuty", "Terraform"],
    },
    {
        "name": "BuildFast Tools", "domain": "buildfast.dev", "industry": "Developer Tools",
        "employee_count": 60, "employee_range": "50-199",
        "location": "Remote", "funding_stage": "Seed",
        "icp_fit_score": 90, "intent_score": 72,
        "tech_stack": ["GitHub", "Linear", "Vercel", "Stripe"],
    },
]


DEMO_LEADS = [
    {
        "email": "sarah.chen@acmesaas.com", "first_name": "Sarah", "last_name": "Chen",
        "job_title": "VP of Sales", "seniority_level": "VP",
        "linkedin_url": "https://linkedin.com/in/sarah-chen-demo",
        "phone": "+1-415-555-0101", "company_name": "Acme SaaS",
        "state": "engaged", "enrichment_score": 92,
        "scenario": "engaged_no_reply",
    },
    {
        "email": "marcus.williams@techflow.io", "first_name": "Marcus", "last_name": "Williams",
        "job_title": "Head of Revenue", "seniority_level": "Director",
        "linkedin_url": "https://linkedin.com/in/marcus-w-demo",
        "company_name": "TechFlow Inc",
        "state": "replied", "enrichment_score": 85,
        "scenario": "objection_competitor",
    },
    {
        "email": "priya.patel@databridge.ai", "first_name": "Priya", "last_name": "Patel",
        "job_title": "Founder & CEO", "seniority_level": "C-Level",
        "linkedin_url": "https://linkedin.com/in/priya-patel-demo",
        "company_name": "DataBridge",
        "state": "enriched", "enrichment_score": 95,
        "scenario": "fresh_high_intent",
    },
    {
        "email": "james.obrien@cloudmetrics.io", "first_name": "James", "last_name": "O'Brien",
        "job_title": "Sales Director", "seniority_level": "Director",
        "linkedin_url": "https://linkedin.com/in/james-obrien-demo",
        "phone": "+1-206-555-0199", "company_name": "CloudMetrics",
        "state": "cold", "enrichment_score": 70,
        "scenario": "cold_low_confidence",
    },
    {
        "email": "ananya.sharma@buildfast.dev", "first_name": "Ananya", "last_name": "Sharma",
        "job_title": "CTO", "seniority_level": "C-Level",
        "linkedin_url": "https://linkedin.com/in/ananya-sharma-demo",
        "company_name": "BuildFast Tools",
        "state": "converted", "enrichment_score": 98,
        "scenario": "converted_success",
    },
]


SCENARIO_DECISIONS = {
    "engaged_no_reply": {
        "decision_type": "send_linkedin_dm",
        "channel_selected": "linkedin",
        "confidence_score": 0.82,
        "reasoning_summary": (
            "I chose to wait 3 days and switch to LinkedIn. Sarah opened the email twice "
            "in 24 hours but hasn't replied — high curiosity, low urgency. A softer, less "
            "intrusive channel may convert this engagement signal into a conversation."
        ),
        "full_reasoning": {
            "signal_analysis": "Two opens within 24 hours, no clicks, no reply. Strong attention signal but no commitment.",
            "situation_assessment": "Lead is curious but not urgent. Email channel may have peaked.",
            "options_considered": [
                "Send another email immediately — risk of feeling pushy",
                "Wait 3 days then switch to LinkedIn — softer touch, matches engagement pattern",
                "Suggest a call — too aggressive for current signal",
            ],
            "decision": "send_linkedin_dm",
            "confidence": 0.82,
            "reasoning_summary": "I chose to wait 3 days and switch to LinkedIn...",
            "next_wait_days": 3,
            "email_personalisation_hooks": [],
        },
    },
    "objection_competitor": {
        "decision_type": "send_email",
        "channel_selected": "email",
        "confidence_score": 0.78,
        "reasoning_summary": (
            "I chose to send a competitor displacement email. Marcus replied that they "
            "use Outreach. I'm focusing on our reasoning transparency — explaining each "
            "decision in plain English — which Outreach does not offer."
        ),
        "full_reasoning": {
            "signal_analysis": "Reply received with objection: already using Outreach. Sentiment: objection.",
            "situation_assessment": "Lead is engaged enough to reply with their stack. Open to comparison if differentiated value is clear.",
            "options_considered": [
                "Close sequence — premature, they engaged",
                "Send displacement email focused on transparency — differentiates without naming competitor",
                "Escalate to AE — better as a follow-up after value is established",
            ],
            "decision": "send_email",
            "confidence": 0.78,
            "reasoning_summary": "I chose to send a competitor displacement email...",
            "next_wait_days": 4,
            "email_personalisation_hooks": ["reasoning transparency", "explainable decisions"],
        },
    },
    "fresh_high_intent": {
        "decision_type": "send_email",
        "channel_selected": "email",
        "confidence_score": 0.94,
        "reasoning_summary": (
            "I chose to send an intro email immediately. DataBridge just raised a Series A "
            "(news signal, 2 days old) and is hiring 3 SDRs. This is one of the highest "
            "buying-intent windows for sales tooling. Funding congratulations is a natural hook."
        ),
        "full_reasoning": {
            "signal_analysis": "Series A funding 2 days ago + active hiring of 3 SDRs. Intent score 88/100.",
            "situation_assessment": "Peak buying window. Founder/CEO is reachable. ICP fit 84.",
            "options_considered": [
                "Wait for inbound — risk of competitor reaching first",
                "Send intro email now with funding congrats hook — highest expected value",
                "Cold call CEO — too aggressive without prior touch",
            ],
            "decision": "send_email",
            "confidence": 0.94,
            "reasoning_summary": "I chose to send an intro email immediately...",
            "next_wait_days": 3,
            "email_personalisation_hooks": ["Series A funding", "hiring 3 SDRs"],
        },
    },
    "cold_low_confidence": {
        "decision_type": "escalate_to_human",
        "channel_selected": None,
        "confidence_score": 0.58,
        "reasoning_summary": (
            "Confidence too low (58%) to act autonomously. Zero engagement after 7 days "
            "and 2 emails sent. Original recommendation was to suggest a phone call, but "
            "signals are too weak to commit autonomously. Flagged for SDR review."
        ),
        "full_reasoning": {
            "signal_analysis": "0 opens, 0 clicks, 0 replies after 2 emails over 7 days.",
            "situation_assessment": "Either wrong contact, wrong timing, or email landed in spam. Cannot determine cause.",
            "options_considered": [
                "Send 3rd email — diminishing returns, may damage sender reputation",
                "Suggest call — could work but no signal to support confidence",
                "Close sequence — wastes ICP fit",
                "Escalate to human — best given uncertainty",
            ],
            "decision": "suggest_call",
            "confidence": 0.58,
            "reasoning_summary": "Confidence too low to act autonomously...",
            "next_wait_days": 1,
            "email_personalisation_hooks": [],
        },
    },
    "converted_success": {
        "decision_type": "close_sequence",
        "channel_selected": None,
        "confidence_score": 1.0,
        "reasoning_summary": (
            "I chose to close the sequence. Ananya replied positively and a meeting was "
            "booked. Sequence has fulfilled its purpose — handing off to AE and removing "
            "from automation queue."
        ),
        "full_reasoning": {
            "signal_analysis": "Positive reply with meeting confirmation. Goal achieved.",
            "situation_assessment": "Conversion. No further automated outreach needed.",
            "options_considered": ["Continue sequence — counterproductive", "Close sequence — correct"],
            "decision": "close_sequence",
            "confidence": 1.0,
            "reasoning_summary": "I chose to close the sequence...",
            "next_wait_days": 0,
            "email_personalisation_hooks": [],
        },
    },
}


async def reset_demo_data(db) -> None:
    """Wipe demo tables. Safe — only runs in dev."""
    for model in (AgentDecision, EmailEvent, ABTest, SequenceStep, Sequence,
                  Lead, Company, PromptStrategy):
        await db.execute(delete(model))


async def seed_companies(db) -> dict[str, Company]:
    """Insert demo companies. Returns dict by name."""
    out: dict[str, Company] = {}
    for c in DEMO_COMPANIES:
        company = Company(
            name=c["name"],
            domain=c["domain"],
            industry=c["industry"],
            employee_count=c["employee_count"],
            employee_range=c["employee_range"],
            location=c["location"],
            funding_stage=c["funding_stage"],
            tech_stack=c["tech_stack"],
            recent_news=c.get("recent_news", []),
            intent_score=c["intent_score"],
            icp_fit_score=c["icp_fit_score"],
        )
        db.add(company)
        await db.flush()
        out[c["name"]] = company
    return out


async def seed_leads(db, companies: dict[str, Company]) -> list[Lead]:
    now = datetime.now(timezone.utc)
    leads: list[Lead] = []
    for ld in DEMO_LEADS:
        company = companies[ld["company_name"]]
        lead = Lead(
            email=ld["email"],
            first_name=ld["first_name"],
            last_name=ld["last_name"],
            job_title=ld["job_title"],
            seniority_level=ld["seniority_level"],
            linkedin_url=ld.get("linkedin_url"),
            phone=ld.get("phone"),
            company_id=company.id,
            source="seed",
            enrichment_status="complete",
            enrichment_score=ld["enrichment_score"],
            state=ld["state"],
            state_updated_at=now - timedelta(days=2),
            linkedin_signals={
                "tenure_months": 24,
                "post_frequency": "weekly",
                "is_active": True,
            },
            company_news=company.recent_news or [],
            tech_stack=company.tech_stack,
            intent_signals={
                "intent_score": company.intent_score,
                "funding_recent": company.funding_stage in ("Series A", "Series B"),
                "hiring_count": 3 if "DataBridge" in company.name else 0,
                "tech_replacement_signals": [
                    t for t in (company.tech_stack or [])
                    if t.lower() in ("outreach", "salesloft", "apollo")
                ],
            },
        )
        db.add(lead)
        await db.flush()
        leads.append(lead)
    return leads


async def seed_email_events(db, leads: list[Lead]) -> None:
    """Create realistic engagement history."""
    now = datetime.now(timezone.utc)
    for lead in leads:
        scenario = next(
            (l["scenario"] for l in DEMO_LEADS if l["email"] == lead.email),
            None,
        )

        if scenario == "engaged_no_reply":
            db.add(EmailEvent(
                lead_id=lead.id, event_type="sent", channel="email",
                subject="Quick thought on your Q3 outreach",
                ab_variant="A", occurred_at=now - timedelta(days=2),
            ))
            db.add(EmailEvent(
                lead_id=lead.id, event_type="opened", channel="email",
                occurred_at=now - timedelta(days=2, hours=-3),
            ))
            db.add(EmailEvent(
                lead_id=lead.id, event_type="opened", channel="email",
                occurred_at=now - timedelta(days=1, hours=-20),
            ))

        elif scenario == "objection_competitor":
            db.add(EmailEvent(
                lead_id=lead.id, event_type="sent", channel="email",
                subject="Reasoning over volume",
                ab_variant="B", occurred_at=now - timedelta(days=3),
            ))
            db.add(EmailEvent(
                lead_id=lead.id, event_type="opened", channel="email",
                occurred_at=now - timedelta(days=3, hours=-1),
            ))
            db.add(EmailEvent(
                lead_id=lead.id, event_type="replied", channel="email",
                reply_content="Thanks but we already use Outreach — happy with it.",
                reply_sentiment="objection", reply_intent="competitor",
                occurred_at=now - timedelta(days=2),
            ))

        elif scenario == "cold_low_confidence":
            db.add(EmailEvent(
                lead_id=lead.id, event_type="sent", channel="email",
                subject="Cloud monitoring at scale",
                ab_variant="A", occurred_at=now - timedelta(days=7),
            ))
            db.add(EmailEvent(
                lead_id=lead.id, event_type="sent", channel="email",
                subject="Following up on monitoring",
                ab_variant="B", occurred_at=now - timedelta(days=3),
            ))

        elif scenario == "converted_success":
            db.add(EmailEvent(
                lead_id=lead.id, event_type="sent", channel="email",
                subject="Quick question on your build pipeline",
                ab_variant="A", occurred_at=now - timedelta(days=5),
            ))
            db.add(EmailEvent(
                lead_id=lead.id, event_type="opened", channel="email",
                occurred_at=now - timedelta(days=5, hours=-2),
            ))
            db.add(EmailEvent(
                lead_id=lead.id, event_type="clicked", channel="email",
                clicked_url="https://salesagent.ai/demo",
                occurred_at=now - timedelta(days=5, hours=-3),
            ))
            db.add(EmailEvent(
                lead_id=lead.id, event_type="replied", channel="email",
                reply_content="Yes, would love to chat. Thursday 2pm works.",
                reply_sentiment="positive", reply_intent="meeting_requested",
                occurred_at=now - timedelta(days=4),
            ))
    await db.flush()


async def seed_agent_decisions(db, leads: list[Lead]) -> None:
    """Create the showcase agent decisions."""
    now = datetime.now(timezone.utc)
    for lead in leads:
        scenario = next(
            (l["scenario"] for l in DEMO_LEADS if l["email"] == lead.email),
            None,
        )
        if not scenario or scenario not in SCENARIO_DECISIONS:
            continue
        d = SCENARIO_DECISIONS[scenario]
        decision = AgentDecision(
            lead_id=lead.id,
            decision_type=d["decision_type"],
            channel_selected=d["channel_selected"],
            confidence_score=d["confidence_score"],
            reasoning_summary=d["reasoning_summary"],
            full_reasoning=d["full_reasoning"],
            signals_observed={
                "enrichment_score": lead.enrichment_score,
                "state": lead.state,
            },
            lead_state_at_decision=lead.state,
            was_approved=True if scenario == "converted_success" else None,
            executed_at=now if scenario == "converted_success" else None,
        )
        db.add(decision)
    await db.flush()


async def seed_weekly_history(db, leads: list[Lead]) -> None:
    """Create historical email events that produce a rising reply rate trend."""
    now = datetime.now(timezone.utc)
    # Anchor lead for synthetic history
    anchor = leads[0]

    weekly = [
        # (weeks_ago, sent_count, replied_count) — rising trend 3.2% → 11.7%
        (4, 124, 4),    # ~3.2%
        (3, 138, 8),    # ~5.8%
        (2, 142, 12),   # ~8.4%
        (1, 137, 16),   # ~11.7%
    ]
    for weeks_ago, sent_count, replied_count in weekly:
        base = now - timedelta(days=7 * weeks_ago + 3)
        for i in range(sent_count):
            db.add(EmailEvent(
                lead_id=anchor.id,
                event_type="sent",
                channel="email",
                subject=f"Weekly synthetic send {weeks_ago}-{i}",
                ab_variant="A" if i % 2 == 0 else "B",
                occurred_at=base + timedelta(minutes=i * 3),
            ))
        for i in range(replied_count):
            db.add(EmailEvent(
                lead_id=anchor.id,
                event_type="replied",
                channel="email",
                reply_content="Sounds interesting, tell me more.",
                reply_sentiment="positive",
                reply_intent="interested",
                occurred_at=base + timedelta(hours=12, minutes=i * 5),
            ))
        # Some opens for funnel realism
        for i in range(int(sent_count * 0.45)):
            db.add(EmailEvent(
                lead_id=anchor.id,
                event_type="opened",
                channel="email",
                occurred_at=base + timedelta(hours=4, minutes=i * 2),
            ))
        for i in range(int(sent_count * 0.18)):
            db.add(EmailEvent(
                lead_id=anchor.id,
                event_type="clicked",
                channel="email",
                clicked_url="https://salesagent.ai/demo",
                occurred_at=base + timedelta(hours=6, minutes=i * 2),
            ))
    await db.flush()


async def seed_ab_tests(db, leads: list[Lead]) -> None:
    """Create A/B test rows showing variant B winning."""
    now = datetime.now(timezone.utc)
    for i in range(3):
        db.add(ABTest(
            lead_id=leads[i % len(leads)].id,
            variant_a_subject="Quick thought on your sales process",
            variant_a_body="Problem-led intro variant",
            variant_b_subject=f"3 SaaS teams shifted from volume to reasoning in {2025+i}",
            variant_b_body="Insight-led intro variant",
            variant_a_opens=42 + i * 5,
            variant_a_replies=2 + i,
            variant_b_opens=58 + i * 7,
            variant_b_replies=8 + i * 2,
            winner="B",
            decided_at=now - timedelta(days=i + 1),
            observation_window_hours=48,
        ))
    await db.flush()


async def seed_prompt_strategies(db) -> None:
    strategies = [
        ("SaaS", "VP", "problem_led", 0.087, 145),
        ("SaaS", "VP", "insight", 0.121, 138),
        ("SaaS", "C-Level", "social_proof", 0.094, 95),
        ("SaaS", "Director", "question", 0.103, 167),
        ("DevOps", "Director", "insight", 0.078, 88),
    ]
    for vert, sen, hook, rate, n in strategies:
        db.add(PromptStrategy(
            vertical=vert, seniority_level=sen, hook_type=hook,
            subject_pattern=f"{hook} pattern subject",
            body_pattern=f"{hook} pattern body",
            avg_reply_rate=rate, sample_size=n, is_active=True,
        ))
    await db.flush()


async def seed_default_sequence(db) -> None:
    seq = Sequence(name="Default 3-Touch SaaS", vertical="SaaS", total_steps=3)
    db.add(seq)
    await db.flush()
    for i, (channel, wait, subj) in enumerate([
        ("email", 0, "Quick thought, {first_name}"),
        ("email", 3, "Following up on {company_name}"),
        ("email", 5, "Last note from me"),
    ], start=1):
        db.add(SequenceStep(
            sequence_id=seq.id, step_number=i, channel=channel,
            subject_template=subj,
            body_template="Generated at runtime by LLM.",
            wait_days=wait,
        ))
    await db.flush()


async def main():
    await init_db()
    async with get_db_context() as db:
        logger.info("Resetting demo data...")
        await reset_demo_data(db)
        logger.info("Seeding companies...")
        companies = await seed_companies(db)
        logger.info("Seeding leads...")
        leads = await seed_leads(db, companies)
        logger.info("Seeding email events...")
        await seed_email_events(db, leads)
        logger.info("Seeding agent decisions...")
        await seed_agent_decisions(db, leads)
        logger.info("Seeding weekly history (rising reply rate)...")
        await seed_weekly_history(db, leads)
        logger.info("Seeding A/B tests...")
        await seed_ab_tests(db, leads)
        logger.info("Seeding prompt strategies...")
        await seed_prompt_strategies(db)
        logger.info("Seeding default sequence...")
        await seed_default_sequence(db)
    logger.info("✓ Seed complete. Open http://localhost:3000")


if __name__ == "__main__":
    asyncio.run(main())
