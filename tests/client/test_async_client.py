import httpx
import pytest
import respx

from coreason_searchpubmed.client.async_client import AsyncPubMedClient, RateLimiter
from coreason_searchpubmed.client.exceptions import PubMedNetworkError


@pytest.mark.asyncio
async def test_rate_limiter() -> None:
    limiter = RateLimiter(rate=100.0, capacity=100.0)
    await limiter.acquire()
    assert limiter.tokens < 100.0


@pytest.mark.asyncio
async def test_rate_limiter_wait() -> None:
    limiter = RateLimiter(rate=100.0, capacity=100.0)
    limiter.tokens = 0.0  # Force it to wait
    await limiter.acquire()
    assert limiter.tokens < 100.0


@respx.mock
@pytest.mark.asyncio
async def test_async_client_success() -> None:
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        return_value=httpx.Response(200, content=b"xml_data")
    )
    client = AsyncPubMedClient(api_key="key")
    data = await client.efetch("pubmed", ["123"])
    assert data == b"xml_data"
    await client.close()


@respx.mock
@pytest.mark.asyncio
async def test_async_client_empty_ids() -> None:
    client = AsyncPubMedClient()
    data = await client.efetch("pubmed", [])
    assert data == b""
    await client.close()


@respx.mock
@pytest.mark.asyncio
async def test_async_client_429_retry() -> None:
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        side_effect=[httpx.Response(429, headers={"Retry-After": "0.1"}), httpx.Response(200, content=b"success")]
    )
    client = AsyncPubMedClient()
    data = await client.efetch("pubmed", ["123"])
    assert data == b"success"
    await client.close()


@respx.mock
@pytest.mark.asyncio
async def test_async_client_http_error_retry() -> None:
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        side_effect=[httpx.Response(500), httpx.Response(500), httpx.Response(200, content=b"recovered")]
    )
    client = AsyncPubMedClient(max_retries=3)
    data = await client.efetch("pubmed", ["123"])
    assert data == b"recovered"
    await client.close()


@respx.mock
@pytest.mark.asyncio
async def test_async_client_max_retries_exceeded() -> None:
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(return_value=httpx.Response(500))
    client = AsyncPubMedClient(max_retries=1)
    with pytest.raises(PubMedNetworkError):
        await client.efetch("pubmed", ["123"])
    await client.close()


@respx.mock
@pytest.mark.asyncio
async def test_async_client_http_exception() -> None:
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )
    client = AsyncPubMedClient(max_retries=1)
    with pytest.raises(PubMedNetworkError):
        await client.efetch("pubmed", ["123"])
    await client.close()


@respx.mock
@pytest.mark.asyncio
async def test_async_client_http_exception_max() -> None:
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(return_value=httpx.Response(500))
    client = AsyncPubMedClient(max_retries=0)
    with pytest.raises(PubMedNetworkError):
        await client.efetch("pubmed", ["123"])
    await client.close()
