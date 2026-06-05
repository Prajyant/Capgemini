# SalesAgent AI

### Autonomous Agentic Sales Intelligence | Capgemini AgentifAI Buildathon 2026

## What This Is

SalesAgent AI is not a sequence automation tool. It is a reasoning agent that enriches leads, decides the best next action, explains every decision in plain English, and gets smarter every week.

The core differentiator: every agent decision answers three questions in plain English, before any action is taken:

- What signals did I observe?
- What did I consider?
- Why did I choose this action and not another?

That transparency is the product. Competitors automate volume. SalesAgent AI automates judgement.

## Architecture

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 14 (App Router) + Tailwind + Recharts |
| Backend | FastAPI (async Python 3.11) |
| Agent | LangGraph + LangChain + Claude Sonnet 4 |
| Database | PostgreSQL 15 (async via SQLAlchemy) |
| Cache / Pub-sub | Redis 7 |
| Background jobs | Celery + Redis broker + Celery Beat |
| Email | SendGrid |
| Containerisation | Docker Compose |

## Quick Start

```bash
git clone <this-repo>
cp .env.example .env       # add your ANTHROPIC_API_KEY at minimum
docker-compose up --build  # everything starts
```

Once containers are running:

```bash
# Seed demo data (5 leads with full reasoning history, rising reply-rate trend)
docker-compose exec backend python seed.py
```

Open:

- Dashboard: http://localhost:3000
- API docs: http://localhost:8000/docs

## Demo Walkthrough

1. Open http://localhost:3000 — the dashboard shows 5 demo leads in the pipeline
2. Each lead card shows the latest agent decision in plain English
3. Click any lead → see the full chain of thought (signal analysis → options → decision)
4. Open Analytics → see reply rate climbing 3.2% → 11.7% over 4 weeks
5. Open Agent Feed → full audit log of every reasoning step
6. Open Import → upload `backend/demo-leads.csv` and watch enrichment happen

### What evaluators see in 60 seconds

- A live dashboard showing leads in a pipeline with agent decisions
- Plain-English reasoning summaries on every card and in the live feed
- Analytics chart proving the reply rate improves week over week
- One lead detail page showing the complete chain of thought

## The Reasoning Engine

The single most important file is `backend/app/agent/reasoning_engine.py`.

The graph: `observe_signals → assess_context → reason_and_decide → validate_decision`

The single most important line:

```python
state["reasoning_summary"] = reasoning_output["reasoning_summary"]
```

Every agent decision produces a plain-English explanation. It is never empty. It is always shown on screen. That is what makes this an agent and not automation.

## Compliance

- Every email passes a spam-score check before send (threshold 3.0)
- Unsubscribe footer auto-injected per CAN-SPAM
- One-click unsubscribe at `/unsubscribe/{lead_id}`
- Hard block on opted-out leads regardless of agent decision
- Decisions with confidence < 0.65 are escalated to human review by default

## Project Structure

```
salesagent-ai/
├── backend/
│   ├── app/
│   │   ├── agent/         # LangGraph reasoning engine
│   │   ├── enrichment/    # Multi-source enrichment with graceful degradation
│   │   ├── outreach/      # Email generation, sending, A/B testing
│   │   ├── nlp/           # Reply intent classification
│   │   ├── tasks/         # Celery background workers
│   │   ├── api/           # FastAPI route handlers
│   │   └── models/        # SQLAlchemy ORM
│   └── seed.py            # Demo data
└── frontend/
    ├── app/               # Next.js 14 App Router pages
    └── components/        # React components
```

## Team MultiBots

- Taranpreet Kaur — AI Architecture
- Prajyant Veer Siag — Backend & Pipeline
- Kashish Sood — LLM & Prompt Engineering
- Sparsh Nautiyal — Frontend & UX
- Vibhor Jindal — Business Strategy & QA

## Use Case

Capgemini AgentifAI Buildathon 2026 · Use Case #27 · B2B Sales Outreach Intelligence
