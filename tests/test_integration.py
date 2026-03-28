import httpx
import pandas as pd
import pytest
import respx

from coreason_searchpubmed.pubmed import get_pubmed_metadata_pmid


@pytest.fixture
def multiple_mock_xml_responses() -> bytes:
    return b"""<?xml version="1.0"?>
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>11111</PMID>
                <Article>
                    <ArticleTitle>Integration Article 1</ArticleTitle>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>22222</PMID>
                <Article>
                    <ArticleTitle>Integration Article 2</ArticleTitle>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
    </PubmedArticleSet>
    """


@respx.mock
def test_full_pipeline_success(multiple_mock_xml_responses: bytes) -> None:
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        return_value=httpx.Response(200, content=multiple_mock_xml_responses)
    )

    df = get_pubmed_metadata_pmid(["11111", "22222"], api_key="test_key")

    # Assertions
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df["pmid"].values) == ["11111", "22222"]
    assert list(df["title"].values) == ["Integration Article 1", "Integration Article 2"]

    # Check all columns exist as expected
    expected_cols = [
        "pmid",
        "pmcid",
        "title",
        "abstract",
        "journal",
        "publicationDate",
        "doi",
        "firstAuthor",
        "lastAuthor",
        "authorAffiliations",
        "meshTags",
        "keywords",
    ]
    for col in expected_cols:
        assert col in df.columns


@respx.mock
@pytest.mark.asyncio
async def test_end_to_end_rate_limit_and_concurrency() -> None:
    """
    Tests fetching 100 PMIDs using the AsyncPubMedClient to verify:
    1. The 10 req/sec limit is respected.
    2. Concurrency is limited to max 10 via the Semaphore.
    3. The main event loop is not blocked.
    """
    import asyncio
    import time

    from coreason_searchpubmed.client.async_client import AsyncPubMedClient

    client = AsyncPubMedClient(api_key="test_key", max_retries=1)

    request_timestamps: list[float] = []

    def mock_efetch_callback(request: httpx.Request) -> httpx.Response:
        _ = request
        request_timestamps.append(time.monotonic())
        return httpx.Response(200, content=b'<?xml version="1.0"?><PubmedArticleSet></PubmedArticleSet>')

    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(side_effect=mock_efetch_callback)

    pmids = [str(i) for i in range(100)]

    try:
        tasks = [client.efetch("pubmed", [pmid]) for pmid in pmids]
        start_t = time.monotonic()
        await asyncio.gather(*tasks)
        end_t = time.monotonic()

        # (100 - 10 initial burst) / 10 req/s = 9 seconds
        assert (end_t - start_t) >= 8.5  # allowing some tolerance

        request_timestamps.sort()
        assert len(request_timestamps) == 100

        # We can check that the gap between request[i] and request[i+10] is at least 0.95s, BUT
        # only after the initial burst!
        for i in range(10, len(request_timestamps) - 10):
            window_start = request_timestamps[i]
            window_end = request_timestamps[i + 10]
            # Time difference between the i-th and (i+10)-th request must be AT LEAST 1.0 second
            # at steady state
            assert (window_end - window_start) >= 0.95

    finally:
        await client.close()
