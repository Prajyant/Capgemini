"""
Tests for the reasoning engine. These run without hitting the LLM by stubbing
the Anthropic call.
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

from app.agent.reasoning_engine import (
    observe_signals, assess_context, validate_decision,
    _count_recent_opens, _has_replied,
)


def test_observe_signals_extracts_engagement():
    history = [
        {"event_type": "sent", "occurred_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()},
        {"event_type": "opened", "occurred_at": (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()},
        {"event_type": "opened", "occurred_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()},
    ]
    state = {
        "engagement_history": history,
        "lead_profile": {"enrichment_score": 75, "icp_fit_score": 80},
    }
    result = observe_signals(state)
    assert result["behavioral_signals"]["email_opens_7d"] == 2
    assert result["behavioral_signals"]["emails_sent_count"] == 1
    assert result["behavioral_signals"]["has_replied"] is False


def test_assess_context_email_always_available_for_active_leads():
    """
    The reasoning engine no longer enforces a per-lead email cap inside
    assess_context — it just lists which channels are valid. The LLM (and
    the human approver) decide whether sending another email is wise.
    """
    state = {
        "lead_profile": {"opted_out": False, "linkedin_url": "https://linkedin.com/x"},
        "behavioral_signals": {"emails_sent_count": 3},
        "current_state": "engaged",
    }
    result = assess_context(state)
    assert "send_email" in result["available_actions"]
    assert "send_linkedin_dm" in result["available_actions"]
    assert "wait" in result["available_actions"]
    assert "close_sequence" in result["available_actions"]


def test_assess_context_blocks_email_for_closed_or_optedout():
    closed = {
        "lead_profile": {"opted_out": False},
        "behavioral_signals": {},
        "current_state": "closed",
    }
    assert "send_email" not in assess_context(closed)["available_actions"]

    opted_out = {
        "lead_profile": {"opted_out": True, "linkedin_url": "https://linkedin.com/x"},
        "behavioral_signals": {},
        "current_state": "engaged",
    }
    actions = assess_context(opted_out)["available_actions"]
    assert "send_email" not in actions
    assert "send_linkedin_dm" not in actions
    assert "close_sequence" in actions


def test_validate_blocks_opted_out():
    state = {
        "lead_profile": {"opted_out": True},
        "decision": "send_email",
        "confidence": 0.9,
        "reasoning_summary": "Original reasoning",
    }
    result = validate_decision(state)
    assert result["decision"] == "close_sequence"
    assert "opted out" in result["reasoning_summary"].lower()


def test_validate_escalates_low_confidence():
    state = {
        "lead_profile": {"opted_out": False},
        "decision": "send_email",
        "confidence": 0.4,
        "reasoning_summary": "Wanted to send email",
    }
    result = validate_decision(state)
    assert result["decision"] == "escalate_to_human"
    assert "confidence too low" in result["reasoning_summary"].lower()


def test_count_recent_opens():
    history = [
        {"event_type": "opened", "occurred_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()},
        {"event_type": "opened", "occurred_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()},
        {"event_type": "sent", "occurred_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()},
    ]
    assert _count_recent_opens(history, days=7) == 1


def test_has_replied():
    assert _has_replied([{"event_type": "replied"}]) is True
    assert _has_replied([{"event_type": "opened"}]) is False
