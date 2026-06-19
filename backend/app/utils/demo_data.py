"""
Hard-coded demo lead roster.

Used by the `POST /api/leads/seed-demo` endpoint to bootstrap a richly
enriched pipeline straight from the dashboard, replacing the old
`demo_send.py` terminal script.

Each entry contains everything the agent needs to write an interesting
first email: persona signals on the lead, plus company news, tech stack
and intent score on their employer.
"""
from typing import Any


# 15 demo leads modelled after `backend/demo-leads.csv` but enriched with
# realistic context the LLM can reason over (recent news, intent signals,
# tech stack, LinkedIn behaviour, ICP fit).
DEMO_LEADS: list[dict[str, Any]] = [
    {
        "lead": {
            "first_name": "Marcus",
            "last_name": "Johnson",
            "job_title": "VP of Sales",
            "seniority_level": "VP",
            "linkedin_url": "https://linkedin.com/in/marcus-johnson-demo",
            "phone": "+1-555-0142",
            "linkedin_signals": {
                "tenure_months": 22,
                "post_frequency": "weekly",
                "recent_post_topics": ["outbound strategy", "AI in GTM", "rep productivity"],
                "is_active": True,
            },
        },
        "company": {
            "name": "Clay",
            "domain": "clay.com",
            "industry": "Sales Intelligence",
            "employee_count": 150,
            "location": "New York, NY",
            "funding_stage": "Series B",
            "tech_stack": ["Salesforce", "Outreach", "Apollo", "Clearbit", "Slack"],
            "recent_news": [
                {
                    "headline": "Clay raises $46M Series B led by Sequoia to expand data platform",
                    "source": "TechCrunch",
                    "published_at": "2026-06-10",
                },
                {
                    "headline": "Clay launches AI agent integrations for revenue teams",
                    "source": "Clay Blog",
                    "published_at": "2026-06-15",
                },
            ],
            "intent_score": 88,
            "icp_fit_score": 94,
        },
    },
    {
        "lead": {
            "first_name": "Priya",
            "last_name": "Sharma",
            "job_title": "Head of Revenue",
            "seniority_level": "Director",
            "linkedin_url": "https://linkedin.com/in/priya-sharma-demo",
            "phone": None,
            "linkedin_signals": {
                "tenure_months": 14,
                "post_frequency": "biweekly",
                "recent_post_topics": ["RevOps", "SaaS metrics", "team scaling"],
                "is_active": True,
            },
        },
        "company": {
            "name": "Mercury",
            "domain": "mercury.com",
            "industry": "FinTech",
            "employee_count": 420,
            "location": "San Francisco, CA",
            "funding_stage": "Series C",
            "tech_stack": ["HubSpot", "Salesloft", "Segment", "Looker", "Stripe"],
            "recent_news": [
                {
                    "headline": "Mercury surpasses 200K business banking customers",
                    "source": "Bloomberg",
                    "published_at": "2026-06-08",
                },
                {
                    "headline": "Mercury hires 12 SDRs to expand mid-market motion",
                    "source": "LinkedIn",
                    "published_at": "2026-06-14",
                },
            ],
            "intent_score": 82,
            "icp_fit_score": 90,
        },
    },
    {
        "lead": {
            "first_name": "David",
            "last_name": "Chen",
            "job_title": "Director of Marketing",
            "seniority_level": "Director",
            "linkedin_url": "https://linkedin.com/in/david-chen-demo",
            "phone": "+1-555-0167",
            "linkedin_signals": {
                "tenure_months": 19,
                "post_frequency": "weekly",
                "recent_post_topics": ["product-led growth", "developer marketing"],
                "is_active": True,
            },
        },
        "company": {
            "name": "Linear",
            "domain": "linear.app",
            "industry": "Developer Tools",
            "employee_count": 110,
            "location": "Remote",
            "funding_stage": "Series B",
            "tech_stack": ["Customer.io", "Mixpanel", "PostHog", "Notion"],
            "recent_news": [
                {
                    "headline": "Linear releases new asynchronous review workflow",
                    "source": "Linear Blog",
                    "published_at": "2026-06-11",
                },
            ],
            "intent_score": 71,
            "icp_fit_score": 85,
        },
    },
    {
        "lead": {
            "first_name": "Sarah",
            "last_name": "Williams",
            "job_title": "Founder & CEO",
            "seniority_level": "C-Level",
            "linkedin_url": "https://linkedin.com/in/sarah-williams-demo",
            "phone": "+1-555-0189",
            "linkedin_signals": {
                "tenure_months": 36,
                "post_frequency": "weekly",
                "recent_post_topics": ["data analytics", "AI assistants", "fundraising"],
                "is_active": True,
            },
        },
        "company": {
            "name": "Hex",
            "domain": "hex.tech",
            "industry": "Data Analytics",
            "employee_count": 120,
            "location": "San Francisco, CA",
            "funding_stage": "Series B",
            "tech_stack": ["Snowflake", "dbt", "Airtable", "HubSpot"],
            "recent_news": [
                {
                    "headline": "Hex launches Magic AI for data exploration",
                    "source": "Hex Blog",
                    "published_at": "2026-06-13",
                },
            ],
            "intent_score": 75,
            "icp_fit_score": 88,
        },
    },
    {
        "lead": {
            "first_name": "James",
            "last_name": "Patel",
            "job_title": "Head of Growth",
            "seniority_level": "Director",
            "linkedin_url": "https://linkedin.com/in/james-patel-demo",
            "phone": None,
            "linkedin_signals": {
                "tenure_months": 11,
                "post_frequency": "biweekly",
                "recent_post_topics": ["growth experiments", "funnel analytics"],
                "is_active": True,
            },
        },
        "company": {
            "name": "PostHog",
            "domain": "posthog.com",
            "industry": "Product Analytics",
            "employee_count": 85,
            "location": "Remote",
            "funding_stage": "Series B",
            "tech_stack": ["GitHub", "Slack", "Linear", "Notion"],
            "recent_news": [
                {
                    "headline": "PostHog rolls out session replay for mobile apps",
                    "source": "PostHog Blog",
                    "published_at": "2026-06-09",
                },
            ],
            "intent_score": 68,
            "icp_fit_score": 80,
        },
    },
    {
        "lead": {
            "first_name": "Emily",
            "last_name": "Rodriguez",
            "job_title": "VP of Marketing",
            "seniority_level": "VP",
            "linkedin_url": "https://linkedin.com/in/emily-rodriguez-demo",
            "phone": "+1-555-0211",
            "linkedin_signals": {
                "tenure_months": 27,
                "post_frequency": "weekly",
                "recent_post_topics": ["developer marketing", "ABM", "content strategy"],
                "is_active": True,
            },
        },
        "company": {
            "name": "Vercel",
            "domain": "vercel.com",
            "industry": "Developer Tools",
            "employee_count": 350,
            "location": "San Francisco, CA",
            "funding_stage": "Series D",
            "tech_stack": ["HubSpot", "Salesforce", "Outreach", "Segment"],
            "recent_news": [
                {
                    "headline": "Vercel announces v0 enterprise tier",
                    "source": "Vercel Blog",
                    "published_at": "2026-06-12",
                },
            ],
            "intent_score": 79,
            "icp_fit_score": 91,
        },
    },
    {
        "lead": {
            "first_name": "Michael",
            "last_name": "Thompson",
            "job_title": "Director of Sales",
            "seniority_level": "Director",
            "linkedin_url": "https://linkedin.com/in/michael-thompson-demo",
            "phone": None,
            "linkedin_signals": {
                "tenure_months": 16,
                "post_frequency": "occasional",
                "recent_post_topics": ["enterprise sales", "internal tools"],
                "is_active": True,
            },
        },
        "company": {
            "name": "Retool",
            "domain": "retool.com",
            "industry": "Developer Tools",
            "employee_count": 400,
            "location": "San Francisco, CA",
            "funding_stage": "Series C",
            "tech_stack": ["Salesforce", "Gong", "Outreach", "Slack"],
            "recent_news": [
                {
                    "headline": "Retool releases AI agent builder",
                    "source": "Retool Blog",
                    "published_at": "2026-06-07",
                },
            ],
            "intent_score": 73,
            "icp_fit_score": 87,
        },
    },
    {
        "lead": {
            "first_name": "Anika",
            "last_name": "Reddy",
            "job_title": "Chief Revenue Officer",
            "seniority_level": "C-Level",
            "linkedin_url": "https://linkedin.com/in/anika-reddy-demo",
            "phone": "+1-555-0234",
            "linkedin_signals": {
                "tenure_months": 9,
                "post_frequency": "weekly",
                "recent_post_topics": ["AI infra", "GTM strategy", "vector databases"],
                "is_active": True,
            },
        },
        "company": {
            "name": "Pinecone",
            "domain": "pinecone.io",
            "industry": "AI Infrastructure",
            "employee_count": 210,
            "location": "New York, NY",
            "funding_stage": "Series B",
            "tech_stack": ["Salesforce", "HubSpot", "Outreach", "Snowflake"],
            "recent_news": [
                {
                    "headline": "Pinecone introduces serverless vector search",
                    "source": "Pinecone Blog",
                    "published_at": "2026-06-10",
                },
                {
                    "headline": "Pinecone hires new CRO Anika Reddy from Snowflake",
                    "source": "Forbes",
                    "published_at": "2026-06-04",
                },
            ],
            "intent_score": 91,
            "icp_fit_score": 95,
        },
    },
    {
        "lead": {
            "first_name": "Ryan",
            "last_name": "O'Brien",
            "job_title": "VP of Demand Generation",
            "seniority_level": "VP",
            "linkedin_url": "https://linkedin.com/in/ryan-obrien-demo",
            "phone": None,
            "linkedin_signals": {
                "tenure_months": 13,
                "post_frequency": "biweekly",
                "recent_post_topics": ["demand gen", "ABM", "AI in marketing"],
                "is_active": True,
            },
        },
        "company": {
            "name": "Modal Labs",
            "domain": "modal.com",
            "industry": "AI Infrastructure",
            "employee_count": 75,
            "location": "San Francisco, CA",
            "funding_stage": "Series A",
            "tech_stack": ["HubSpot", "Mixpanel", "Linear", "Notion"],
            "recent_news": [
                {
                    "headline": "Modal launches GPU pricing optimizer for ML teams",
                    "source": "Modal Blog",
                    "published_at": "2026-06-11",
                },
            ],
            "intent_score": 70,
            "icp_fit_score": 83,
        },
    },
    {
        "lead": {
            "first_name": "Olivia",
            "last_name": "Martinez",
            "job_title": "Head of Sales",
            "seniority_level": "Director",
            "linkedin_url": "https://linkedin.com/in/olivia-martinez-demo",
            "phone": "+1-555-0256",
            "linkedin_signals": {
                "tenure_months": 18,
                "post_frequency": "weekly",
                "recent_post_topics": ["experimentation", "feature flags", "ICP fit"],
                "is_active": True,
            },
        },
        "company": {
            "name": "Statsig",
            "domain": "statsig.com",
            "industry": "Feature Flags",
            "employee_count": 140,
            "location": "Seattle, WA",
            "funding_stage": "Series B",
            "tech_stack": ["Salesforce", "Salesloft", "Mixpanel", "Snowflake"],
            "recent_news": [
                {
                    "headline": "Statsig closes $43M Series B to scale experimentation platform",
                    "source": "VentureBeat",
                    "published_at": "2026-06-06",
                },
            ],
            "intent_score": 80,
            "icp_fit_score": 89,
        },
    },
    {
        "lead": {
            "first_name": "Daniel",
            "last_name": "Kim",
            "job_title": "Director of Marketing",
            "seniority_level": "Director",
            "linkedin_url": "https://linkedin.com/in/daniel-kim-demo",
            "phone": None,
            "linkedin_signals": {
                "tenure_months": 21,
                "post_frequency": "biweekly",
                "recent_post_topics": ["data activation", "reverse ETL", "RevOps"],
                "is_active": True,
            },
        },
        "company": {
            "name": "Hightouch",
            "domain": "hightouch.com",
            "industry": "Data Activation",
            "employee_count": 130,
            "location": "San Francisco, CA",
            "funding_stage": "Series B",
            "tech_stack": ["Snowflake", "Segment", "HubSpot", "Salesforce"],
            "recent_news": [
                {
                    "headline": "Hightouch launches AI-driven audience builder",
                    "source": "Hightouch Blog",
                    "published_at": "2026-06-09",
                },
            ],
            "intent_score": 74,
            "icp_fit_score": 86,
        },
    },
    {
        "lead": {
            "first_name": "Sophia",
            "last_name": "Nguyen",
            "job_title": "VP of Revenue",
            "seniority_level": "VP",
            "linkedin_url": "https://linkedin.com/in/sophia-nguyen-demo",
            "phone": "+1-555-0278",
            "linkedin_signals": {
                "tenure_months": 8,
                "post_frequency": "weekly",
                "recent_post_topics": ["customer success", "B2B SaaS", "AI agents"],
                "is_active": True,
            },
        },
        "company": {
            "name": "Pylon",
            "domain": "usepylon.com",
            "industry": "Customer Success",
            "employee_count": 55,
            "location": "San Francisco, CA",
            "funding_stage": "Series A",
            "tech_stack": ["HubSpot", "Slack", "Linear", "Intercom"],
            "recent_news": [
                {
                    "headline": "Pylon raises $17M Series A to redefine B2B support",
                    "source": "TechCrunch",
                    "published_at": "2026-06-13",
                },
            ],
            "intent_score": 84,
            "icp_fit_score": 92,
        },
    },
    {
        "lead": {
            "first_name": "Lucas",
            "last_name": "Garcia",
            "job_title": "Senior Director of Sales",
            "seniority_level": "Director",
            "linkedin_url": "https://linkedin.com/in/lucas-garcia-demo",
            "phone": "+1-555-0299",
            "linkedin_signals": {
                "tenure_months": 25,
                "post_frequency": "biweekly",
                "recent_post_topics": ["data engineering", "modern data stack"],
                "is_active": True,
            },
        },
        "company": {
            "name": "dbt Labs",
            "domain": "getdbt.com",
            "industry": "Data Infrastructure",
            "employee_count": 450,
            "location": "Philadelphia, PA",
            "funding_stage": "Series D",
            "tech_stack": ["Salesforce", "Outreach", "Snowflake", "Looker"],
            "recent_news": [
                {
                    "headline": "dbt Labs unveils Mesh for distributed analytics teams",
                    "source": "dbt Blog",
                    "published_at": "2026-06-05",
                },
            ],
            "intent_score": 77,
            "icp_fit_score": 88,
        },
    },
    {
        "lead": {
            "first_name": "Maya",
            "last_name": "Krishnan",
            "job_title": "Head of Marketing",
            "seniority_level": "Director",
            "linkedin_url": "https://linkedin.com/in/maya-krishnan-demo",
            "phone": None,
            "linkedin_signals": {
                "tenure_months": 12,
                "post_frequency": "weekly",
                "recent_post_topics": ["ML deployment", "developer marketing"],
                "is_active": True,
            },
        },
        "company": {
            "name": "Replicate",
            "domain": "replicate.com",
            "industry": "Machine Learning",
            "employee_count": 65,
            "location": "San Francisco, CA",
            "funding_stage": "Series A",
            "tech_stack": ["GitHub", "Stripe", "Mixpanel", "Slack"],
            "recent_news": [
                {
                    "headline": "Replicate launches custom model fine-tuning UI",
                    "source": "Replicate Blog",
                    "published_at": "2026-06-08",
                },
            ],
            "intent_score": 69,
            "icp_fit_score": 81,
        },
    },
    {
        "lead": {
            "first_name": "Ethan",
            "last_name": "Roberts",
            "job_title": "VP of Sales",
            "seniority_level": "VP",
            "linkedin_url": "https://linkedin.com/in/ethan-roberts-demo",
            "phone": "+1-555-0312",
            "linkedin_signals": {
                "tenure_months": 24,
                "post_frequency": "weekly",
                "recent_post_topics": ["fintech", "spend management", "AI workflows"],
                "is_active": True,
            },
        },
        "company": {
            "name": "Ramp",
            "domain": "ramp.com",
            "industry": "FinTech",
            "employee_count": 500,
            "location": "New York, NY",
            "funding_stage": "Series D",
            "tech_stack": ["Salesforce", "Outreach", "Gong", "Looker"],
            "recent_news": [
                {
                    "headline": "Ramp launches AI-powered procurement assistant",
                    "source": "Forbes",
                    "published_at": "2026-06-12",
                },
                {
                    "headline": "Ramp expands enterprise team, hiring 20 AEs",
                    "source": "LinkedIn",
                    "published_at": "2026-06-15",
                },
            ],
            "intent_score": 86,
            "icp_fit_score": 93,
        },
    },
]


def email_for(lead: dict) -> str:
    """Construct a deterministic demo email from a lead's first/last name + company."""
    first = (lead["lead"]["first_name"] or "").lower()
    last = (lead["lead"]["last_name"] or "").lower().replace("'", "")
    domain = lead["company"]["domain"]
    return f"{first}.{last}@{domain}"
