"""Pydantic request/response models, one set per ``ordinoxai`` table.

Conventions:

* ``*Create`` — fields accepted on POST; required fields mirror NOT NULL
  columns without a default.
* ``*Update`` — every field optional; only those explicitly sent are written
  (PATCH semantics).
* ``*Read`` — response shape. Fields are optional with ``None`` defaults so a
  response never fails to serialize if a column is null.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field

# Lightweight email validation without the external `email-validator` package
# (which Pydantic's EmailStr requires). Good enough to reject obvious garbage;
# real deliverability is verified out-of-band.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str) -> str:
    if not _EMAIL_RE.match(value):
        raise ValueError("invalid email address")
    return value


Email = Annotated[str, AfterValidator(_validate_email)]


class _Read(BaseModel):
    """Common read fields. Subclasses add table-specific columns."""

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


# --------------------------------------------------------------------------- #
# Companies
# --------------------------------------------------------------------------- #
class CompanyCreate(BaseModel):
    name: str = Field(min_length=1)
    website: str | None = None
    industry: str | None = None
    country: str | None = None
    status: str = "active"


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    website: str | None = None
    industry: str | None = None
    country: str | None = None
    status: str | None = None


class CompanyRead(_Read):
    name: str | None = None
    website: str | None = None
    industry: str | None = None
    country: str | None = None
    status: str | None = None


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
class UserCreate(BaseModel):
    email: Email
    company_id: UUID | None = None
    full_name: str | None = None
    role: str = "user"
    status: str = "active"


class UserUpdate(BaseModel):
    email: Email | None = None
    company_id: UUID | None = None
    full_name: str | None = None
    role: str | None = None
    status: str | None = None


class UserRead(_Read):
    email: str | None = None
    company_id: UUID | None = None
    full_name: str | None = None
    role: str | None = None
    status: str | None = None


# --------------------------------------------------------------------------- #
# Jobs
# --------------------------------------------------------------------------- #
class JobCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    company_id: UUID | None = None
    created_by: UUID | None = None
    department: str | None = None
    location: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    requirements: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str = "GBP"
    status: str = "draft"


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    company_id: UUID | None = None
    created_by: UUID | None = None
    department: str | None = None
    location: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    requirements: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    status: str | None = None


class JobRead(_Read):
    company_id: UUID | None = None
    created_by: UUID | None = None
    title: str | None = None
    department: str | None = None
    location: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    description: str | None = None
    requirements: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    status: str | None = None


# --------------------------------------------------------------------------- #
# Candidates
# --------------------------------------------------------------------------- #
class CandidateCreate(BaseModel):
    full_name: str = Field(min_length=1)
    email: Email | None = None
    phone: str | None = None
    country: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    source: str | None = None
    status: str = "new"


class CandidateUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1)
    email: Email | None = None
    phone: str | None = None
    country: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    source: str | None = None
    status: str | None = None


class CandidateRead(_Read):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    country: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    source: str | None = None
    status: str | None = None


# --------------------------------------------------------------------------- #
# Applications
# --------------------------------------------------------------------------- #
class ApplicationCreate(BaseModel):
    job_id: UUID
    candidate_id: UUID
    status: str = "submitted"
    stage: str = "screening"
    cv_file_url: str | None = None
    cover_letter: str | None = None


class ApplicationUpdate(BaseModel):
    status: str | None = None
    stage: str | None = None
    cv_file_url: str | None = None
    cover_letter: str | None = None
    ai_score: float | None = None
    ai_summary: str | None = None
    ai_risk_flags: list[str] | None = None
    ai_recommendation: str | None = None


class ApplicationRead(_Read):
    job_id: UUID | None = None
    candidate_id: UUID | None = None
    status: str | None = None
    stage: str | None = None
    cv_file_url: str | None = None
    cover_letter: str | None = None
    ai_score: float | None = None
    ai_summary: str | None = None
    ai_risk_flags: list[str] = Field(default_factory=list)
    ai_recommendation: str | None = None
    submitted_at: datetime | None = None


# --------------------------------------------------------------------------- #
# Interviews
# --------------------------------------------------------------------------- #
class InterviewCreate(BaseModel):
    application_id: UUID
    scheduled_at: datetime | None = None
    duration_minutes: int = 60
    location: str | None = None
    meeting_url: str | None = None
    interviewer_name: str | None = None
    interviewer_email: Email | None = None
    status: str = "scheduled"
    notes: str | None = None
    feedback: dict = Field(default_factory=dict)


class InterviewUpdate(BaseModel):
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    location: str | None = None
    meeting_url: str | None = None
    interviewer_name: str | None = None
    interviewer_email: Email | None = None
    status: str | None = None
    notes: str | None = None
    feedback: dict | None = None


class InterviewRead(_Read):
    application_id: UUID | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    location: str | None = None
    meeting_url: str | None = None
    interviewer_name: str | None = None
    interviewer_email: str | None = None
    status: str | None = None
    notes: str | None = None
    feedback: dict = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Waitlist
# --------------------------------------------------------------------------- #
class WaitlistCreate(BaseModel):
    email: Email
    full_name: str | None = None
    company_name: str | None = None
    country: str | None = None
    role: str | None = None
    notes: str | None = None
    status: str = "new"


class WaitlistUpdate(BaseModel):
    full_name: str | None = None
    company_name: str | None = None
    country: str | None = None
    role: str | None = None
    notes: str | None = None
    status: str | None = None


class WaitlistRead(_Read):
    email: str | None = None
    full_name: str | None = None
    company_name: str | None = None
    country: str | None = None
    role: str | None = None
    notes: str | None = None
    status: str | None = None


# --------------------------------------------------------------------------- #
# AI scoring
# --------------------------------------------------------------------------- #
class ScoreResult(BaseModel):
    """Structured output of the candidate scorer."""

    score: float = Field(ge=0, le=100)
    summary: str
    risk_flags: list[str] = Field(default_factory=list)
    recommendation: str  # advance | hold | reject
    method: str = "heuristic"  # heuristic | llm
