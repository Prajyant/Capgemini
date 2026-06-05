"""A/B test and prompt strategy models."""
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ABTest(Base):
    __tablename__ = "ab_tests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False
    )
    sequence_step_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sequence_steps.id"), nullable=True
    )

    variant_a_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    variant_a_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    variant_b_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    variant_b_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    variant_a_opens: Mapped[int] = mapped_column(Integer, default=0)
    variant_a_replies: Mapped[int] = mapped_column(Integer, default=0)
    variant_b_opens: Mapped[int] = mapped_column(Integer, default=0)
    variant_b_replies: Mapped[int] = mapped_column(Integer, default=0)

    winner: Mapped[str | None] = mapped_column(String(1), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observation_window_hours: Mapped[int] = mapped_column(Integer, default=48)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PromptStrategy(Base):
    __tablename__ = "prompt_strategies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vertical: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seniority_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hook_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    subject_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)

    avg_reply_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
