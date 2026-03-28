from coreason_searchpubmed.parsers.xml_parser import parse_pubmed_xml

def test_parse_empty():
    articles = parse_pubmed_xml(b"")
    assert len(articles) == 0

def test_parse_invalid_xml():
    articles = parse_pubmed_xml(b"<invalid><xml>")
    assert len(articles) == 0

def test_parse_valid_xml():
    xml = b"""<?xml version="1.0"?>
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>123</PMID>
                <Article>
                    <ArticleTitle>Title</ArticleTitle>
                    <Abstract>
                        <AbstractText>Abs1</AbstractText>
                        <AbstractText>Abs2</AbstractText>
                    </Abstract>
                    <Journal>
                        <Title>JournalName</Title>
                        <JournalIssue>
                            <PubDate>
                                <Year>2020</Year>
                                <Month>01</Month>
                                <Day>01</Day>
                            </PubDate>
                        </JournalIssue>
                    </Journal>
                    <ELocationID EIdType="doi">10.123/456</ELocationID>
                    <AuthorList>
                        <Author>
                            <LastName>Smith</LastName>
                            <ForeName>John</ForeName>
                            <AffiliationInfo>
                                <Affiliation>Inst A</Affiliation>
                            </AffiliationInfo>
                        </Author>
                        <Author>
                            <LastName>Doe</LastName>
                            <ForeName>Jane</ForeName>
                        </Author>
                    </AuthorList>
                </Article>
                <MeshHeadingList>
                    <MeshHeading>
                        <DescriptorName>Mesh1</DescriptorName>
                    </MeshHeading>
                </MeshHeadingList>
                <KeywordList>
                    <Keyword>Kw1</Keyword>
                </KeywordList>
            </MedlineCitation>
            <PubmedData>
                <ArticleIdList>
                    <ArticleId IdType="pmc">PMC123</ArticleId>
                </ArticleIdList>
            </PubmedData>
        </PubmedArticle>
    </PubmedArticleSet>
    """
    articles = parse_pubmed_xml(xml)
    assert len(articles) == 1
    a = articles[0]
    assert a.pmid == "123"
    assert a.title == "Title"
    assert a.abstract == "Abs1 Abs2"
    assert a.journal == "JournalName"
    assert a.publication_date == "2020-01-01"
    assert a.doi == "10.123/456"
    assert a.first_author == "Smith John"
    assert a.last_author == "Doe Jane"
    assert a.author_affiliations == ["Inst A"]
    assert a.mesh_tags == ["Mesh1"]
    assert a.keywords == ["Kw1"]
    assert a.pmcid == "PMC123"

def test_parse_missing_medline():
    xml = b"""<?xml version="1.0"?><PubmedArticleSet><PubmedArticle></PubmedArticle></PubmedArticleSet>"""
    articles = parse_pubmed_xml(xml)
    assert len(articles) == 0

def test_parse_missing_pmid():
    xml = b"""<?xml version="1.0"?><PubmedArticleSet><PubmedArticle><MedlineCitation></MedlineCitation></PubmedArticle></PubmedArticleSet>"""
    articles = parse_pubmed_xml(xml)
    assert len(articles) == 0

def test_parse_missing_article():
    xml = b"""<?xml version="1.0"?><PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID></MedlineCitation></PubmedArticle></PubmedArticleSet>"""
    articles = parse_pubmed_xml(xml)
    assert len(articles) == 0

def test_extract_date_medlinedate():
    xml = b"""<?xml version="1.0"?><PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><ArticleTitle>T</ArticleTitle><Journal><JournalIssue><PubDate><MedlineDate>2020 Spring</MedlineDate></PubDate></JournalIssue></Journal></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"""
    articles = parse_pubmed_xml(xml)
    assert articles[0].publication_date == "2020 Spring"

def test_extract_date_none():
    xml = b"""<?xml version="1.0"?><PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><ArticleTitle>T</ArticleTitle><Journal><JournalIssue><PubDate></PubDate></JournalIssue></Journal></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"""
    articles = parse_pubmed_xml(xml)
    assert articles[0].publication_date is None

def test_parse_exception_on_node():
    # If one article fails to parse, it skips it and continues
    from unittest.mock import patch
    with patch("coreason_searchpubmed.parsers.xml_parser._parse_single_article", side_effect=[Exception("mock err"), None]):
        xml = b"""<?xml version="1.0"?><PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID></MedlineCitation></PubmedArticle></PubmedArticleSet>"""
        articles = parse_pubmed_xml(xml)
        assert len(articles) == 0
