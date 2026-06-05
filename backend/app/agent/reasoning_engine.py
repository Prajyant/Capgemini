"""
The LangGraph reasoning agent.

This is what makes SalesAgent AI an agent, not just automation.
The chain-of-thought produced here is the single most important output
of the entire system — it's what gets shown to the SDR and to evaluators.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional, TypedDict

from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic

from app.config import settings

logger = logging.getLogger(__name__)


class LeadAgentState(TypedDict, total=False):
    lead_id: str
    lead_profile: dict
    engagement_history: list
    current_state: str
    behavioral_signals: dict
    available_actions: list
    reasoning: str
    decision: str
    confidence: float
    reasoning_summary: str
    next_wait_days: int
    personalisation_hooks: list
    full_reasoning: dict


# ---------- Signal observation helpers ----------

def _count_recent_opens(history: list, days: int = 7) -> int:
    cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
    return sum(
        1 for e in history
        if e.get("event_type") == "opened"
        and _ts(e.get("occurred_at")) > cutoff
    )


def _ts(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, datetime):
        return value.timestamp()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return 0.0


def _days_since_last_open(history: list) -> Optional[int]:
    opens = [e for e in history if e.get("event_type") == "opened"]
    if not opens:
        return None
    latest = max(_ts(e.get("occurred_at")) for e in opens)
    if latest == 0:
        return None
    return int((datetime.now(timezone.utc).timestamp() - latest) / 86400)


def _has_clicked(history: list) -> bool:
    return any(e.get("event_type") == "clicked" for e in history)


def _has_replied(history: list) -> bool:
    return any(e.get("event_type") == "replied" for e in history)


def _last_reply_sentiment(history: list) -> Optional[str]:
    replies = [e for e in history if e.get("event_type") == "replied"]
    if not replies:
        return None
    latest = max(replies, key=lambda e: _ts(e.get("occurred_at")))
    return latest.get("reply_sentiment")


def _last_reply_intent(history: list) -> Optional[str]:
    replies = [e for e in history if e.get("event_type") == "replied"]
    if not replies:
        return None
    latest = max(replies, key=lambda e: _ts(e.get("occurred_at")))
    return latest.get("reply_intent")


def _emails_sent(history: list) -> int:
    return sum(1 for e in history if e.get("event_type") == "sent")


def _days_in_state(profile: dict) -> int:
    state_updated = profile.get("state_updated_at")
    if not state_updated:
        return 0
    ts = _ts(state_updated)
    if ts == 0:
        return 0
    return int((datetime.now(timezone.utc).timestamp() - ts) / 86400)


def _format_history(history: list, limit: int = 10) -> str:
    if not history:
        return "No prior engagement."
    sorted_history = sorted(history, key=lambda e: _ts(e.get("occurred_at")), reverse=True)
    lines = []
    for e in sorted_history[:limit]:
        ts = e.get("occurred_at", "?")
        evt = e.get("event_type", "?")
        extra = ""
        if evt == "sent":
            extra = f" subject='{e.get('subject', '')}'"
        elif evt == "replied":
            extra = f" sentiment={e.get('reply_sentiment')} intent={e.get('reply_intent')} body='{(e.get('reply_content') or '')[:120]}'"
        elif evt == "clicked":
            extra = f" url={e.get('clicked_url', '')}"
        lines.append(f"  - [{ts}] {evt}{extra}")
    return "\n".join(lines)


# ---------- Graph nodes ----------

def _build_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=settings.CLAUDE_MODEL,
        max_tokens=2000,
        temperature=0.3,
        api_key=settings.ANTHROPIC_API_KEY,
    )


def observe_signals(state: LeadAgentState) -> LeadAgentState:
    """Step 1: Gather and structure all available signals."""
    history = state.get("engagement_history") or []
    profile = state.get("lead_profile") or {}

    signals = {
        "email_opens_7d": _count_recent_opens(history, days=7),
        "email_opens_total": sum(1 for e in history if e.get("event_type") == "opened"),
        "last_open_days_ago": _days_since_last_open(history),
        "has_clicked": _has_clicked(history),
        "has_replied": _has_replied(history),
        "reply_sentiment": _last_reply_sentiment(history),
        "reply_intent": _last_reply_intent(history),
        "emails_sent_count": _emails_sent(history),
        "days_in_current_state": _days_in_state(profile),
        "enrichment_score": profile.get("enrichment_score", 0),
        "icp_fit_score": profile.get("icp_fit_score", 0),
        "intent_score": profile.get("intent_score", 0),
        "has_funding_news": bool(_extract_funding_news(profile.get("company_news"))),
        "has_hiring_signal": bool((profile.get("intent_signals") or {}).get("hiring_count", 0)),
    }
    state["behavioral_signals"] = signals
    return state


def _extract_funding_news(news: Optional[list]) -> Optional[dict]:
    if not news:
        return None
    for item in news:
        headline = (item.get("headline") or "").lower()
        if any(k in headline for k in ["raised", "series", "funding", "round"]):
            return item
    return None


def assess_context(state: LeadAgentState) -> LeadAgentState:
    """Step 2: Determine which actions are valid given the current state."""
    actions: list[str] = []
    profile = state.get("lead_profile") or {}
    signals = state.get("behavioral_signals") or {}
    current_state = state.get("current_state", "new")

    if not profile.get("opted_out"):
        if signals.get("emails_sent_count", 0) < 3 and current_state not in ("converted", "closed"):
            actions.append("send_email")
        if profile.get("linkedin_url"):
            actions.append("send_linkedin_dm")
        if profile.get("phone") or profile.get("seniority_level") in ("C-Level", "VP"):
            actions.append("suggest_call")

    actions.append("wait")
    actions.append("escalate_to_human")
    actions.append("close_sequence")

    state["available_actions"] = actions
    return state


SYSTEM_PROMPT = """You are an expert B2B sales intelligence agent with deep expertise in outreach strategy.

