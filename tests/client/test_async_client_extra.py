# Copyright (c) 2026 CoReason, Inc.
import pytest

from coreason_searchpubmed.client.async_client import AsyncPubMedClient


@pytest.mark.asyncio
async def test_async_client_none_params() -> None:
    client = AsyncPubMedClient()
    import httpx
    import respx

    @respx.mock
    async def run_test() -> None:
        respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
            return_value=httpx.Response(200, content=b"data")
        )
        resp = await client._request("POST", "efetch.fcgi", None)
        assert resp.content == b"data"

    await run_test()
    await client.close()

@pytest.mark.asyncio
async def test_async_client_retry_after_invalid_header() -> None:
    import httpx
    import respx

    from coreason_searchpubmed.client.async_client import AsyncPubMedClient

    client = AsyncPubMedClient(max_retries=2)

    @respx.mock
    async def run_test() -> None:
        respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "invalid"}),
                httpx.Response(200, content=b"recovered")
            ]
        )
        resp = await client.efetch("pubmed", ["123"])
        assert resp == b"recovered"

    await run_test()
    await client.close()
