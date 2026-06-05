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


def test_assess_context_excludes_email_when_3_sent():
    state = {
        "lead_profile": {"opted_out": False, "linkedin_url": "https://linkedin.com/x"},
        "behavioral_signals": {"emails_sent_count": 3},
        "current_state": "engaged",
    }
    result = assess_context(state)
    assert "send_email" not in result["available_actions"]
    assert "send_linkedin_dm" in result["available_actions"]
    assert "wait" in result["available_actions"]


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