Your job is to analyse a lead's profile and engagement signals, reason carefully about the situation, and decide the best next action.

CRITICAL RULES:
1. Always reason step by step before deciding
2. Sometimes the best action is to WAIT or do NOTHING — do not default to sending
3. Every decision must have a clear, specific reason tied to the signals you observed
4. Your reasoning_summary must be written in plain English that a non-technical SDR can understand
5. Be honest about uncertainty — if signals are mixed, say so
6. Reference specific signals (e.g., "opened twice in 24h", "Series A announced", "replied with objection")

OUTPUT FORMAT (respond with valid JSON only, no markdown fences):
{
    "signal_analysis": "What signals did you observe and what do they mean?",
    "situation_assessment": "What is the overall situation with this lead right now?",
    "options_considered": ["option 1 with pros/cons", "option 2 with pros/cons"],
    "decision": "one of: send_email | send_linkedin_dm | suggest_call | wait | escalate_to_human | close_sequence",
    "confidence": 0.0 to 1.0,
    "reasoning_summary": "Plain English explanation for the SDR. Start with 'I chose to...' and explain why based on specific signals. Keep under 50 words.",
    "next_wait_days": integer,
    "email_personalisation_hooks": ["specific hook 1", "specific hook 2"]
}"""


def reason_and_decide(state: LeadAgentState) -> LeadAgentState:
    """Step 3: THE CORE. Claude reasons about the situation and decides."""
    profile = state.get("lead_profile") or {}
    signals = state.get("behavioral_signals") or {}
    history = state.get("engagement_history") or []

    user_prompt = f"""LEAD PROFILE:
Name: {profile.get('first_name', '?')} {profile.get('last_name', '')}
Title: {profile.get('job_title', 'Unknown')}
Seniority: {profile.get('seniority_level', 'Unknown')}
Company: {profile.get('company_name', 'Unknown')}
Industry: {profile.get('industry', 'Unknown')}
Employee Range: {profile.get('employee_range', 'Unknown')}
ICP Fit Score: {profile.get('icp_fit_score', 0)}/100
Enrichment Score: {profile.get('enrichment_score', 0)}/100

ENRICHMENT SIGNALS:
Recent Company News: {json.dumps((profile.get('company_news') or [])[:2], default=str)}
Tech Stack: {json.dumps((profile.get('tech_stack') or [])[:5], default=str)}
Intent Signals: {json.dumps(profile.get('intent_signals') or {}, default=str)}
LinkedIn Signals: {json.dumps(profile.get('linkedin_signals') or {}, default=str)}

ENGAGEMENT HISTORY (most recent first):
{_format_history(history)}

BEHAVIOURAL SIGNALS:
{json.dumps(signals, indent=2, default=str)}

