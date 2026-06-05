"""Analytics response schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OverviewKPIs(BaseModel):
    total_active_leads: int
    total_active_leads_delta: int
    reply_rate_week: float
    reply_rate_delta: float
    emails_sent_today: int
    decisions_made_today: int


class WeeklyReplyRate(BaseModel):
    week_label: str
    week_start: datetime
    sent: int
    replied: int
    reply_rate: float


class FunnelMetrics(BaseModel):
    sent: int
    delivered: int
    opened: int
    clicked: int
    replied: int


class ChannelMetrics(BaseModel):
    channel: str
    sent: int
    engagement_rate: float


class ABTestResult(BaseModel):
    sequence_step: str
    variant_a_subject: str
    variant_b_subject: str
    variant_a_open_rate: float
    variant_b_open_rate: float
    variant_a_reply_rate: float
    variant_b_reply_rate: float
    winner: Optional[str] = None


class AgentDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    lead_id: UUID
    decision_type: str
    channel_selected: Optional[str] = None
    confidence_score: float
    reasoning_summary: str
    full_reasoning: Optional[dict] = None
    signals_observed: Optional[dict] = None
    lead_state_at_decision: Optional[str] = None
    was_approved: Optional[bool] = None
    approved_by: Optional[str] = None
    executed_at: Optional[datetime] = None
    created_at: datetime


class AgentPerformance(BaseModel):
    decision_breakdown: dict[str, int]
    avg_confidence: float
    avg_confidence_trend: list[dict]
    human_override_rate: float
    total_decisions: int
