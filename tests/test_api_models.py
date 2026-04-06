"""Tests for Greenhouse API models."""

from mcp_greenhouse.api_models import (
    JobAttributeReport,
    JobChangeSet,
    JobListResponse,
    JobSummary,
    NormalizedJobPosting,
)


def test_job_summary_model() -> None:
    """JobSummary parses public Greenhouse fields."""
    job = JobSummary.model_validate(
        {
            "id": 123,
            "internal_job_id": 456,
            "title": "Platform Engineer",
            "updated_at": "2026-04-01T00:00:00Z",
            "location": {"name": "Berlin"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/123",
            "metadata": [{"name": "Level", "value": "Senior"}],
        }
    )
    assert job.id == 123
    assert job.location is not None
    assert job.location.name == "Berlin"
    assert isinstance(job.metadata, list)


def test_job_list_response_defaults() -> None:
    """Job list responses default to an empty list and empty meta."""
    response = JobListResponse()
    assert response.jobs == []
    assert response.meta.total is None


def test_normalized_job_posting_defaults() -> None:
    """Normalized jobs provide stable default collections."""
    posting = NormalizedJobPosting(
        job_id=1,
        board_token="acme",
        title="Engineer",
    )
    assert posting.departments == []
    assert posting.offices == []
    assert posting.metadata == {}
    assert posting.has_salary_data is False


def test_attribute_report_model() -> None:
    """Attribute reports capture field presence flags."""
    report = JobAttributeReport(
        job_id=1,
        board_token="acme",
        has_salary_data=True,
        has_experience_level=True,
        has_workplace_type=False,
        has_department_data=True,
        has_office_data=False,
        metadata_field_names=["Experience Level"],
        experience_level_values=["Senior"],
        salary_range_count=1,
    )
    assert report.has_salary_data is True
    assert report.salary_range_count == 1


def test_job_change_set_model() -> None:
    """Change sets carry snapshot state across polling runs."""
    changes = JobChangeSet(board_token="acme")
    assert changes.new_jobs == []
    assert changes.updated_jobs == []
    assert changes.current_snapshot == []
