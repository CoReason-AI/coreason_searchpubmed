# Copyright (c) 2026 CoReason, Inc.
import logging
from typing import Any

import httpx
from ratelimit import limits, sleep_and_retry
from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tenacity.wait import wait_base

from coreason_searchpubmed.client.exceptions import PubMedNetworkError

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


class WaitRetryAfter(wait_base):  # type: ignore[misc]
    """Wait strategy that honors Retry-After header, falling back to exponential backoff."""

    def __init__(self, fallback: wait_base) -> None:
        self.fallback = fallback

    def __call__(self, retry_state: RetryCallState) -> float:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
            retry_after = exc.response.headers.get("Retry-After")
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:  # pragma: no cover
                    pass
        return float(self.fallback(retry_state))


class PubMedClient:
    def __init__(self, api_key: str | None = None, timeout: float = 30.0, max_retries: int = 3) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        rate = 10 if api_key else 3

        @sleep_and_retry
        @limits(calls=rate, period=1)
        def rate_limited_request(method: str, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
            return self.client.request(method, url, params=params)

        self._rate_limited_request = rate_limited_request
        self.client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self.client.close()

    def _request(self, method: str, endpoint: str, params: dict[str, Any] | None = None) -> httpx.Response:
        if params is None:
            params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        url = f"{BASE_URL}{endpoint}"

        try:
            for attempt in Retrying(
                stop=stop_after_attempt(self.max_retries),
                wait=WaitRetryAfter(wait_exponential(multiplier=2, min=2, max=10)),
                retry=retry_if_exception_type(httpx.HTTPError),
                reraise=True,
            ):
                with attempt:
                    response = self._rate_limited_request(method, url, params=params)
                    if response.status_code == 429:
                        logger.warning("Rate limited (429). Retrying via tenacity.")
                        raise httpx.HTTPStatusError(
                            "429 Too Many Requests", request=response.request, response=response
                        )
                    response.raise_for_status()
                    return response

        except httpx.HTTPError as e:
            logger.error(f"HTTP error after {self.max_retries} attempts: {e}")
            raise PubMedNetworkError(f"Failed to fetch {url} after {self.max_retries} attempts.") from e

        raise PubMedNetworkError(f"Failed to fetch {url} after {self.max_retries} attempts.")  # pragma: no cover

    def efetch(self, db: str, ids: list[str], retmode: str = "xml") -> bytes:
        if not ids:
            return b""
        id_str = ",".join(ids)
        params = {"db": db, "id": id_str, "retmode": retmode}
        response = self._request("POST", "efetch.fcgi", params=params)
        return bytes(response.content)
