# Copyright (c) 2026 CoReason, Inc.
import asyncio
import time
from typing import Any

import httpx

from coreason_searchpubmed.client.exceptions import PubMedNetworkError
from coreason_searchpubmed.utils.logger import logger

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


class RateLimiter:
    def __init__(self, rate: float, capacity: float) -> None:
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now

                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait_time = (1 - self.tokens) / self.rate
            await asyncio.sleep(wait_time)


class AsyncPubMedClient:
    def __init__(self, api_key: str | None = None, timeout: float = 30.0, max_retries: int = 3) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        rate = 10.0 if api_key else 3.0
        self.rate_limiter = RateLimiter(rate=rate, capacity=rate)
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self.client.aclose()

    async def _request(self, method: str, endpoint: str, params: dict[str, Any] | None = None) -> httpx.Response:
        if params is None:
            params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        url = f"{BASE_URL}{endpoint}"

        for attempt in range(1, self.max_retries + 1):
            await self.rate_limiter.acquire()
            try:
                response = await self.client.request(method, url, params=params)
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", 1.0))
                    logger.warning(f"Rate limited (429). Retrying after {retry_after}s.")
                    await asyncio.sleep(retry_after)
                    continue
                response.raise_for_status()
                return response
            except httpx.HTTPError as e:
                logger.error(f"HTTP error on attempt {attempt}: {e}")
                if attempt == self.max_retries:
                    raise PubMedNetworkError(f"Failed to fetch {url} after {self.max_retries} attempts.") from e
                await asyncio.sleep(2**attempt)

        raise PubMedNetworkError(f"Failed to fetch {url} after {self.max_retries} attempts.")

    async def efetch(self, db: str, ids: list[str], retmode: str = "xml") -> bytes:
        if not ids:
            return b""
        id_str = ",".join(ids)
        params = {"db": db, "id": id_str, "retmode": retmode}
        response = await self._request("POST", "efetch.fcgi", params=params)
        return bytes(response.content)
