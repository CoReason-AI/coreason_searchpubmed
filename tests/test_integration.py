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
