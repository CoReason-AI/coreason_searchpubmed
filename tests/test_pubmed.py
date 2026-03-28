import asyncio

import httpx
import pandas as pd
import pytest
import respx

from coreason_searchpubmed.pubmed import get_pubmed_metadata_pmid


@pytest.fixture
def mock_xml_response() -> bytes:
    return b"""<?xml version="1.0"?>
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
                <Article>
                    <ArticleTitle>Test Article</ArticleTitle>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
    </PubmedArticleSet>
    """


def test_get_pubmed_metadata_pmid_empty() -> None:
    df = get_pubmed_metadata_pmid([])
    assert isinstance(df, pd.DataFrame)
    assert df.empty


@respx.mock  # type: ignore
def test_get_pubmed_metadata_pmid_success(mock_xml_response: bytes) -> None:
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        return_value=httpx.Response(200, content=mock_xml_response)
    )

    df = get_pubmed_metadata_pmid(["12345"])
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "pmid" in df.columns
    assert "title" in df.columns
    assert df.iloc[0]["pmid"] == "12345"
    assert df.iloc[0]["title"] == "Test Article"


@respx.mock  # type: ignore
def test_get_pubmed_metadata_pmid_network_error() -> None:
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        side_effect=httpx.HTTPError("Network down")
    )
    # The error should be caught and logged, returning an empty dataframe instead of crashing
    df = get_pubmed_metadata_pmid(["12345"])
    assert isinstance(df, pd.DataFrame)
    assert df.empty


@respx.mock  # type: ignore
def test_get_pubmed_metadata_pmid_runtime_error_event_loop(mock_xml_response: bytes) -> None:
    # This simulates calling it from an already running event loop
    respx.post("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        return_value=httpx.Response(200, content=mock_xml_response)
    )

    async def run_in_loop() -> pd.DataFrame:
        return get_pubmed_metadata_pmid(["12345"])

    df = asyncio.run(run_in_loop())
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert df.iloc[0]["pmid"] == "12345"