CURRENT LEAD STATE: {state.get('current_state', 'new')}
AVAILABLE ACTIONS: {state.get('available_actions', [])}

Reason carefully about this lead's situation, weigh the available actions, and decide the best next action. Remember: doing nothing is sometimes the right answer."""

    try:
        llm = _build_llm()
        response = llm.invoke([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])
        content = response.content
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        # Strip code fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        reasoning_output = json.loads(content)
    except Exception as e:
        logger.exception("Reasoning failed, falling back to escalation: %s", e)
        reasoning_output = {
            "signal_analysis": f"Reasoning engine error: {e}",
            "situation_assessment": "Unable to reason automatically.",
            "options_considered": [],
            "decision": "escalate_to_human",
            "confidence": 0.0,
            "reasoning_summary": "I could not reason about this lead due to a system error. Escalating to a human SDR for manual review.",
            "next_wait_days": 1,
            "email_personalisation_hooks": [],
        }

    state["full_reasoning"] = reasoning_output
    state["reasoning"] = json.dumps(reasoning_output)
    state["decision"] = reasoning_output.get("decision", "escalate_to_human")
    state["confidence"] = float(reasoning_output.get("confidence", 0.0))
    state["reasoning_summary"] = reasoning_output.get(
        "reasoning_summary",
        "No reasoning summary produced — escalating for human review."
    )
    state["next_wait_days"] = int(reasoning_output.get("next_wait_days", 3))
    state["personalisation_hooks"] = reasoning_output.get("email_personalisation_hooks", [])
    return state


def validate_decision(state: LeadAgentState) -> LeadAgentState:
    """Step 4: Compliance and sanity checks. Hard blocks override agent decisions."""
    profile = state.get("lead_profile") or {}

    # Hard block: opted out
    if profile.get("opted_out"):
        state["decision"] = "close_sequence"
        state["reasoning_summary"] = "Lead has opted out. Sequence closed automatically per CAN-SPAM compliance."
        state["confidence"] = 1.0
        return state

    # Hard block: confidence too low
    threshold = settings.CONFIDENCE_THRESHOLD
    if state.get("confidence", 0.0) < threshold and state.get("decision") != "escalate_to_human":
        original = state.get("decision")
        state["decision"] = "escalate_to_human"
        original_summary = state.get("reasoning_summary", "")
        state["reasoning_summary"] = (
            f"Confidence too low ({state.get('confidence', 0):.0%}) to act autonomously. "
            f"Original recommendation: {original}. Flagged for human review. "
            f"Context: {original_summary}"
        )

    # Validate decision is in allowed set
    allowed_decisions = {
        "send_email", "send_linkedin_dm", "suggest_call",
        "wait", "escalate_to_human", "close_sequence"
    }
    if state.get("decision") not in allowed_decisions:
        logger.warning("Invalid decision %s; coercing to escalate.", state.get("decision"))
        state["decision"] = "escalate_to_human"
        state["reasoning_summary"] = (
            "Agent produced an unrecognised action. Escalating to human for safety. "
            f"Original: {state.get('reasoning_summary', '')}"
        )

    return state


# ---------- Graph compilation ----------

_compiled_agent = None


def build_reasoning_agent():
    """Build and cache the LangGraph agent."""
    global _compiled_agent
    if _compiled_agent is not None:
        return _compiled_agent

    graph = StateGraph(LeadAgentState)
    graph.add_node("observe_signals", observe_signals)
    graph.add_node("assess_context", assess_context)
    graph.add_node("reason_and_decide", reason_and_decide)
    graph.add_node("validate_decision", validate_decision)

    graph.set_entry_point("observe_signals")
    graph.add_edge("observe_signals", "assess_context")
    graph.add_edge("assess_context", "reason_and_decide")
    graph.add_edge("reason_and_decide", "validate_decision")
    graph.add_edge("validate_decision", END)

    _compiled_agent = graph.compile()
    return _compiled_agent


def run_reasoning(
    lead_id: str,
    lead_profile: dict,
    engagement_history: list,
    current_state: str,
) -> LeadAgentState:
    """Run the full reasoning graph for one lead. Returns the final state."""
    agent = build_reasoning_agent()
    initial_state: LeadAgentState = {
        "lead_id": str(lead_id),
        "lead_profile": lead_profile,
        "engagement_history": engagement_history,
        "current_state": current_state,
    }
    result = agent.invoke(initial_state)
    return result
