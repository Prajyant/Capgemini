"""
Agent reasoning test harness.

For each reply scenario, this script:
  1. Resets to a fresh lead with full context
  2. Records the intro email as 'sent'
  3. Records the buyer's reply (classified via the real classifier)
  4. Runs the REAL agent reasoning
  5. Prints expected decision vs the agent's actual decision + summary

Usage (with venv activated):
  python test_scenarios.py
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import delete, select

from app.database import get_db_context, init_db
from app.models import Lead, EmailEvent, AgentDecision, ABTest, Company
from app.nlp.reply_classifier import classify_reply
from app.agent.decision_maker import reason_for_lead

logging.basicConfig(level=logging.WARNING)  # quiet noise; we print our own
logger = logging.getLogger("test_scenarios")
logger.setLevel(logging.INFO)

TARGET_EMAIL = "lead-test@example.com"

COMPANY = {
    "name": "NorthBridge Analytics",
    "domain": "northbridgeanalytics.com",
    "industry": "Data Infrastructure / SaaS",
    "employee_count": 240,
    "employee_range": "200-499",
    "location": "Austin, TX",
    "funding_stage": "Series B",
    "tech_stack": ["Snowflake", "dbt", "Salesforce", "Outreach", "AWS"],
    "recent_news": [
        {"headline": "NorthBridge raises $40M Series B", "source": "TechCrunch",
         "url": "https://example.com/a", "published_at": "2026-06-10"},
        {"headline": "NorthBridge hiring 4 SDRs", "source": "LinkedIn",
         "url": "https://example.com/b", "published_at": "2026-06-15"},
    ],
    "intent_score": 82,
    "icp_fit_score": 90,
}

# (label, reply text, expected decision(s))
SCENARIOS = [
    ("Interested / wants to meet",
     "This sounds interesting. I'd be open to a quick call next week to learn more.",
     ["send_email", "suggest_call"]),
    ("Needs more info",
     "Before we talk, can you tell me how your platform is different from what Outreach already does for us?",
     ["send_email"]),
    ("Objection / competitor",
     "We're already using Outreach and pretty happy with it. Why would we switch?",
     ["send_email"]),
    ("Not now / timing",
     "We're heads-down on a product launch this quarter. Maybe revisit in Q4?",
     ["wait"]),
    ("Wrong person",
     "I'm not the right person for this — you'd want to talk to our RevOps lead.",
     ["send_email", "escalate_to_human"]),
    ("Unsubscribe",
     "Please remove me from your list and don't email again.",
     ["close_sequence"]),
    ("Ready to convert",
     "Yes let's do it. Send me a calendar invite for Tuesday afternoon.",
     ["send_email", "suggest_call"]),
]


async def reset_company(db) -> Company:
    company = Company(
        name=COMPANY["name"], domain=COMPANY["domain"], industry=COMPANY["industry"],
        employee_count=COMPANY["employee_count"], employee_range=COMPANY["employee_range"],
        location=COMPANY["location"], funding_stage=COMPANY["funding_stage"],
        tech_stack=COMPANY["tech_stack"], recent_news=COMPANY["recent_news"],
        intent_score=COMPANY["intent_score"], icp_fit_score=COMPANY["icp_fit_score"],
    )
    db.add(company)
    await db.flush()
    return company


async def build_lead(db, company) -> Lead:
    now = datetime.now(timezone.utc)
    lead = Lead(
        email=TARGET_EMAIL, first_name="Alaguraja", last_name="Narayanan",
        job_title="VP of Engineering", seniority_level="VP",
        linkedin_url="https://linkedin.com/in/test", phone="+1-415-555-0142",
        company_id=company.id, source="test", enrichment_status="complete",
        enrichment_score=90, state="contacted",
        state_updated_at=now - timedelta(days=1),
        linkedin_signals={"tenure_months": 28, "is_active": True, "connections_count": "500+"},
        company_news=COMPANY["recent_news"], tech_stack=COMPANY["tech_stack"],
        intent_signals={"intent_score": 82, "funding_recent": True, "hiring_count": 4,
                        "tech_replacement_signals": ["Outreach"]},
    )
    db.add(lead)
    await db.flush()
    # Intro email already sent
    db.add(EmailEvent(
        lead_id=lead.id, event_type="sent", channel="email",
        subject="Scaling Data Platforms", ab_variant="B",
        occurred_at=now - timedelta(hours=20),
    ))
    db.add(EmailEvent(
        lead_id=lead.id, event_type="opened", channel="email",
        occurred_at=now - timedelta(hours=18),
    ))
    await db.flush()
    return lead


async def run_one(label: str, reply_text: str, expected: list[str]) -> dict:
    from app.agent.reasoning_engine import run_reasoning

    # classify the reply (real classifier)
    classification = await classify_reply(reply_text)
    now = datetime.now(timezone.utc)

    # Build serialized profile + history directly (no DB writes needed)
    profile = {
        "first_name": "Alaguraja", "last_name": "Narayanan",
        "job_title": "VP of Engineering", "seniority_level": "VP",
        "linkedin_url": "https://linkedin.com/in/test", "phone": "+1-415-555-0142",
        "opted_out": False, "enrichment_score": 90,
        "linkedin_signals": {"tenure_months": 28, "is_active": True, "connections_count": "500+"},
        "company_news": COMPANY["recent_news"], "tech_stack": COMPANY["tech_stack"],
        "intent_signals": {"intent_score": 82, "funding_recent": True, "hiring_count": 4,
                           "tech_replacement_signals": ["Outreach"]},
        "state_updated_at": now.isoformat(),
        "company_name": COMPANY["name"], "company_domain": COMPANY["domain"],
        "industry": COMPANY["industry"], "employee_count": COMPANY["employee_count"],
        "employee_range": COMPANY["employee_range"], "icp_fit_score": 90,
        "intent_score": 82, "funding_stage": "Series B",
    }
    history = [
        {"event_type": "sent", "channel": "email", "subject": "Scaling Data Platforms",
         "occurred_at": (now - timedelta(hours=20)).isoformat()},
        {"event_type": "opened", "channel": "email",
         "occurred_at": (now - timedelta(hours=18)).isoformat()},
        {"event_type": "replied", "channel": "email", "subject": "Re: Scaling Data Platforms",
         "reply_content": reply_text,
         "reply_sentiment": classification.get("sentiment"),
         "reply_intent": classification.get("intent"),
         "occurred_at": now.isoformat()},
    ]

    result = run_reasoning(
        lead_id="test", lead_profile=profile,
        engagement_history=history, current_state="replied",
    )
    actual = result.get("decision", "?")
    return {
        "label": label, "reply": reply_text,
        "intent": classification.get("intent"), "sentiment": classification.get("sentiment"),
        "expected": expected, "actual": actual,
        "confidence": float(result.get("confidence", 0.0)),
        "summary": result.get("reasoning_summary", ""),
        "pass": actual in expected,
    }


async def main():
    await init_db()
    print("\n" + "=" * 70)
    print("  AGENT REASONING TEST — all reply scenarios")
    print("=" * 70)

    results = []
    for label, reply, expected in SCENARIOS:
        try:
            r = await run_one(label, reply, expected)
        except Exception as e:
            r = {"label": label, "reply": reply, "expected": expected,
                 "actual": f"ERROR: {e}", "pass": False, "intent": "?",
                 "sentiment": "?", "confidence": 0, "summary": str(e)}
        results.append(r)

        status = "✅ PASS" if r["pass"] else "❌ MISMATCH"
        print(f"\n{status}  {r['label']}")
        print(f"   Reply:      {r['reply']}")
        print(f"   Classified: intent={r['intent']} sentiment={r['sentiment']}")
        print(f"   Expected:   {r['expected']}")
        print(f"   Agent did:  {r['actual']} (confidence {r['confidence']:.0%})")
        print(f"   Summary:    {r['summary']}")
        await asyncio.sleep(1)  # gentle on rate limits

    passed = sum(1 for r in results if r["pass"])
    print("\n" + "=" * 70)
    print(f"  RESULT: {passed}/{len(results)} scenarios matched expectations")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
