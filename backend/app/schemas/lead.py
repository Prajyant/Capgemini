"""Lead Pydantic schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, ConfigDict, Field


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    employee_range: Optional[str] = None
    location: Optional[str] = None
    funding_stage: Optional[str] = None
    tech_stack: Optional[list] = None
    recent_news: Optional[list] = None
    intent_score: int = 0
    icp_fit_score: int = 0


class LeadCreate(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    seniority_level: Optional[str] = None
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    industry: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    source: str = "manual"


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    state: Optional[str] = None
    opted_out: Optional[bool] = None


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    seniority_level: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    enrichment_status: str
    enrichment_score: int = 0
    state: str
    state_updated_at: Optional[datetime] = None
    next_action_at: Optional[datetime] = None
    current_step: int = 0
    opted_out: bool = False
    created_at: datetime
    updated_at: datetime
    company: Optional[CompanyOut] = None
    linkedin_signals: Optional[dict] = None
    company_news: Optional[list] = None
    tech_stack: Optional[list] = None
    intent_signals: Optional[dict] = None


class LeadStateChange(BaseModel):
    state: str = Field(..., description="new|enriched|contacted|engaged|replied|converted|cold|unsubscribed|closed")
    reason: Optional[str] = None


class CSVImportResult(BaseModel):
    imported: int
    failed: int
    errors: list[dict] = []
    lead_ids: list[UUID] = []
