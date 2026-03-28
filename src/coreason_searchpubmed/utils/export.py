# Copyright (c) 2026 CoReason, Inc.
import contextlib

import pandas as pd

from coreason_searchpubmed.models.article import Article


def to_dataframe(articles: list[Article]) -> pd.DataFrame:
    if not articles:
        return pd.DataFrame(
            columns=[
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
        )

    # Access fields directly using field aliases to avoid slow .model_dump()
    cols = [
        "pmid",
        "pmcid",
        "title",
        "abstract",
        "journal",
        "publication_date",
        "doi",
        "first_author",
        "last_author",
        "author_affiliations",
        "mesh_tags",
        "keywords",
    ]

    # Preallocate columnar data
    data = {k: [getattr(a, k) for a in articles] for k in cols}

    df = pd.DataFrame(data)

    # Rename columns to aliases
    rename_map = {
        "publication_date": "publicationDate",
        "first_author": "firstAuthor",
        "last_author": "lastAuthor",
        "author_affiliations": "authorAffiliations",
        "mesh_tags": "meshTags",
    }
    df = df.rename(columns=rename_map)

    text_cols = ["pmid", "pmcid", "title", "abstract", "journal", "publicationDate", "doi", "firstAuthor", "lastAuthor"]

    for col in text_cols:
        if col in df.columns:
            with contextlib.suppress(TypeError, ValueError):
                df[col] = df[col].astype("string[pyarrow]")

    return df
