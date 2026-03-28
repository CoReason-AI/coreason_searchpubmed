import pytest
import respx
import httpx
import time
from coreason_searchpubmed.client.sync_client import PubMedClient, SyncRateLimiter
from coreason_searchpubmed.client.exceptions import PubMedNetworkError

def test_sync_rate_limiter():
    limiter = SyncRateLimiter(rate=100.0, capacity=100.0)
    limiter.acquire()
    assert limiter.tokens < 100.0

def test_sync_rate_limiter_wait():
    limiter = SyncRateLimiter(rate=100.0, capacity=100.0)
    limiter.tokens = 0.0
    limiter.acquire()
    assert limiter.tokens < 100.0

@respx.mock
def test_sync_client_success():
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        return_value=httpx.Response(200, content=b"xml_data")
    )
    client = PubMedClient(api_key="key")
    data = client.efetch("pubmed", ["123"])
    assert data == b"xml_data"
    client.close()

def test_sync_client_empty_ids():
    client = PubMedClient()
    data = client.efetch("pubmed", [])
    assert data == b""
    client.close()

@respx.mock
def test_sync_client_429_retry():
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0.1"}),
            httpx.Response(200, content=b"success")
        ]
    )
    client = PubMedClient()
    data = client.efetch("pubmed", ["123"])
    assert data == b"success"
    client.close()

@respx.mock
def test_sync_client_http_error_retry():
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(200, content=b"recovered")
        ]
    )
    client = PubMedClient(max_retries=3)
    data = client.efetch("pubmed", ["123"])
    assert data == b"recovered"
    client.close()

@respx.mock
def test_sync_client_max_retries_exceeded():
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        return_value=httpx.Response(500)
    )
    client = PubMedClient(max_retries=1)
    with pytest.raises(PubMedNetworkError):
        client.efetch("pubmed", ["123"])
    client.close()

@respx.mock
def test_sync_client_http_exception():
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )
    client = PubMedClient(max_retries=1)
    with pytest.raises(PubMedNetworkError):
        client.efetch("pubmed", ["123"])
    client.close()

@respx.mock
def test_sync_client_http_exception_max():
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        return_value=httpx.Response(500)
    )
    client = PubMedClient(max_retries=0)
    with pytest.raises(PubMedNetworkError):
        client.efetch("pubmed", ["123"])
    client.close()
