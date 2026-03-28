from coreason_searchpubmed.models.article import Article

def test_article_model_instantiation():
    article = Article(pmid="123", title="Test")
    assert article.pmid == "123"
    assert article.title == "Test"

def test_article_aliases():
    article = Article(pmid="123", publicationDate="2020-01-01")
    assert article.publication_date == "2020-01-01"
    dump = article.model_dump(by_alias=True)
    assert "publicationDate" in dump
    assert dump["publicationDate"] == "2020-01-01"
