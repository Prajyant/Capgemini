"""Company ORM model."""
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employee_range: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    funding_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    annual_revenue: Mapped[str | None] = mapped_column(String(50), nullable=True)

    tech_stack: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    recent_news: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    intent_score: Mapped[int] = mapped_column(Integer, default=0)
    icp_fit_score: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    leads = relationship("Lead", back_populates="company", lazy="selectin")
