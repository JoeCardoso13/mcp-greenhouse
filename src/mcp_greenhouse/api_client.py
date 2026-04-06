"""Async HTTP client for the Greenhouse Job Board API."""

from __future__ import annotations

import json
from typing import Any, Literal

import aiohttp
from aiohttp import ClientError

from .api_models import DepartmentsResponse, JobBoard, JobDetail, JobListResponse, OfficesResponse


class GreenhouseAPIError(Exception):
    """Exception raised for Greenhouse API errors."""

    def __init__(self, status: int, message: str, details: Any | None = None) -> None:
        self.status = status
        self.message = message
        self.details = details
        super().__init__(f"Greenhouse API Error {status}: {message}")


class GreenhouseClient:
    """Async client for the public Greenhouse Job Board API."""

    BASE_URL = "https://boards-api.greenhouse.io/v1"

    def __init__(self, timeout: float = 30.0, base_url: str | None = None) -> None:
        self.timeout = timeout
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> GreenhouseClient:
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def _ensure_session(self) -> None:
        if self._session is None:
            headers = {
                "User-Agent": "mcp-server-greenhouse/0.1.0",
                "Accept": "application/json",
            }
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make an HTTP request to the Greenhouse API."""
        await self._ensure_session()
        if self._session is None:
            raise RuntimeError("Session not initialized")

        url = f"{self.base_url}{path}"
        filtered_params = {k: v for k, v in (params or {}).items() if v is not None}

        try:
            async with self._session.request(method, url, params=filtered_params) as response:
                text = await response.text()
                payload: Any
                try:
                    payload = json.loads(text) if text else {}
                except json.JSONDecodeError:
                    payload = {"raw": text}

                if response.status >= 400:
                    message = (
                        self._extract_error_message(payload) or response.reason or "Unknown error"
                    )
                    raise GreenhouseAPIError(response.status, message, payload)

                return payload
        except ClientError as exc:
            raise GreenhouseAPIError(500, f"Network error: {exc}") from exc

    @staticmethod
    def _extract_error_message(payload: Any) -> str | None:
        """Extract an error message from a Greenhouse error payload."""
        if isinstance(payload, dict):
            for key in ("error", "message", "errors"):
                value = payload.get(key)
                if isinstance(value, str):
                    return value
                if isinstance(value, list) and value:
                    first = value[0]
                    if isinstance(first, str):
                        return first
                    if isinstance(first, dict):
                        return str(first.get("message") or first)
                if isinstance(value, dict):
                    return str(value.get("message") or value)
        return None

    async def get_job_board(self, board_token: str) -> JobBoard:
        """Fetch job board metadata."""
        data = await self._request("GET", f"/boards/{board_token}")
        return JobBoard.model_validate(data)

    async def list_jobs(self, board_token: str, include_content: bool = False) -> JobListResponse:
        """List public jobs for a board."""
        data = await self._request(
            "GET",
            f"/boards/{board_token}/jobs",
            params={"content": str(include_content).lower() if include_content else None},
        )
        return JobListResponse.model_validate(data)

    async def get_job(
        self,
        board_token: str,
        job_id: int,
        questions: bool = False,
        pay_transparency: bool = False,
    ) -> JobDetail:
        """Fetch a single job posting."""
        data = await self._request(
            "GET",
            f"/boards/{board_token}/jobs/{job_id}",
            params={
                "questions": str(questions).lower() if questions else None,
                "pay_transparency": str(pay_transparency).lower() if pay_transparency else None,
            },
        )
        return JobDetail.model_validate(data)

    async def list_departments(
        self,
        board_token: str,
        render_as: Literal["list", "tree"] = "list",
    ) -> DepartmentsResponse:
        """List departments for a board."""
        data = await self._request(
            "GET",
            f"/boards/{board_token}/departments",
            params={"render_as": render_as},
        )
        return DepartmentsResponse.model_validate(data)

    async def list_offices(
        self,
        board_token: str,
        render_as: Literal["list", "tree"] = "list",
    ) -> OfficesResponse:
        """List offices for a board."""
        data = await self._request(
            "GET",
            f"/boards/{board_token}/offices",
            params={"render_as": render_as},
        )
        return OfficesResponse.model_validate(data)
