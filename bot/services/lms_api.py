"""LMS backend client for bot handlers."""

from __future__ import annotations

from typing import Any

import httpx

from config import BotConfig


class LmsApiError(RuntimeError):
    """Known backend/API failure with user-facing details."""


class LmsApiClient:
    def __init__(self, config: BotConfig, timeout_seconds: float = 10.0) -> None:
        self._base_url = config.lms_api_base_url.rstrip("/")
        self._api_key = config.lms_api_key
        self._timeout = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        try:
            response = httpx.get(
                url,
                headers=self._headers(),
                params=params,
                timeout=self._timeout,
            )
        except httpx.ConnectError as exc:
            detail = str(exc).strip() or "connection refused"
            raise LmsApiError(
                f"Backend error: {detail}. Check that the services are running."
            ) from exc
        except httpx.TimeoutException as exc:
            detail = str(exc).strip() or "request timed out"
            raise LmsApiError(f"Backend error: {detail}.") from exc
        except httpx.HTTPError as exc:
            raise LmsApiError(f"Backend error: {exc}") from exc

        if response.status_code >= 400:
            body = response.text.strip()
            detail = body if body else response.reason_phrase
            raise LmsApiError(f"Backend error: HTTP {response.status_code} {detail}")

        try:
            return response.json()
        except ValueError as exc:
            raise LmsApiError("Backend error: invalid JSON response.") from exc

    def get_items(self) -> list[dict[str, Any]]:
        data = self._get("/items/")
        if not isinstance(data, list):
            raise LmsApiError("Backend error: /items/ returned unexpected format.")
        return data

    def get_pass_rates(self, lab_slug: str) -> list[dict[str, Any]]:
        data = self._get("/analytics/pass-rates", params={"lab": lab_slug})
        if not isinstance(data, list):
            raise LmsApiError(
                "Backend error: /analytics/pass-rates returned unexpected format."
            )
        return data
