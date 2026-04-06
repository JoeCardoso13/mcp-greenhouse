"""Shared fixtures and configuration for integration tests."""

import os

import pytest
import pytest_asyncio

from mcp_greenhouse.api_client import GreenhouseClient


@pytest.fixture
def board_token() -> str:
    """Get a real board token for live API tests."""
    token = os.environ.get("GREENHOUSE_BOARD_TOKEN")
    if not token:
        pytest.skip("GREENHOUSE_BOARD_TOKEN not set")
    return token


@pytest_asyncio.fixture
async def client() -> GreenhouseClient:
    """Create a real Greenhouse client."""
    instance = GreenhouseClient()
    yield instance
    await instance.close()
