# Copyright (c) 2026 CoReason, Inc.
import asyncio
from typing import Any

import httpx
import pytest
import respx

from coreason_searchpubmed.client.async_client import AsyncPubMedClient


@pytest.mark.asyncio
@respx.mock
async def test_async_pubmed_client_rate_limiter() -> None:
    mock_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    # Since monkeypatching asyncio.sleep causes problems with event loop starvation or infinite token bucket looping
    # (as the semaphore lock + fast-forward time can lead to a single task hoarding the CPU),
    # let's write a mathematical test that tracks REAL execution times, but uses very small requests
    # and just proves the token bucket algorithm delays requests by at least the expected mathematical time.
    # To avoid test taking too long, we can monkeypatch the RateLimiter rate/capacity specifically for the test!

    # We will test a custom AsyncPubMedClient with rate = 100/sec, capacity = 10.
    # 20 requests: first 10 take 0s. The next 10 take 10 * 0.01 = 0.1s. Total time ~ 0.1s.

    current_time = []

    def side_effect(request: httpx.Request, **kwargs: Any) -> httpx.Response:  # noqa: ARG001
        import time

        current_time.append(time.monotonic())
        return httpx.Response(200, content=b"<xml></xml>")

    respx.post(mock_url).mock(side_effect=side_effect)

    client = AsyncPubMedClient(api_key="fake_key", max_retries=1)
    # Monkeypatch the rate limiter for faster testing:
    # capacity = 10, rate = 100 req/sec
    client.rate_limiter.capacity = 10.0
    client.rate_limiter.tokens = 10.0
    client.rate_limiter.rate = 100.0
    client._semaphore = asyncio.Semaphore(100)  # Ensure concurrency doesn't limit us

    # Test 30 concurrent requests
    tasks = [client.efetch(db="pubmed", ids=[str(i)]) for i in range(30)]

    import time

    start = time.monotonic()
    await asyncio.gather(*tasks)
    end = time.monotonic()

    await client.close()

    execution_times = current_time
    execution_times.sort()

    assert len(execution_times) == 30

    # The 30 requests should take at least mathematically:
    # first 10 -> immediate
    # next 20 -> 20 / 100 = 0.2 seconds minimum
    total_time = end - start
    assert total_time >= 0.2
