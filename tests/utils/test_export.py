import pandas as pd

from coreason_searchpubmed.models.article import Article
from coreason_searchpubmed.utils.export import to_dataframe


def test_export_empty() -> None:
    df = to_dataframe([])
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == [
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
    assert len(df) == 0


def test_export_with_data() -> None:
    articles = [Article(pmid="123", title="Test", authorAffiliations=["Inst A"])]
    df = to_dataframe(articles)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["pmid"] == "123"
    assert df.iloc[0]["title"] == "Test"
    assert df.iloc[0]["authorAffiliations"] == ["Inst A"]
