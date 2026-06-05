"""
Chain-of-thought formatter — converts raw reasoning JSON into display-ready structures.
"""
from typing import Optional


def format_for_display(full_reasoning: Optional[dict]) -> dict:
    """
    Take the raw LLM reasoning JSON and produce a display-ready structure
    for the AgentReasoningPanel and Agent Feed page.
    """
    if not full_reasoning:
        return {
            "signal_analysis": "No detailed reasoning available.",
            "situation_assessment": "",
            "options_considered": [],
            "decision": "unknown",
            "confidence": 0.0,
            "summary": "No reasoning summary available.",
        }
    return {
        "signal_analysis": full_reasoning.get("signal_analysis", ""),
        "situation_assessment": full_reasoning.get("situation_assessment", ""),
        "options_considered": full_reasoning.get("options_considered", []),
        "decision": full_reasoning.get("decision", "unknown"),
        "confidence": float(full_reasoning.get("confidence", 0.0)),
        "summary": full_reasoning.get("reasoning_summary", ""),
        "next_wait_days": full_reasoning.get("next_wait_days"),
        "personalisation_hooks": full_reasoning.get("email_personalisation_hooks", []),
    }


def confidence_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.65:
        return "medium"
    return "low"
