import pytest
import respx
import httpx
from coreason_searchpubmed.client.sync_client import PubMedClient

@respx.mock
def test_sync_client_none_params():
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        return_value=httpx.Response(200, content=b"")
    )
    client = PubMedClient(api_key="key")
    # Call _request directly with params=None to trigger line 49
    client._request("POST", "efetch.fcgi", params=None)
    client.close()
