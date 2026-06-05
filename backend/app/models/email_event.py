"""Email event tracking model."""
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class EmailEvent(Base):
    __tablename__ = "email_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True
    )

    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), default="email")

    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    ab_variant: Mapped[str | None] = mapped_column(String(1), nullable=True)

    opened_count: Mapped[int] = mapped_column(Integer, default=0)
    clicked_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    reply_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reply_intent: Mapped[str | None] = mapped_column(String(30), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    lead = relationship("Lead", back_populates="email_events")
