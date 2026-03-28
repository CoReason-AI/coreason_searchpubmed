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

    records = [article.model_dump(by_alias=True) for article in articles]
    df = pd.DataFrame(records)

    text_cols = ["pmid", "pmcid", "title", "abstract", "journal", "publicationDate", "doi", "firstAuthor", "lastAuthor"]

    for col in text_cols:
        if col in df.columns:
            with contextlib.suppress(TypeError, ValueError):
                df[col] = df[col].astype("string[pyarrow]")

    return df
