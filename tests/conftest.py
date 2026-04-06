"""Shared fixtures for unit tests."""

from unittest.mock import AsyncMock

import pytest

from mcp_greenhouse.api_models import (
    DepartmentsResponse,
    JobBoard,
    JobDetail,
    JobListMeta,
    JobListResponse,
    JobSummary,
    Location,
    OfficesResponse,
)
from mcp_greenhouse.server import mcp


@pytest.fixture
def mcp_server():
    """Return the MCP server instance."""
    return mcp


@pytest.fixture
def sample_job() -> JobSummary:
    """A representative Greenhouse job posting."""
    return JobSummary(
        id=101,
        internal_job_id=2001,
        title="Senior Backend Engineer",
        updated_at="2026-04-01T12:00:00Z",
        location=Location(name="Remote - US"),
        absolute_url="https://boards.greenhouse.io/acme/jobs/101",
        metadata=[
            {"name": "Experience Level", "value": "Senior"},
            {"name": "Workplace Type", "value": "Remote"},
        ],
        content="Senior role with remote flexibility.",
    )


@pytest.fixture
def mock_client(sample_job: JobSummary):
    """Create a mock Greenhouse API client."""
    client = AsyncMock()
    client.get_job_board = AsyncMock(return_value=JobBoard(name="Acme", content="<p>Hiring!</p>"))
    client.list_jobs = AsyncMock(
        return_value=JobListResponse(
            jobs=[sample_job],
            meta=JobListMeta(total=1),
        )
    )
    client.get_job = AsyncMock(
        return_value=JobDetail.model_validate(
            sample_job.model_dump()
            | {
                "pay_input_ranges": [
                    {
                        "min_cents": 10000000,
                        "max_cents": 15000000,
                        "currency_type": "USD",
                        "title": "US Salary Range",
                    }
                ],
                "departments": [{"id": 1, "name": "Engineering"}],
                "offices": [{"id": 10, "name": "Remote US"}],
            }
        )
    )
    client.list_departments = AsyncMock(
        return_value=DepartmentsResponse.model_validate(
            {"departments": [{"id": 1, "name": "Engineering", "jobs": [sample_job.model_dump()]}]}
        )
    )
    client.list_offices = AsyncMock(
        return_value=OfficesResponse.model_validate(
            {"offices": [{"id": 10, "name": "Remote US", "departments": []}]}
        )
    )
    return client
