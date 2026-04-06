"""Core tools integration tests using the live Greenhouse Job Board API."""

import pytest

from mcp_greenhouse.api_client import GreenhouseClient


class TestCoreTools:
    """Live API tests for the read-only Greenhouse tool surface."""

    @pytest.mark.asyncio
    async def test_get_job_board(self, client: GreenhouseClient, board_token: str):
        """The board endpoint returns a usable name."""
        board = await client.get_job_board(board_token)
        assert board.name

    @pytest.mark.asyncio
    async def test_list_jobs(self, client: GreenhouseClient, board_token: str):
        """Listing jobs returns a collection with the expected public fields."""
        jobs = await client.list_jobs(board_token, include_content=False)
        assert isinstance(jobs.jobs, list)
        assert jobs.meta.total is None or jobs.meta.total >= 0
        if jobs.jobs:
            first = jobs.jobs[0]
            assert first.id
            assert first.title

    @pytest.mark.asyncio
    async def test_get_first_job_details(self, client: GreenhouseClient, board_token: str):
        """A listed job can be fetched individually with content and pay data."""
        jobs = await client.list_jobs(board_token, include_content=False)
        if not jobs.jobs:
            pytest.skip("Board has no public jobs")
        detail = await client.get_job(board_token, jobs.jobs[0].id, pay_transparency=True)
        assert detail.id == jobs.jobs[0].id
        assert detail.title
