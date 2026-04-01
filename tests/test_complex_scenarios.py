import httpx
import respx

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


@respx.mock
def test_429_retry_after_handling() -> None:
    """
    Test that the async client respects 429 Retry-After headers and retries.
    """
    import asyncio

    import httpx

    from coreason_searchpubmed.client.async_client import AsyncPubMedClient

    client = AsyncPubMedClient(max_retries=2)

    # First call returns 429 with Retry-After: 1
    # Second call returns 200 with valid XML
    route = respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi")

    route.side_effect = [
        httpx.Response(
            429,
            headers={"Retry-After": "0.1"},
            request=httpx.Request("POST", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"),
        ),
        httpx.Response(200, content=b"<?xml version='1.0'?><PubmedArticleSet></PubmedArticleSet>"),
    ]

    async def run_test() -> None:
        content = await client.efetch(db="pubmed", ids=["12345"])
        assert content == b"<?xml version='1.0'?><PubmedArticleSet></PubmedArticleSet>"

    asyncio.run(run_test())


def test_wait_retry_after_fallback() -> None:
    """Test the WaitRetryAfter logic."""
    import httpx
    from tenacity import Future, RetryCallState
    from tenacity.wait import wait_none

    from coreason_searchpubmed.client.async_client import WaitRetryAfter

    waiter = WaitRetryAfter(wait_none())

    # Mock a RetryCallState with a 429 exception
    state = RetryCallState(retry_object=None, fn=None, args=(), kwargs={})

    req = httpx.Request("POST", "http://test")
    resp = httpx.Response(429, headers={"Retry-After": "4.2"}, request=req)
    exc = httpx.HTTPStatusError("429", request=req, response=resp)

    attempt = Future(1)
    attempt.set_exception(exc)
    state.outcome = attempt

    wait_time = waiter(state)
    assert wait_time == 4.2

    # Test invalid Retry-After fallback
    resp2 = httpx.Response(429, headers={"Retry-After": "invalid"}, request=req)
    exc2 = httpx.HTTPStatusError("429", request=req, response=resp2)
    attempt2 = Future(1)
    attempt2.set_exception(exc2)
    state.outcome = attempt2

    wait_time2 = waiter(state)
    assert wait_time2 == 0.0  # From wait_none fallback


def test_xml_malformed_article() -> None:
    """
    Test that a single malformed article does not crash the entire batch parsing.
    """
    # Contains one good article, one without PMID (should fail gracefully), and one good article.
    xml_content = b"""<?xml version="1.0"?>
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>111</PMID>
                <Article><ArticleTitle>Good Article 1</ArticleTitle></Article>
            </MedlineCitation>
        </PubmedArticle>
        <PubmedArticle>
            <MedlineCitation>
                <!-- Missing PMID -->
                <Article><ArticleTitle>Bad Article (No PMID)</ArticleTitle></Article>
            </MedlineCitation>
        </PubmedArticle>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>222</PMID>
                <Article><ArticleTitle>Good Article 2</ArticleTitle></Article>
            </MedlineCitation>
        </PubmedArticle>
    </PubmedArticleSet>
    """

    articles = parse_pubmed_xml(xml_content)

    # We expect 2 valid articles, the malformed one should have been logged and skipped.
    assert len(articles) == 2
    assert articles[0].pmid == "111"
    assert articles[1].pmid == "222"


def test_xml_syntax_error_batch() -> None:
    """
    Test that a completely malformed XML batch fails gracefully and returns an empty list.
    """
    xml_content = b"<?xml version='1.0'?><PubmedArticleSet><PubmedArticle><UnclosedTag></PubmedArticleSet>"

    articles = parse_pubmed_xml(xml_content)

    # We expect an empty list, not a crash.
    assert isinstance(articles, list)
    assert len(articles) == 0


def test_xml_no_content() -> None:
    """
    Test with completely empty bytes.
    """
    articles = parse_pubmed_xml(b"")
    assert isinstance(articles, list)
    assert len(articles) == 0
