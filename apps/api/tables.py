"""Table registry: the single source of truth for which columns the API may
write and filter on per ``ordinoxai`` table.

Dynamic SQL in :mod:`apps.api.db` only ever interpolates identifiers drawn
from this registry, never user input — that is what keeps the generic CRUD
layer safe from SQL injection. Values are always passed as bound parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Columns every table manages itself; never written by the API.
MANAGED = ("id", "created_at", "updated_at")

# Whitelisted columns usable in ORDER BY, on top of each spec's writable set.
ORDERABLE_COMMON = ("created_at", "updated_at")


@dataclass(frozen=True)
class TableSpec:
    name: str
    writable: tuple[str, ...]
    jsonb: tuple[str, ...] = ()
    filterable: tuple[str, ...] = ()
    default_order: str = "created_at"
    extra_orderable: tuple[str, ...] = field(default_factory=tuple)

    def orderable(self) -> set[str]:
        return set(ORDERABLE_COMMON) | set(self.writable) | set(self.extra_orderable)


TABLES: dict[str, TableSpec] = {
    "companies": TableSpec(
        name="companies",
        writable=("name", "website", "industry", "country", "status"),
        filterable=("status", "country"),
        default_order="name",
        extra_orderable=("name",),
    ),
    "users": TableSpec(
        name="users",
        writable=("company_id", "email", "full_name", "role", "status"),
        filterable=("company_id", "role", "status", "email"),
    ),
    "jobs": TableSpec(
        name="jobs",
        writable=(
            "company_id",
            "created_by",
            "title",
            "department",
            "location",
            "employment_type",
            "seniority",
            "description",
            "requirements",
            "salary_min",
            "salary_max",
            "currency",
            "status",
        ),
        filterable=("company_id", "status", "department", "seniority", "employment_type"),
    ),
    "candidates": TableSpec(
        name="candidates",
        writable=(
            "full_name",
            "email",
            "phone",
            "country",
            "linkedin_url",
            "portfolio_url",
            "source",
            "status",
        ),
        filterable=("status", "country", "source", "email"),
    ),
    "applications": TableSpec(
        name="applications",
        writable=(
            "job_id",
            "candidate_id",
            "status",
            "stage",
            "cv_file_url",
            "cover_letter",
            "ai_score",
            "ai_summary",
            "ai_risk_flags",
            "ai_recommendation",
        ),
        jsonb=("ai_risk_flags",),
        filterable=("job_id", "candidate_id", "status", "stage"),
        extra_orderable=("ai_score", "submitted_at"),
    ),
    "interviews": TableSpec(
        name="interviews",
        writable=(
            "application_id",
            "scheduled_at",
            "duration_minutes",
            "location",
            "meeting_url",
            "interviewer_name",
            "interviewer_email",
            "status",
            "notes",
            "feedback",
        ),
        jsonb=("feedback",),
        filterable=("application_id", "status"),
        extra_orderable=("scheduled_at",),
    ),
    "waitlist_users": TableSpec(
        name="waitlist_users",
        writable=(
            "email",
            "full_name",
            "company_name",
            "country",
            "role",
            "notes",
            "status",
            "ip_address",
            "user_agent",
        ),
        filterable=("status", "country"),
    ),
}
