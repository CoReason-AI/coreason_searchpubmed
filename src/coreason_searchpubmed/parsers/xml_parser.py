# Copyright (c) 2026 CoReason, Inc.

from lxml import etree

from coreason_searchpubmed.models.article import Article
from coreason_searchpubmed.utils.logger import logger


def parse_pubmed_xml(xml_content: bytes) -> list[Article]:
    articles: list[Article] = []
    if not xml_content:
        return articles

    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    try:
        root = etree.fromstring(xml_content, parser=parser)
    except etree.XMLSyntaxError as e:
        logger.error(f"Failed to parse XML batch: {e}")
        return articles

    for article_node in root.findall(".//PubmedArticle", namespaces={"ncbi": "http://www.ncbi.nlm.nih.gov"}):
        try:
            article = _parse_single_article(article_node)
            if article:
                articles.append(article)
        except Exception as e:
            logger.error(f"Failed to parse individual article: {e}")
            continue

    return articles

def _parse_single_article(article_node: etree._Element) -> Article | None:
    medline_cit = article_node.find("MedlineCitation")
    if medline_cit is None:
        return None

    pmid_node = medline_cit.find("PMID")
    pmid = pmid_node.text if pmid_node is not None else None
    if not pmid:
        return None

    article_elem = medline_cit.find("Article")
    if article_elem is None:
        return None

    title_node = article_elem.find("ArticleTitle")
    title = title_node.text if title_node is not None else None

    abstract_texts = article_elem.findall("Abstract/AbstractText")
    abstract = " ".join([t.text for t in abstract_texts if t.text]) if abstract_texts else None

    journal_node = article_elem.find("Journal/Title")
    journal = journal_node.text if journal_node is not None else None

    pub_date_node = article_elem.find("Journal/JournalIssue/PubDate")
    publication_date = _extract_date(pub_date_node) if pub_date_node is not None else None

    doi = None
    elocation_ids = article_elem.findall("ELocationID")
    for eid in elocation_ids:
        if eid.get("EIdType") == "doi" and eid.text:
            doi = eid.text
            break

    authors = article_elem.findall("AuthorList/Author")
    first_author, last_author = None, None
    author_affiliations: list[str] = []

    if authors:
        first_author = _extract_author_name(authors[0])
        if len(authors) > 1:
            last_author = _extract_author_name(authors[-1])

        for author in authors:
            affiliations = author.findall("AffiliationInfo/Affiliation")
            for aff in affiliations:
                if aff.text and aff.text not in author_affiliations:
                    author_affiliations.append(aff.text)

    mesh_tags: list[str] = []
    mesh_headings = medline_cit.findall("MeshHeadingList/MeshHeading")
    for mesh in mesh_headings:
        descriptor = mesh.find("DescriptorName")
        if descriptor is not None and descriptor.text:
            mesh_tags.append(descriptor.text)

    keywords: list[str] = []
    keyword_list = medline_cit.findall("KeywordList/Keyword")
    keywords.extend([kw.text for kw in keyword_list if kw.text])

    pmcid = None
    pubmed_data = article_node.find("PubmedData")
    if pubmed_data is not None:
        article_ids = pubmed_data.findall("ArticleIdList/ArticleId")
        for aid in article_ids:
            if aid.get("IdType") == "pmc" and aid.text:
                pmcid = aid.text
                break

    return Article(
        pmid=pmid,
        pmcid=pmcid,
        title=title,
        abstract=abstract,
        journal=journal,
        publicationDate=publication_date,
        doi=doi,
        firstAuthor=first_author,
        lastAuthor=last_author,
        authorAffiliations=author_affiliations or None,
        meshTags=mesh_tags or None,
        keywords=keywords or None
    )

def _extract_date(pub_date_node: etree._Element) -> str | None:
    year_node = pub_date_node.find("Year")
    month_node = pub_date_node.find("Month")
    day_node = pub_date_node.find("Day")

    if year_node is not None and year_node.text:
        date_str = year_node.text
        if month_node is not None and month_node.text:
            date_str += f"-{month_node.text}"
            if day_node is not None and day_node.text:
                date_str += f"-{day_node.text}"
        return date_str

    medline_date_node = pub_date_node.find("MedlineDate")
    if medline_date_node is not None and medline_date_node.text:
        return medline_date_node.text

    return None

def _extract_author_name(author_node: etree._Element) -> str | None:
    last_name_node = author_node.find("LastName")
    fore_name_node = author_node.find("ForeName")

    last = last_name_node.text if last_name_node is not None else ""
    first = fore_name_node.text if fore_name_node is not None else ""

    name = f"{last} {first}".strip()
    return name or None
