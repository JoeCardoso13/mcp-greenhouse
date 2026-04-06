"""Tests for Greenhouse MCP Server tools and skill resource."""

from unittest.mock import patch

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_greenhouse.api_client import GreenhouseAPIError
from mcp_greenhouse.server import SKILL_CONTENT


class TestSkillResource:
    """Test the skill resource and server instructions."""

    @pytest.mark.asyncio
    async def test_initialize_returns_instructions(self, mcp_server):
        """Server instructions reference the Greenhouse skill resource."""
        async with Client(mcp_server) as client:
            result = await client.initialize()
            assert result.instructions is not None
            assert "skill://greenhouse/usage" in result.instructions

    @pytest.mark.asyncio
    async def test_skill_resource_listed(self, mcp_server):
        """skill://greenhouse/usage appears in resource listing."""
        async with Client(mcp_server) as client:
            resources = await client.list_resources()
            uris = [str(r.uri) for r in resources]
            assert "skill://greenhouse/usage" in uris

    def test_skill_content_covers_key_workflows(self):
        """The embedded skill content describes the intended workflows."""
        assert "list_new_or_updated_jobs" in SKILL_CONTENT
        assert "normalize_job_data" in SKILL_CONTENT
        assert "inspect_job_attributes" in SKILL_CONTENT


class TestToolListing:
    """Test that all tools are registered and discoverable."""

    @pytest.mark.asyncio
    async def test_all_tools_listed(self, mcp_server):
        """All expected tools appear in tool listing."""
        async with Client(mcp_server) as client:
            tools = await client.list_tools()
            names = {t.name for t in tools}
            expected = {
                "get_job_board",
                "list_company_jobs",
                "get_job_details",
                "list_departments",
                "list_offices",
                "normalize_job_data",
                "inspect_job_attributes",
                "list_new_or_updated_jobs",
            }
            assert expected == names


class TestMCPTools:
    """Test the MCP server tools via FastMCP Client."""

    @pytest.mark.asyncio
    async def test_get_job_board(self, mcp_server, mock_client):
        """The board metadata tool delegates to the API client."""
        with patch("mcp_greenhouse.server.get_client", return_value=mock_client):
            async with Client(mcp_server) as client:
                await client.call_tool("get_job_board", {"board_token": "acme"})
        mock_client.get_job_board.assert_called_once_with("acme")

    @pytest.mark.asyncio
    async def test_normalize_job_data(self, mcp_server, mock_client):
        """Normalization fetches jobs and maps them into the stable schema."""
        with patch("mcp_greenhouse.server.get_client", return_value=mock_client):
            async with Client(mcp_server) as client:
                result = await client.call_tool(
                    "normalize_job_data",
                    {"board_token": "acme", "include_content": True},
                )
        mock_client.list_jobs.assert_called_once_with("acme", include_content=True)
        assert result is not None

    @pytest.mark.asyncio
    async def test_list_new_or_updated_jobs(self, mcp_server, mock_client):
        """Polling diff marks changed jobs as updated."""
        with patch("mcp_greenhouse.server.get_client", return_value=mock_client):
            async with Client(mcp_server) as client:
                result = await client.call_tool(
                    "list_new_or_updated_jobs",
                    {
                        "board_token": "acme",
                        "previous_snapshot": [
                            {
                                "job_id": 101,
                                "updated_timestamp": "2026-03-01T00:00:00Z",
                                "title": "Senior Backend Engineer",
                            }
                        ],
                    },
                )
        mock_client.list_jobs.assert_called_once_with("acme", include_content=True)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_job_board_api_error(self, mcp_server, mock_client):
        """Tool errors surface as ToolError."""
        mock_client.get_job_board.side_effect = GreenhouseAPIError(404, "Board not found")
        with patch("mcp_greenhouse.server.get_client", return_value=mock_client):
            async with Client(mcp_server) as client:
                with pytest.raises(ToolError, match="404"):
                    await client.call_tool("get_job_board", {"board_token": "missing"})
