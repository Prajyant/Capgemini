"""Sequence Pydantic schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SequenceStepIn(BaseModel):
    step_number: int
    channel: str = "email"
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    wait_days: int = 3


class SequenceStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    step_number: int
    channel: str
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    wait_days: int


class SequenceCreate(BaseModel):
    name: str
    vertical: Optional[str] = None
    total_steps: int = 3
    steps: list[SequenceStepIn] = []


class SequenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    vertical: Optional[str] = None
    total_steps: int
    is_active: bool
    created_at: datetime
    steps: list[SequenceStepOut] = []


class GeneratedEmail(BaseModel):
    subject: str
    body: str
    personalisation_used: Optional[str] = None
    spam_score: float = 0.0
    passes_spam_check: bool = True
    ab_variant: str = "A"


class SequenceEmailsOut(BaseModel):
    sequence_id: UUID
    lead_id: UUID
    emails: list[GeneratedEmail]
