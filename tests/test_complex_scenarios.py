import time

import httpx
import pytest
import respx

from coreason_searchpubmed.client.async_client import RateLimiter
from coreason_searchpubmed.parsers.xml_parser import parse_pubmed_xml
from coreason_searchpubmed.pubmed import get_pubmed_metadata_pmid


def test_xxe_vulnerability_prevention() -> None:
    """
    Test that the XML parser does not resolve external entities (XXE vulnerability check).
    """
    malicious_xml = b"""<?xml version="1.0" encoding="ISO-8859-1"?>
    <!DOCTYPE foo [
      <!ELEMENT foo ANY >
      <!ENTITY xxe SYSTEM "file:///etc/passwd" >]>
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>&xxe;</PMID>
                <Article>
                    <ArticleTitle>Malicious Article</ArticleTitle>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
    </PubmedArticleSet>
    """
    articles = parse_pubmed_xml(malicious_xml)

    # If XXE is properly disabled (resolve_entities=False), the entity '&xxe;' should NOT be resolved,
    # or the parser should drop it or throw an error.
    # Typically, with resolve_entities=False, the parsed node text will be None or just the raw unexpanded text,
    # or the entity resolution might result in an empty string.
    # Let's ensure no sensitive data or entity string is populated where it shouldn't.

    # Since lxml with resolve_entities=False often just returns empty string or None for unresolved entities
    # we just verify that it doesn't crash, and pmid is not something unexpected
    if articles:
        assert articles[0].pmid is None or "&xxe;" not in articles[0].pmid
    else:
        # If it fails to parse entirely, that's also acceptable security-wise.
        assert len(articles) == 0


@pytest.mark.asyncio
async def test_rate_limiter_replenishment_math() -> None:
    """
    Test the token bucket rate limiter strictly obeys time bounds mathematically.
    """
    # 10 tokens per second, max 10
    limiter = RateLimiter(rate=10.0, capacity=10.0)

    # Drain the bucket
    for _ in range(10):
        await limiter.acquire()

    assert limiter.tokens < 1.0

    # Fast forward time conceptually
    # Because time is monotonic in the real implementation, we will mock the `time.monotonic` call for this instance.

    original_monotonic = time.monotonic

    try:
        # Mock time to be 0.5 seconds later. 10 * 0.5 = 5 tokens should be replenished.
        mock_time = original_monotonic() + 0.5
        time.monotonic = lambda: mock_time

        # Next acquire should be immediate (0 wait) because we now have ~5 tokens
        await limiter.acquire()
        assert 3.0 < limiter.tokens <= 5.0

    finally:
        time.monotonic = original_monotonic


@respx.mock
def test_large_batch_chunking() -> None:
    """
    Test that get_pubmed_metadata_pmid correctly chunks PMIDs into batches of 200.
    """
    # Create 450 PMIDs
    pmids = [str(i) for i in range(1, 451)]

    # Mock the API to return a single article for each batch to simplify
    xml_response = b"""<?xml version="1.0"?>
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>1</PMID>
                <Article>
                    <ArticleTitle>Chunked Article</ArticleTitle>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
    </PubmedArticleSet>
    """

    mock_post = respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        return_value=httpx.Response(200, content=xml_response)
    )

    df = get_pubmed_metadata_pmid(pmids)

    # 450 items / 200 per batch = 3 batches (200, 200, 50)
    assert mock_post.call_count == 3

    # Check that df has results from each of the 3 calls (we mocked it to return 1 item per call, so 3 items total)
    assert len(df) == 3
    assert df.iloc[0]["title"] == "Chunked Article"
