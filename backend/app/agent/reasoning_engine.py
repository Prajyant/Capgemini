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

from app.config import settings
from app.llm import get_llm, extract_text

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

def _build_llm():
    return get_llm(temperature=0.3, max_tokens=2000)


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
        # Email is always the preferred channel for follow-ups
        if current_state not in ("converted", "closed"):
            actions.append("send_email")
        if profile.get("linkedin_url"):
            actions.append("send_linkedin_dm")
        # Only offer call if there's been prior engagement (not as first action)
        if (profile.get("phone") or profile.get("seniority_level") in ("C-Level", "VP")) \
                and signals.get("has_replied"):
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

DECISION PRIORITY FRAMEWORK (follow this order):
- If lead has OPTED OUT → close_sequence (mandatory)
- If lead replied with "interested" or "meeting_requested" intent → send_email (send a follow-up to confirm time/details, NOT suggest_call)
- If lead replied with "needs_more_info" intent → send_email (answer their question with value)
- If lead replied with "wrong_person" intent → send_email (thank them, politely ask for a referral or introduction to the right person)
- If lead replied with "not_now" → wait (respect their timing, follow up in the number of days they mentioned, or 30 days)
- If lead replied with "competitor" or "objection" → send_email (address the objection with differentiated value)
- If lead replied with "already_customer" → close_sequence (they're already a customer)
- If lead replied with "unsubscribe" → close_sequence
- If lead has opened multiple times but NOT replied → send_email (different angle) or send_linkedin_dm
- If lead is brand new with high intent signals → send_email (initial outreach)
- If no engagement after 2+ emails → escalate_to_human or suggest_call as last resort
- Only suggest_call AFTER at least one email exchange has occurred AND they've expressed interest in connecting

KEY PRINCIPLE: Email is always the preferred first response to a reply. Only choose WAIT when the lead explicitly asked to be contacted later ("not_now"). Never WAIT on a reply that needs an answer or action (wrong_person, needs_more_info, interested, objection) — those require a send_email response.

OUTPUT FORMAT (respond with valid JSON only, no markdown fences):
{
    "signal_analysis": "What signals did you observe and what do they mean?",
    "situation_assessment": "What is the overall situation with this lead right now?",
    "options_considered": ["option 1 with pros/cons", "option 2 with pros/cons", "option 3 with pros/cons"],
    "decision": "one of: send_email | send_linkedin_dm | suggest_call | wait | escalate_to_human | close_sequence",
    "confidence": 0.0 to 1.0,
    "reasoning_summary": "Plain English explanation for the SDR. Start with 'I chose to...' and explain why based on specific signals. 2-3 sentences max.",
    "next_wait_days": integer (0 if action is immediate),
    "email_personalisation_hooks": ["specific hook 1", "specific hook 2"]
}"""


def _heuristic_decision(profile: dict, signals: dict, history: list, state: "LeadAgentState") -> dict:
    """
    Rule-based fallback used when the LLM is unavailable (rate limit / error).
    Produces a sensible decision from the most recent reply intent and signals,
    so the agent never returns a dead-end 'system error' to the user.
    """
    first_name = profile.get("first_name") or "this lead"
    reply_intent = _last_reply_intent(history)
    has_replied = signals.get("has_replied")
    emails_sent = signals.get("emails_sent_count", 0)
    opens_7d = signals.get("email_opens_7d", 0)

    intent_map = {
        "interested": ("send_email", 0.85,
            f"{first_name} expressed interest, so I'm sending a follow-up email to confirm and propose next steps.", 0),
        "meeting_requested": ("send_email", 0.88,
            f"{first_name} asked to meet — I'm replying with concrete time options to lock it in.", 0),
        "needs_more_info": ("send_email", 0.82,
            f"{first_name} asked a question before committing. I'm sending an email that answers it directly with value.", 0),
        "competitor": ("send_email", 0.75,
            f"{first_name} uses a competing tool. This is an objection to address, not a dead end — I'm sending a differentiation email.", 0),
        "wrong_person": ("send_email", 0.78,
            f"{first_name} isn't the right contact. I'm sending a polite email asking for an introduction to the right person.", 0),
        "not_now": ("wait", 0.8,
            f"{first_name} asked to be contacted later, so I'm waiting and will follow up when the timing is right.", 30),
        "out_of_office": ("wait", 0.85,
            f"{first_name} is out of office. I'm waiting until they return before following up.", 7),
        "already_customer": ("close_sequence", 0.9,
            f"{first_name} is already our customer. Closing the sequence and handing off to account management.", 0),
        "unsubscribe": ("close_sequence", 1.0,
            f"{first_name} asked to be removed. Closing the sequence immediately to honor the opt-out.", 0),
    }

    if reply_intent in intent_map:
        decision, confidence, summary, wait_days = intent_map[reply_intent]
        hooks = ["reference their reply", "propose a clear next step"] if decision == "send_email" else []
        return {
            "signal_analysis": f"Most recent reply intent is '{reply_intent}'. This is the strongest signal and drives the next action.",
            "situation_assessment": f"{first_name} is actively engaged; the reply intent determines the optimal response.",
            "options_considered": [
                f"{decision} — directly addresses the reply",
                "wait — only if they asked for later timing",
                "escalate_to_human — reserved for genuinely ambiguous cases",
            ],
            "decision": decision,
            "confidence": confidence,
            "reasoning_summary": summary,
            "next_wait_days": wait_days,
            "email_personalisation_hooks": hooks,
        }

    if not has_replied:
        if emails_sent == 0:
            return {
                "signal_analysis": "Lead has not been contacted yet but matches our ICP.",
                "situation_assessment": "Fresh lead in a growth phase. Good time for a first touch.",
                "options_considered": ["send_email — initiate outreach", "wait — no reason to delay"],
                "decision": "send_email", "confidence": 0.75,
                "reasoning_summary": f"I'm sending an intro email to {first_name} — they fit our ICP and there's no prior contact yet.",
                "next_wait_days": 0,
                "email_personalisation_hooks": ["company context", "relevant pain point"],
            }
        if opens_7d > 0:
            return {
                "signal_analysis": f"{opens_7d} open(s) in the last 7 days, no reply yet.",
                "situation_assessment": "Lead is curious but hasn't committed. A gentle nudge may help.",
                "options_considered": ["send_email — re-engage", "wait — give them space", "send_linkedin_dm — softer channel"],
                "decision": "send_email", "confidence": 0.7,
                "reasoning_summary": f"{first_name} opened our email but hasn't replied. I'm sending a short follow-up from a new angle.",
                "next_wait_days": 3,
                "email_personalisation_hooks": ["new angle", "value reminder"],
            }
        if emails_sent >= 3:
            return {
                "signal_analysis": "3+ emails sent with no engagement.",
                "situation_assessment": "Diminishing returns. Time to pause or hand off.",
                "options_considered": ["wait — pause outreach", "escalate_to_human — manual review", "close_sequence"],
                "decision": "wait", "confidence": 0.65,
                "reasoning_summary": f"No engagement from {first_name} after several emails. I'm pausing outreach to avoid hurting sender reputation.",
                "next_wait_days": 7,
                "email_personalisation_hooks": [],
            }
        return {
            "signal_analysis": "Contacted, awaiting response.",
            "situation_assessment": "Reasonable to wait before the next touch.",
            "options_considered": ["wait — give them time", "send_email — follow up"],
            "decision": "wait", "confidence": 0.7,
            "reasoning_summary": f"I'm waiting to give {first_name} time to respond before the next follow-up.",
            "next_wait_days": 3,
            "email_personalisation_hooks": [],
        }

    return {
        "signal_analysis": "Lead replied but intent is ambiguous.",
        "situation_assessment": "A direct reply keeps the conversation going.",
        "options_considered": ["send_email — clarify and add value", "escalate_to_human"],
        "decision": "send_email", "confidence": 0.65,
        "reasoning_summary": f"{first_name} replied but their intent is unclear. I'm sending a friendly email to clarify and keep the conversation moving.",
        "next_wait_days": 2,
        "email_personalisation_hooks": ["clarify their needs"],
    }


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
        content = extract_text(content)
        # Strip code fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        reasoning_output = json.loads(content)
    except Exception as e:
        logger.warning("LLM reasoning failed (%s). Using heuristic fallback.", e)
        reasoning_output = _heuristic_decision(profile, signals, history, state)

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
