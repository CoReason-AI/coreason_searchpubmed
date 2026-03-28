import pytest
import respx
import httpx
from coreason_searchpubmed.client.async_client import AsyncPubMedClient

@respx.mock
@pytest.mark.asyncio
async def test_async_client_none_params():
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        return_value=httpx.Response(200, content=b"")
    )
    client = AsyncPubMedClient(api_key="key")
    # Call _request directly with params=None to trigger line 49
    await client._request("POST", "efetch.fcgi", params=None)
    await client.close()
