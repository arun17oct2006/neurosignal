
"""HTTP client for the AWS Stockcache API."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlsplit

import httpx


class MarketCacheError(RuntimeError):
    """Raised when Stockcache is unavailable or returns an invalid response."""


class MarketCacheClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        configured_url = (
            os.getenv("MARKETCACHE_API_URL", "")
            if base_url is None
            else base_url
        )
        configured_key = (
            os.getenv("MARKETCACHE_API_KEY", "")
            if api_key is None
            else api_key
        )

        self.base_url = configured_url.rstrip("/")
        self.api_key = configured_key

    def action(self, action: str, **data: Any) -> dict[str, Any]:
        if not self.base_url or not self.api_key:
            raise MarketCacheError(
                "MARKETCACHE_API_URL and MARKETCACHE_API_KEY "
                "must both be configured"
            )

        try:
            parsed_url = urlsplit(self.base_url)
        except ValueError:
            raise MarketCacheError(
                "MARKETCACHE_API_URL is invalid"
            ) from None

        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise MarketCacheError(
                "MARKETCACHE_API_URL must be an HTTPS URL"
            )

        # Send the action and its supplied fields to API Gateway.
        request_payload = {"action": action, **data}

        try:
            response = httpx.post(
                self.base_url,
                json=request_payload,
                headers={"x-api-key": self.api_key},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()

        except httpx.HTTPStatusError as exc:
            # Include a limited response body for debugging, never the API key.
            status = exc.response.status_code
            body = exc.response.text[:500]

            raise MarketCacheError(
                f"Stockcache action '{action}' failed "
                f"(HTTP {status}): {body}"
            ) from None

        except httpx.HTTPError as exc:
            # Avoid exposing request details, headers, or credentials.
            raise MarketCacheError(
                f"Stockcache action '{action}' failed "
                f"({type(exc).__name__})"
            ) from None

        except ValueError:
            raise MarketCacheError(
                f"Stockcache action '{action}' returned invalid JSON"
            ) from None

        if not isinstance(payload, dict):
            raise MarketCacheError(
                f"Stockcache action '{action}' returned "
                "a non-object response"
            )

        return payload
