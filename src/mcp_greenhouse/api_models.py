"""Pydantic models for the Greenhouse Job Board API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GreenhouseBaseModel(BaseModel):
    """Base model with permissive parsing for Greenhouse responses."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Location(GreenhouseBaseModel):
    """Simple location object."""

    name: str | None = None


class MetadataItem(GreenhouseBaseModel):
    """Custom metadata field exposed by Greenhouse."""

    id: int | None = None
    name: str
    value_type: str | None = Field(default=None, alias="value_type")
    value: Any = None


class JobListMeta(GreenhouseBaseModel):
    """Metadata returned alongside job lists."""

    total: int | None = None


class EmbeddedJob(GreenhouseBaseModel):
    """Compact job shape embedded in department and office responses."""

    id: int
    title: str
    location: Location | None = None
    updated_at: str | None = None
    absolute_url: str | None = None
    language: str | None = None


class DepartmentRef(GreenhouseBaseModel):
    """Department reference included on jobs or department listings."""

    id: int
    name: str
    parent_id: int | None = None
    child_ids: list[int] = Field(default_factory=list)
    jobs: list[EmbeddedJob] = Field(default_factory=list)
    children: list[DepartmentRef] = Field(default_factory=list)


class OfficeRef(GreenhouseBaseModel):
    """Office reference included on jobs or office listings."""

    id: int
    name: str
    location: str | None = None
    departments: list[DepartmentRef] = Field(default_factory=list)
    parent_id: int | None = None
    child_ids: list[int] = Field(default_factory=list)
    children: list[OfficeRef] = Field(default_factory=list)


class JobFieldOption(GreenhouseBaseModel):
    """Selectable option for a job application field."""

    value: Any = None
    label: str | None = None
    free_form: bool | None = None
    id: int | None = None


class JobField(GreenhouseBaseModel):
    """Field definition inside a job question."""

    name: str
    type: str
    values: list[JobFieldOption] = Field(default_factory=list)


class JobQuestion(GreenhouseBaseModel):
    """Application question block."""

    required: bool | None = None
    label: str
    fields: list[JobField] = Field(default_factory=list)


class DemographicQuestion(GreenhouseBaseModel):
    """Demographic question returned when enabled."""

    id: int
    label: str
    required: bool | None = None
    type: str
    answer_options: list[JobFieldOption] = Field(default_factory=list)


class DemographicQuestions(GreenhouseBaseModel):
    """Demographic question group."""

    header: str | None = None
    description: str | None = None
    questions: list[DemographicQuestion] = Field(default_factory=list)


class DataComplianceRule(GreenhouseBaseModel):
    """Data compliance rule."""

    type: str
    requires_consent: bool | None = None
    requires_processing_consent: bool | None = None
    requires_retention_consent: bool | None = None
    retention_period: int | None = None


class PayInputRange(GreenhouseBaseModel):
    """Pay transparency data block."""

    min_cents: int | None = None
    max_cents: int | None = None
    currency_type: str | None = None
    title: str | None = None
    blurb: str | None = None


class JobSummary(GreenhouseBaseModel):
    """Core public job posting fields."""

    id: int
    internal_job_id: int | None = None
    title: str
    updated_at: str | None = None
    requisition_id: str | None = None
    location: Location | None = None
    absolute_url: str | None = None
    language: str | None = None
    metadata: Any = None
    content: str | None = None
    departments: list[DepartmentRef] = Field(default_factory=list)
    offices: list[OfficeRef] = Field(default_factory=list)


class JobDetail(JobSummary):
    """Full job detail response."""

    questions: list[JobQuestion] = Field(default_factory=list)
    location_questions: list[JobQuestion] = Field(default_factory=list)
    compliance: list[JobQuestion] = Field(default_factory=list)
    demographic_questions: DemographicQuestions | None = None
    data_compliance: list[DataComplianceRule] = Field(default_factory=list)
    pay_input_ranges: list[PayInputRange] = Field(default_factory=list)


class JobBoard(GreenhouseBaseModel):
    """Top-level job board metadata."""

    name: str
    content: str | None = None


class JobListResponse(GreenhouseBaseModel):
    """List jobs response wrapper."""

    jobs: list[JobSummary] = Field(default_factory=list)
    meta: JobListMeta = Field(default_factory=JobListMeta)


class DepartmentsResponse(GreenhouseBaseModel):
    """List departments response wrapper."""

    departments: list[DepartmentRef] = Field(default_factory=list)


class OfficesResponse(GreenhouseBaseModel):
    """List offices response wrapper."""

    offices: list[OfficeRef] = Field(default_factory=list)


class NormalizedJobPosting(GreenhouseBaseModel):
    """Stable normalized job schema for downstream storage."""

    job_id: int
    board_token: str
    internal_job_id: int | None = None
    title: str
    location: str | None = None
    url: str | None = None
    updated_timestamp: str | None = None
    description: str | None = None
    departments: list[str] = Field(default_factory=list)
    offices: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    has_salary_data: bool = False
    has_experience_level: bool = False
    has_workplace_type: bool = False
    salary_ranges: list[PayInputRange] = Field(default_factory=list)
    experience_level_values: list[str] = Field(default_factory=list)
    workplace_type_values: list[str] = Field(default_factory=list)


class JobAttributeReport(GreenhouseBaseModel):
    """Presence report for salary and related job attributes."""

    job_id: int
    board_token: str
    has_salary_data: bool
    has_experience_level: bool
    has_workplace_type: bool
    has_department_data: bool
    has_office_data: bool
    metadata_field_names: list[str] = Field(default_factory=list)
    experience_level_values: list[str] = Field(default_factory=list)
    workplace_type_values: list[str] = Field(default_factory=list)
    salary_range_count: int = 0
    notes: list[str] = Field(default_factory=list)


class PreviousJobSnapshot(GreenhouseBaseModel):
    """Minimal snapshot used for change detection across polls."""

    job_id: int
    updated_timestamp: str | None = None
    title: str | None = None
    url: str | None = None


class JobChangeSet(GreenhouseBaseModel):
    """Diff result for polling workflows."""

    board_token: str
    new_jobs: list[NormalizedJobPosting] = Field(default_factory=list)
    updated_jobs: list[NormalizedJobPosting] = Field(default_factory=list)
    unchanged_count: int = 0
    current_snapshot: list[PreviousJobSnapshot] = Field(default_factory=list)


DepartmentRef.model_rebuild()
OfficeRef.model_rebuild()
