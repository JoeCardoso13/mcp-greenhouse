"""Unit tests for the Greenhouse API client."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from mcp_greenhouse.api_client import GreenhouseAPIError, GreenhouseClient


@pytest_asyncio.fixture
async def client():
    """Create a client with a mocked session."""
    instance = GreenhouseClient()
    instance._session = AsyncMock()
    yield instance
    await instance.close()


class TestClientInitialization:
    """Test client creation and configuration."""

    def test_init_defaults(self):
        """Client defaults to the public Greenhouse base URL."""
        client = GreenhouseClient()
        assert client.base_url == "https://boards-api.greenhouse.io/v1"
        assert client.timeout == 30.0

    def test_custom_timeout_and_base_url(self):
        """Client accepts custom timeout and base URL."""
        client = GreenhouseClient(timeout=10.0, base_url="https://example.test/v1/")
        assert client.timeout == 10.0
        assert client.base_url == "https://example.test/v1"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Client works as an async context manager."""
        async with GreenhouseClient() as managed:
            assert managed._session is not None
        assert managed._session is None


class TestClientMethods:
    """Test API client methods with mocked responses."""

    @pytest.mark.asyncio
    async def test_get_job_board(self, client):
        """Board metadata is parsed into a JobBoard model."""
        with patch.object(
            client, "_request", return_value={"name": "Acme", "content": "<p>Hello</p>"}
        ):
            board = await client.get_job_board("acme")
        assert board.name == "Acme"

    @pytest.mark.asyncio
    async def test_list_jobs(self, client):
        """Job lists are parsed and the total is preserved."""
        with patch.object(
            client,
            "_request",
            return_value={"jobs": [{"id": 1, "title": "Engineer"}], "meta": {"total": 1}},
        ):
            jobs = await client.list_jobs("acme", include_content=True)
        assert len(jobs.jobs) == 1
        assert jobs.meta.total == 1

    @pytest.mark.asyncio
    async def test_get_job(self, client):
        """Single job lookups are parsed into a JobDetail model."""
        with patch.object(client, "_request", return_value={"id": 1, "title": "Engineer"}):
            job = await client.get_job("acme", 1, questions=True, pay_transparency=True)
        assert job.id == 1
        assert job.title == "Engineer"

    @pytest.mark.asyncio
    async def test_list_departments(self, client):
        """Department listings are parsed into typed responses."""
        with patch.object(
            client, "_request", return_value={"departments": [{"id": 1, "name": "Eng"}]}
        ):
            response = await client.list_departments("acme", render_as="tree")
        assert response.departments[0].name == "Eng"

    @pytest.mark.asyncio
    async def test_list_offices(self, client):
        """Office listings are parsed into typed responses."""
        with patch.object(
            client, "_request", return_value={"offices": [{"id": 10, "name": "Remote"}]}
        ):
            response = await client.list_offices("acme")
        assert response.offices[0].name == "Remote"


class TestErrorHandling:
    """Test error handling for API errors."""

    @pytest.mark.asyncio
    async def test_list_jobs_propagates_api_error(self, client):
        """Explicit API errors bubble up unchanged."""
        with patch.object(
            client, "_request", side_effect=GreenhouseAPIError(404, "Board not found")
        ):
            with pytest.raises(GreenhouseAPIError, match="Board not found"):
                await client.list_jobs("missing-board")

    def test_error_string_representation(self):
        """The exception string includes status and message."""
        err = GreenhouseAPIError(401, "Unauthorized", {"message": "Unauthorized"})
        assert "401" in str(err)
        assert "Unauthorized" in str(err)
