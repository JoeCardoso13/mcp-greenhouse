"""Greenhouse MCP Server - public Job Board API integration."""

from __future__ import annotations

import logging
import sys
from importlib.resources import files
from typing import Any, Literal

from fastmcp import Context, FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_greenhouse.api_client import GreenhouseAPIError, GreenhouseClient
from mcp_greenhouse.api_models import (
    DepartmentsResponse,
    JobAttributeReport,
    JobBoard,
    JobChangeSet,
    JobDetail,
    JobListResponse,
    JobSummary,
    NormalizedJobPosting,
    OfficesResponse,
    PreviousJobSnapshot,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp_greenhouse")

SKILL_CONTENT = files("mcp_greenhouse").joinpath("SKILL.md").read_text()

mcp = FastMCP(
    "Greenhouse",
    instructions=(
        "Read the skill resource at skill://greenhouse/usage before using tools. "
        "Always ask for a board token if the user has not provided one."
    ),
)

_client: GreenhouseClient | None = None

EXPERIENCE_KEYWORDS = ("experience", "seniority", "level", "career level", "role level")
WORKPLACE_KEYWORDS = ("remote", "hybrid", "onsite", "on-site", "in-office", "workplace")
SALARY_KEYWORDS = ("salary", "compensation", "pay", "ote", "base")


@mcp.resource("skill://greenhouse/usage")
def skill_usage() -> str:
    """Tool selection guide and workflow patterns for Greenhouse."""
    return SKILL_CONTENT


def get_client(_: Context | None = None) -> GreenhouseClient:
    """Get or create the API client instance."""
    global _client
    if _client is None:
        _client = GreenhouseClient()
    return _client


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring."""
    return JSONResponse({"status": "healthy", "service": "mcp-greenhouse"})


def _metadata_map(metadata: Any) -> dict[str, Any]:
    """Normalize Greenhouse metadata into a simple name -> value mapping."""
    if metadata is None:
        return {}
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, list):
        mapped: dict[str, Any] = {}
        for item in metadata:
            if isinstance(item, dict) and item.get("name"):
                mapped[str(item["name"])] = item.get("value")
        return mapped
    return {}


def _matching_metadata_values(metadata: dict[str, Any], keywords: tuple[str, ...]) -> list[str]:
    """Return metadata values whose keys match a keyword set."""
    values: list[str] = []
    for key, value in metadata.items():
        key_lower = key.lower()
        if any(keyword in key_lower for keyword in keywords) and value not in (None, ""):
            values.append(str(value))
    return values


def _content_matches(content: str | None, patterns: tuple[str, ...]) -> list[str]:
    """Extract loose text matches from job descriptions."""
    if not content:
        return []
    content_lower = content.lower()
    return [pattern for pattern in patterns if pattern in content_lower]


def _dedupe_strings(values: list[str]) -> list[str]:
    """Deduplicate while preserving order."""
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped


def _to_normalized_job(board_token: str, job: JobSummary | JobDetail) -> NormalizedJobPosting:
    """Convert a Greenhouse job object into the normalized storage schema."""
    metadata = _metadata_map(job.metadata)
    pay_ranges = list(getattr(job, "pay_input_ranges", []) or [])
    experience_values = _matching_metadata_values(metadata, EXPERIENCE_KEYWORDS)
    experience_values.extend(
        _content_matches(
            job.content, ("junior", "mid", "senior", "staff", "principal", "lead", "intern")
        )
    )
    workplace_values = _matching_metadata_values(metadata, WORKPLACE_KEYWORDS)
    workplace_values.extend(
        _content_matches(job.content, ("remote", "hybrid", "on-site", "onsite", "in-office"))
    )

    return NormalizedJobPosting(
        job_id=job.id,
        board_token=board_token,
        internal_job_id=job.internal_job_id,
        title=job.title,
        location=job.location.name if job.location else None,
        url=job.absolute_url,
        updated_timestamp=job.updated_at,
        description=job.content,
        departments=[department.name for department in job.departments],
        offices=[office.name for office in job.offices],
        metadata=metadata,
        has_salary_data=bool(pay_ranges)
        or bool(_matching_metadata_values(metadata, SALARY_KEYWORDS)),
        has_experience_level=bool(experience_values),
        has_workplace_type=bool(workplace_values),
        salary_ranges=pay_ranges,
        experience_level_values=_dedupe_strings(experience_values),
        workplace_type_values=_dedupe_strings(workplace_values),
    )


def _to_previous_snapshot(job: NormalizedJobPosting) -> PreviousJobSnapshot:
    """Reduce normalized jobs to a polling snapshot."""
    return PreviousJobSnapshot(
        job_id=job.job_id,
        updated_timestamp=job.updated_timestamp,
        title=job.title,
        url=job.url,
    )


def _snapshot_from_input(item: dict[str, Any]) -> PreviousJobSnapshot:
    """Parse arbitrary tool input into a typed previous snapshot."""
    payload = dict(item)
    if "id" in payload and "job_id" not in payload:
        payload["job_id"] = payload["id"]
    if "updated_at" in payload and "updated_timestamp" not in payload:
        payload["updated_timestamp"] = payload["updated_at"]
    return PreviousJobSnapshot.model_validate(payload)


def _change_detected(previous: PreviousJobSnapshot, current: PreviousJobSnapshot) -> bool:
    """Compare previous and current snapshots for meaningful changes."""
    return any(
        (
            previous.updated_timestamp != current.updated_timestamp,
            previous.title != current.title,
            previous.url != current.url,
        )
    )


@mcp.tool()
async def get_job_board(
    board_token: str,
    ctx: Context | None = None,
) -> JobBoard:
    """Fetch the board-level name and intro content for a Greenhouse board token."""
    client = get_client(ctx)
    try:
        return await client.get_job_board(board_token)
    except GreenhouseAPIError as exc:
        if ctx:
            await ctx.error(f"Greenhouse API error: {exc.message}")
        raise


@mcp.tool()
async def list_company_jobs(
    board_token: str,
    include_content: bool = False,
    ctx: Context | None = None,
) -> JobListResponse:
    """List current public job postings for a target company board."""
    client = get_client(ctx)
    try:
        return await client.list_jobs(board_token, include_content=include_content)
    except GreenhouseAPIError as exc:
        if ctx:
            await ctx.error(f"Greenhouse API error: {exc.message}")
        raise


@mcp.tool()
async def get_job_details(
    board_token: str,
    job_id: int,
    include_questions: bool = False,
    include_pay_transparency: bool = True,
    ctx: Context | None = None,
) -> JobDetail:
    """Fetch a single Greenhouse job with optional question and pay detail."""
    client = get_client(ctx)
    try:
        return await client.get_job(
            board_token,
            job_id,
            questions=include_questions,
            pay_transparency=include_pay_transparency,
        )
    except GreenhouseAPIError as exc:
        if ctx:
            await ctx.error(f"Greenhouse API error: {exc.message}")
        raise


@mcp.tool()
async def list_departments(
    board_token: str,
    render_as: Literal["list", "tree"] = "list",
    ctx: Context | None = None,
) -> DepartmentsResponse:
    """List departments and their public jobs for a Greenhouse board."""
    client = get_client(ctx)
    try:
        return await client.list_departments(board_token, render_as=render_as)
    except GreenhouseAPIError as exc:
        if ctx:
            await ctx.error(f"Greenhouse API error: {exc.message}")
        raise


@mcp.tool()
async def list_offices(
    board_token: str,
    render_as: Literal["list", "tree"] = "list",
    ctx: Context | None = None,
) -> OfficesResponse:
    """List offices and their department/job groupings for a Greenhouse board."""
    client = get_client(ctx)
    try:
        return await client.list_offices(board_token, render_as=render_as)
    except GreenhouseAPIError as exc:
        if ctx:
            await ctx.error(f"Greenhouse API error: {exc.message}")
        raise


@mcp.tool()
async def normalize_job_data(
    board_token: str,
    include_content: bool = True,
    ctx: Context | None = None,
) -> list[NormalizedJobPosting]:
    """Fetch current jobs and map them into a stable normalized schema."""
    client = get_client(ctx)
    try:
        jobs = await client.list_jobs(board_token, include_content=include_content)
        return [_to_normalized_job(board_token, job) for job in jobs.jobs]
    except GreenhouseAPIError as exc:
        if ctx:
            await ctx.error(f"Greenhouse API error: {exc.message}")
        raise


@mcp.tool()
async def inspect_job_attributes(
    board_token: str,
    job_id: int,
    ctx: Context | None = None,
) -> JobAttributeReport:
    """Report whether salary, experience level, and workplace signals are present."""
    client = get_client(ctx)
    try:
        job = await client.get_job(board_token, job_id, questions=False, pay_transparency=True)
    except GreenhouseAPIError as exc:
        if ctx:
            await ctx.error(f"Greenhouse API error: {exc.message}")
        raise

    normalized = _to_normalized_job(board_token, job)
    notes: list[str] = []
    if not normalized.has_salary_data:
        notes.append("No pay ranges or salary-like metadata were found.")
    if not normalized.has_experience_level:
        notes.append("No obvious experience-level metadata or description keywords were found.")
    if not normalized.has_workplace_type:
        notes.append("No obvious remote, hybrid, or on-site signal was found.")

    return JobAttributeReport(
        job_id=job.id,
        board_token=board_token,
        has_salary_data=normalized.has_salary_data,
        has_experience_level=normalized.has_experience_level,
        has_workplace_type=normalized.has_workplace_type,
        has_department_data=bool(job.departments),
        has_office_data=bool(job.offices),
        metadata_field_names=sorted(normalized.metadata.keys()),
        experience_level_values=normalized.experience_level_values,
        workplace_type_values=normalized.workplace_type_values,
        salary_range_count=len(normalized.salary_ranges),
        notes=notes,
    )


@mcp.tool()
async def list_new_or_updated_jobs(
    board_token: str,
    previous_snapshot: list[dict[str, Any]] | None = None,
    include_content: bool = True,
    ctx: Context | None = None,
) -> JobChangeSet:
    """Compare current jobs against a prior snapshot and surface new or changed postings."""
    client = get_client(ctx)
    try:
        current_jobs = await client.list_jobs(board_token, include_content=include_content)
    except GreenhouseAPIError as exc:
        if ctx:
            await ctx.error(f"Greenhouse API error: {exc.message}")
        raise

    normalized_jobs = [_to_normalized_job(board_token, job) for job in current_jobs.jobs]
    current_snapshot = [_to_previous_snapshot(job) for job in normalized_jobs]
    previous_by_id = {
        snapshot.job_id: snapshot
        for snapshot in (_snapshot_from_input(item) for item in (previous_snapshot or []))
    }

    new_jobs: list[NormalizedJobPosting] = []
    updated_jobs: list[NormalizedJobPosting] = []
    unchanged_count = 0

    for job, snapshot in zip(normalized_jobs, current_snapshot, strict=False):
        prior = previous_by_id.get(snapshot.job_id)
        if prior is None:
            new_jobs.append(job)
        elif _change_detected(prior, snapshot):
            updated_jobs.append(job)
        else:
            unchanged_count += 1

    return JobChangeSet(
        board_token=board_token,
        new_jobs=new_jobs,
        updated_jobs=updated_jobs,
        unchanged_count=unchanged_count,
        current_snapshot=current_snapshot,
    )


app = mcp.http_app()

if __name__ == "__main__":
    mcp.run()
