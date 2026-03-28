# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_searchpubmed

"""
Domain models for PubMed articles.
"""


from pydantic import BaseModel, Field


class Article(BaseModel):
    """
    Structured representation of a PubMed article.
    """

    pmid: str = Field(description="PubMed ID")
    pmcid: str | None = Field(default=None, description="PubMed Central ID")
    title: str | None = Field(default=None, description="Article title")
    abstract: str | None = Field(default=None, description="Article abstract")
    journal: str | None = Field(default=None, description="Journal name")
    publication_date: str | None = Field(default=None, alias="publicationDate", description="Publication date")
    doi: str | None = Field(default=None, description="Digital Object Identifier")
    first_author: str | None = Field(default=None, alias="firstAuthor", description="First author's name")
    last_author: str | None = Field(default=None, alias="lastAuthor", description="Last author's name")
    author_affiliations: list[str] | None = Field(
        default=None, alias="authorAffiliations", description="List of author affiliations"
    )
    mesh_tags: list[str] | None = Field(default=None, alias="meshTags", description="List of MeSH tags")
    keywords: list[str] | None = Field(default=None, description="List of keywords")
