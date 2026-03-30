# Copyright (c) 2026 CoReason, Inc.
import asyncio
import logging
from typing import Any

import httpx
from aiolimiter import AsyncLimiter
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tenacity.wait import wait_base

from coreason_searchpubmed.client.exceptions import PubMedNetworkError

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


class WaitRetryAfter(wait_base):
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


class AsyncPubMedClient:
    def __init__(self, api_key: str | None = None, timeout: float = 30.0, max_retries: int = 3) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        rate = 10.0 if api_key else 3.0
        self.rate_limiter = AsyncLimiter(max_rate=rate, time_period=1.0)
        self.client = httpx.AsyncClient(timeout=timeout)
        self._semaphore = asyncio.Semaphore(int(rate))

    async def close(self) -> None:
        await self.client.aclose()

    async def _request(self, method: str, endpoint: str, params: dict[str, Any] | None = None) -> httpx.Response:
        if params is None:
            params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        url = f"{BASE_URL}{endpoint}"

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_retries),
                wait=WaitRetryAfter(wait_exponential(multiplier=2, min=2, max=10)),
                retry=retry_if_exception_type(httpx.HTTPError),
                reraise=True,
            ):
                with attempt:
                    # Acquire semaphore first to ensure we strictly enforce concurrent connections
                    # and prevent hoarding rate tokens while waiting for a concurrency slot.
                    async with self._semaphore:
                        async with self.rate_limiter:
                            response = await self.client.request(method, url, params=params)
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

    async def efetch(self, db: str, ids: list[str], retmode: str = "xml") -> bytes:
        if not ids:
            return b""
        id_str = ",".join(ids)
        params = {"db": db, "id": id_str, "retmode": retmode}
        response = await self._request("POST", "efetch.fcgi", params=params)
        return bytes(response.content)
