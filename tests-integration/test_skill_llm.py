"""Smoke tests for LLM tool selection against the embedded Greenhouse skill."""

from __future__ import annotations

import os
from typing import Any

import pytest
from fastmcp import Client

from mcp_greenhouse.server import SKILL_CONTENT, mcp


def get_anthropic_client():
    """Create an Anthropic client when the key is available."""
    token = os.environ.get("ANTHROPIC_API_KEY")
    if not token:
        pytest.skip("ANTHROPIC_API_KEY not set")
    import anthropic

    return anthropic.Anthropic(api_key=token)


async def get_server_context() -> dict[str, Any]:
    """Extract instructions, skill content, and tool definitions from the MCP server."""
    async with Client(mcp) as client:
        init = await client.initialize()
        instructions = init.instructions

        tools_list = await client.list_tools()
        tools = [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            }
            for tool in tools_list
        ]

        return {
            "instructions": instructions,
            "skill": SKILL_CONTENT,
            "tools": tools,
        }


def call_llm(ctx: dict[str, Any], user_prompt: str):
    """Ask Claude which tool it would use, given the server instructions and skill."""
    client = get_anthropic_client()
    system = (
        "You are an assistant deciding which MCP tool to call.\n\n"
        f"## Server Instructions\n{ctx['instructions']}\n\n"
        f"## Skill Resource\n{ctx['skill']}"
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
        tools=[{"type": "custom", **tool} for tool in ctx["tools"]],
    )
    tool_calls = [block for block in response.content if block.type == "tool_use"]
    assert tool_calls, "LLM did not call any tool"
    return tool_calls[0]


class TestSkillLLMInvocation:
    """Test that Claude selects the intended tool for key workflows."""

    @pytest.mark.asyncio
    async def test_polling_prompt_selects_diff_tool(self):
        """Polling workflows should choose the change-detection tool."""
        ctx = await get_server_context()
        tool_call = call_llm(
            ctx,
            "Check board token acme for newly posted or updated roles since my previous snapshot.",
        )
        assert tool_call.name == "list_new_or_updated_jobs"

    @pytest.mark.asyncio
    async def test_normalization_prompt_selects_normalize_tool(self):
        """Storage-oriented prompts should choose normalization."""
        ctx = await get_server_context()
        tool_call = call_llm(
            ctx,
            "Normalize all public jobs for board token acme so I can store title, location, URL, updated timestamp, department, and office.",
        )
        assert tool_call.name == "normalize_job_data"

    @pytest.mark.asyncio
    async def test_salary_prompt_selects_attribute_tool(self):
        """Attribute-inspection prompts should use inspect_job_attributes."""
        ctx = await get_server_context()
        tool_call = call_llm(
            ctx,
            "For board token acme and job id 123, tell me whether salary data and experience level are present.",
        )
        assert tool_call.name == "inspect_job_attributes"
