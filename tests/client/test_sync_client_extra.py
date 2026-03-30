# Copyright (c) 2026 CoReason, Inc.

from coreason_searchpubmed.client.sync_client import PubMedClient


def test_sync_client_none_params() -> None:
    import httpx
    import respx

    client = PubMedClient()

    @respx.mock
    def run_test() -> None:
        respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
            return_value=httpx.Response(200, content=b"data")
        )
        resp = client._request("POST", "efetch.fcgi", None)
        assert resp.content == b"data"

    run_test()
    client.close()


def test_sync_client_retry_after_invalid_header() -> None:
    import httpx
    import respx

    client = PubMedClient(max_retries=2)

    @respx.mock
    def run_test() -> None:
        respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "invalid"}),
                httpx.Response(200, content=b"recovered")
            ]
        )
        resp = client.efetch("pubmed", ["123"])
        assert resp == b"recovered"

    run_test()
    client.close()
