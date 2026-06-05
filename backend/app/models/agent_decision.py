"""
Agent decision model — the core of the product.

Every reasoning_summary stored here is what makes this an agent, not automation.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True
    )

    # The decision
    decision_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    channel_selected: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0)

    # The chain of thought — THE PRODUCT
    reasoning_summary: Mapped[str] = mapped_column(Text, nullable=False)
    full_reasoning: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Context
    signals_observed: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    lead_state_at_decision: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Execution
    was_approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    lead = relationship("Lead", back_populates="agent_decisions")
